// Run with Node.js and Playwright. Optional CHROMIUM_EXECUTABLE selects system Chrome.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const scripts = path.join(__dirname, '..', 'NWP_Willamette_Master_2026_11_10_Multithread', 'scripts', 'ExternalPython');
const baseline = {id:'run-baseline',label:'First baseline',kind:'baseline',alternative:'Con_Season',created_utc:'2026-11-13T12:00:00Z',run_code:'Con_Season0'};
const config = {schema:1,name:'Original configuration',columns:['Variable','Hills Creek','Lookout Point'],
  rows:[['Abbreviation','HCR','LOP'],['SupportsSalem','FALSE','TRUE'],['SupportsAlbany','FALSE','TRUE'],
    ['MinConStor','155400','118800'],['MaxRelease','1800','2700'],['TravelTimeDays','2','2']],
  calculation:{forecast_days:10,wy_type_mode:'storage-maf'}};

async function openPage(browser, filename, api) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', dialog => dialog.accept());
  let html = fs.readFileSync(path.join(scripts,filename),'utf8')
    .replaceAll('__TOKEN__',JSON.stringify('test-token')).replaceAll('__TARGET__',JSON.stringify('Test / Con_Season'))
    .replaceAll('__RUN_TYPE__',JSON.stringify('ensemble')).replaceAll('__ALTERNATIVE__',JSON.stringify('Con_Season'));
  await page.route('http://standalone.test/**', async route => {
    if (route.request().method()==='GET') return route.fulfill({contentType:'text/html',body:html});
    assert.equal(route.request().headers()['x-editor-token'],'test-token');
    const result = await api(new URL(route.request().url()).pathname,route.request().postDataJSON());
    return route.fulfill({status:result.error?400:200,contentType:'application/json',body:JSON.stringify(result)});
  });
  await page.goto('http://standalone.test/editor');
  return {page,errors};
}

async function main() {
  const browser = await chromium.launch({headless:true,
    ...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox']});
  try {
    // Cold opening cannot submit an empty selection; capture updates the open page
    // even when the subsequent live DSS scan fails.
    let rows=[],locked=false;
    let current=await openPage(browser,'standalone_results.html',async (url,data)=>{
      if(url==='/archives')return {runs:rows};
      if(url==='/list'){
        await new Promise(resolve=>setTimeout(resolve,200));
        return {runs:rows,outputs:locked?[]:['Con_Season0'],notices:locked?['Live DSS is locked; saved runs remain available.']:[]};
      }
      if(url==='/capture'){assert.equal(data.kind,undefined);assert.equal(data.code,'Con_Season0');rows=[baseline];locked=true;return baseline}
      if(url==='/plot'){assert.deepEqual(data.ids,[baseline.id]);return {path:'saved-plots/index.html'}}
      throw Error('Unexpected API '+url);
    });
    let page=current.page;
    assert.equal(await page.locator('#capture').isDisabled(),true);
    await page.waitForFunction(()=>document.querySelector('#output').value==='Con_Season0'&&!document.querySelector('#refresh').disabled);
    await page.fill('#name','First baseline');
    await page.click('#capture');
    await page.waitForFunction(()=>!document.querySelector('#plot').disabled);
    assert.match(await page.textContent('#status'),/Archived.*First baseline/);
    assert.match(await page.textContent('#status'),/locked/);
    assert.equal(await page.locator('#runs option:checked').getAttribute('value'),baseline.id);
    await page.click('#plot');await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Plots:'));
    assert.deepEqual(current.errors,[]);await page.close();
    console.log('PASS: cold loading, first baseline capture, immediate selection/plot and live-DSS refresh failure');

    locked=true;rows=[baseline];
    current=await openPage(browser,'standalone_results.html',async (url,data)=>{
      if(url==='/archives')return {runs:rows};
      if(url==='/list')return {runs:rows,outputs:locked?[]:['Con_Season1'],notices:locked?['Live DSS is locked']:[]};
      if(url==='/delete'){assert.equal(data.id,'run-result');assert.equal(data.confirmed,true);rows=rows.filter(row=>row.id!==data.id);return {deleted:data.id}}
      if(url==='/capture'){assert.equal(data.baseline_id,undefined);assert.equal(data.kind,undefined);
        const row={...baseline,id:'run-result',label:'Augmented result',kind:'result'};rows=[row,baseline];return row}
      throw Error('Unexpected API '+url);
    });
    page=current.page;await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    assert.equal(await page.locator('#runs option').count(),1);
    await page.selectOption('#runs',baseline.id);assert.equal(await page.locator('#plot').isEnabled(),true);
    await page.fill('#name','Augmented result');
    locked=false;await page.click('#refresh');await page.waitForFunction(()=>!document.querySelector('#capture').disabled);
    assert.equal(await page.inputValue('#name'),'Augmented result');
    await page.click('#capture');await page.waitForFunction(()=>document.querySelector('#runs').value==='run-result'&&!document.querySelector('#plot').disabled);
    assert.equal(await page.locator('#runs option').count(),2);
    assert.equal(await page.inputValue('#name'),'');
    await page.fill('#name','  FIRST BASELINE  ');await page.click('#capture');
    await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('already exists'));
    assert.equal(await page.locator('#runs option').count(),2);
    await page.click('#delete');
    await page.waitForFunction(()=>document.querySelector('#runs').options.length===1&&!document.querySelector('#refresh').disabled);
    assert.match(await page.textContent('#status'),/Deleted/);
    assert.deepEqual(current.errors,[]);await page.close();
    console.log('PASS: existing archives with locked live DSS, independent snapshots, duplicate warning, deletion and refresh');

    let available=[];let submitted;
    current=await openPage(browser,'standalone_augmentation.html',async (url,data)=>{
      if(url==='/state')return {configuration:config,baselines:available,baseline_id:null};
      if(url==='/calculate'){submitted=data;return {configuration_name:data.configuration.name,scheme:'scheme-test'}}
      if(url==='/save')return data.configuration;
      throw Error('Unexpected API '+url);
    });
    page=current.page;await page.waitForFunction(()=>!document.querySelector('#save').disabled);
    assert.equal(await page.locator('#calculate').isDisabled(),true);
    await page.fill('#days','5');await page.fill('#name','Configured augmentation');
    await page.getByTitle('MaxRelease / Lookout Point').fill('900');
    available=[baseline];await page.click('#refresh');await page.waitForFunction(()=>!document.querySelector('#calculate').disabled);
    assert.equal(await page.inputValue('#days'),'5');
    assert.equal(await page.getByTitle('MaxRelease / Lookout Point').inputValue(),'900');
    await page.click('#calculate');await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Loaded'));
    assert.equal(submitted.baseline_id,baseline.id);assert.equal(submitted.confirmed,true);
    assert.equal(submitted.configuration.calculation.forecast_days,5);
    assert.equal(submitted.configuration.rows.find(row=>row[0]==='MaxRelease')[2],'900');
    const imported={...config,name:'Imported configuration',calculation:{forecast_days:7,wy_type_mode:'storage-maf'}};
    await page.locator('#file').setInputFiles({name:'configuration.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(imported))});
    await page.waitForFunction(()=>document.querySelector('#name').value==='Imported configuration');
    assert.equal(await page.inputValue('#days'),'7');
    const download=page.waitForEvent('download');await page.click('#save');assert.equal((await download).suggestedFilename(),'Imported_configuration.json');
    assert.deepEqual(current.errors,[]);await page.close();
    console.log('PASS: augmentation configuration, missing baseline, refresh preserves edits, calculate payload and portable JSON open/save');
    for(const filename of ['baseline-editor.html','../RTSPython/baseline-editor.html']){
      current=await openPage(browser,filename,async()=>{throw Error('No server call expected')});
      page=current.page;await page.waitForSelector('#baseline-augmentation');
      assert.equal(await page.inputValue('#baseline-augmentation'),'off');
      await page.selectOption('#baseline-augmentation','simplified');
      await page.getByRole('button',{name:'Deep Drawdown',exact:true}).click();
      await page.getByRole('button',{name:'Configuration Overview',exact:true}).click();
      assert.equal(await page.inputValue('#baseline-augmentation'),'simplified');
      const download=page.waitForEvent('download');await page.click('#save');
      const exported=JSON.parse(fs.readFileSync(await (await download).path(),'utf8'));
      assert.equal(exported.baseline_augmentation,'simplified');
      assert.deepEqual(current.errors,[]);await page.close();
    }
    console.log('PASS: baseline editors preserve and export basic augmentation as part of baseline settings');
  } finally { await browser.close(); }
}
main().catch(error=>{console.error(error);process.exitCode=1});
