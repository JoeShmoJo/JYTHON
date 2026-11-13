# -*- coding: utf-8 -*-
"""Jython 2.7 Swing controls for named archive snapshots in either main GUI."""
import codecs
import json
import os
import shutil
import tempfile
from java.awt import BorderLayout, GridLayout
from java.io import File
from java.lang import ProcessBuilder
from java.lang import Exception as JavaException
from java.util import ArrayList
from javax.swing import (JPanel, JLabel, JTextField, JComboBox, JButton, JList,
                         DefaultListModel, JScrollPane, JOptionPane, SwingWorker,
                         ListSelectionModel)


def display_time(value):
    if not value:return 'time unavailable'
    try:
        from java.time import OffsetDateTime, ZoneId
        from java.time.format import DateTimeFormatter
        return str(OffsetDateTime.parse(str(value)).atZoneSameInstant(ZoneId.systemDefault()).format(
            DateTimeFormatter.ofPattern('yyyy-MM-dd HH:mm:ss z')))
    except Exception:return str(value)


class ArchiveTask(SwingWorker):
    def __init__(self,panel,request):
        SwingWorker.__init__(self);self.panel=panel;self.request=request
    def doInBackground(self):
        directory=tempfile.mkdtemp(prefix='saved-results-')
        try:
            request=os.path.join(directory,'request.json');response=os.path.join(directory,'response.json')
            log=os.path.join(directory,'task.log')
            with codecs.open(request,'w','utf-8') as handle:handle.write(unicode(json.dumps(self.request)))
            command=ArrayList()
            for arg in [self.panel.python,'-u',os.path.join(self.panel.backend,'saved_results_actions.py'),
                        '--request',request,'--response',response]:command.add(arg)
            builder=ProcessBuilder(command);builder.directory(File(self.panel.backend))
            builder.redirectErrorStream(True);builder.redirectOutput(File(log))
            code=builder.start().waitFor()
            if os.path.isfile(response):
                with codecs.open(response,'r','utf-8') as handle:result=json.load(handle)
            else:
                with codecs.open(log,'r','utf-8','replace') as handle:detail=''.join(handle.readlines()[-20:])
                raise RuntimeError('Archive task did not return a response. '+detail)
            if code or result.get('error'):raise RuntimeError(result.get('error','Archive task failed.'))
            return result
        finally:shutil.rmtree(directory)
    def done(self):
        panel=self.panel
        panel.host_busy(False);panel.busy=False
        try:panel.completed(self.request,self.get())
        except (Exception,JavaException) as error:
            panel.status.setText('Archive action failed: '+str(error))
            panel.message('Archive action failed: '+str(error))
            JOptionPane.showMessageDialog(panel.dialog_parent,str(error),'Saved results',JOptionPane.WARNING_MESSAGE)
        finally:panel.update_controls()


class SavedResultsPanel(JPanel):
    def __init__(self,owner,mode,backend,python,get_context):
        JPanel.__init__(self,BorderLayout(5,5))
        self.owner=owner;self.dialog_parent=getattr(owner,'frame',owner)
        self.mode=mode;self.backend=backend;self.python=python;self.get_context=get_context
        self.busy=False;self.context=None;self.rows=[];self.want_selection=[];self.notice=None
        self.controls=[]
        top=JPanel(GridLayout(0,2,4,3))
        top.add(JLabel('Archive name for current results'));self.archive_name=JTextField();top.add(self.archive_name)
        self.archive_name.setToolTipText('Enter a distinct name after each compute; saving settings does not archive outputs.')
        top.add(JLabel('Completed output to archive'));self.output=JComboBox();top.add(self.output)
        self.kind=JComboBox(['New baseline','Result paired with a baseline']);self.baseline=JComboBox()
        if mode=='standalone':
            top.add(JLabel('Archive purpose'));top.add(self.kind)
            top.add(JLabel('Baseline for paired result'));top.add(self.baseline)
        self.add(top,BorderLayout.NORTH)
        self.model=DefaultListModel();self.runs=JList(self.model)
        self.runs.setSelectionMode(ListSelectionModel.MULTIPLE_INTERVAL_SELECTION)
        self.runs.setVisibleRowCount(4)
        self.runs.setToolTipText('Saved snapshots: Ctrl-click one or two to plot. Times are archive times in this computer\'s timezone.')
        self.add(JScrollPane(self.runs),BorderLayout.CENTER)
        bottom=JPanel(GridLayout(0,1,4,3))
        actions=JPanel(GridLayout(1,4,4,3))
        for text,handler in [('Refresh archives / outputs',self.refresh),('Archive current results',self.archive),
                             ('Plot selected archives',self.plot),('Delete selected archive',self.delete)]:
            button=JButton(text,actionPerformed=handler);actions.add(button);self.controls.append(button)
        bottom.add(actions)
        bottom.add(JLabel('<html><b>Before your next compute:</b> archive current results if you want to keep them. Recomputing replaces live outputs.<br>Saving baseline settings is separate from archiving results. Select one or two saved archives to plot.</html>'))
        self.status=JLabel('Select the target, then Refresh archives / outputs.');bottom.add(self.status)
        self.add(bottom,BorderLayout.SOUTH)
        self.controls.extend([self.archive_name,self.output,self.kind,self.baseline,self.runs])
        self.kind.addActionListener(lambda event:self.update_controls())
        self.update_controls()
    def host_busy(self,busy):
        if hasattr(self.owner,'set_busy'):self.owner.set_busy(busy)
        else:self.owner.busy=busy
    def message(self,text):
        if hasattr(self.owner,'message'):self.owner.message(text)
        elif hasattr(self.owner,'append'):self.owner.append(text)
    def update_controls(self):
        for control in self.controls:control.setEnabled(not self.busy)
        self.baseline.setEnabled(not self.busy and self.kind.getSelectedIndex()==1)
    def selection(self):return [self.rows[int(index)] for index in self.runs.getSelectedIndices()]
    def start(self,action,**data):
        if self.busy or self.owner.busy:return
        try:
            context=self.get_context()
            if action!='list' and context!=self.context:
                raise RuntimeError('The target changed. Refresh archives / outputs before continuing.')
            request=dict(mode=self.mode,context=context,action=action,**data)
            self.busy=True;self.host_busy(True);self.update_controls()
            self.status.setText('Working: '+action+'...')
            ArchiveTask(self,request).execute()
        except (Exception,JavaException) as error:
            self.busy=False;self.host_busy(False);self.update_controls()
            JOptionPane.showMessageDialog(self.dialog_parent,str(error),'Saved results',JOptionPane.WARNING_MESSAGE)
    def refresh(self,event=None):
        if not self.want_selection:self.want_selection=[row['id'] for row in self.selection()]
        self.start('list')
    def archive(self,event):
        if self.busy or self.owner.busy:return
        label=str(self.archive_name.getText()).strip()
        if not label:
            JOptionPane.showMessageDialog(self.dialog_parent,'Enter a distinct archive name first.');return
        duplicate=next((row for row in self.rows if row['label'].strip().lower()==label.lower()),None)
        if duplicate:
            JOptionPane.showMessageDialog(self.dialog_parent,'An archive named "'+duplicate['label']+'" already exists, saved '+display_time(duplicate.get('created_utc'))+'.\nEnter a different name. The existing archive will be kept.','Duplicate archive name',JOptionPane.WARNING_MESSAGE);return
        if not self.output.getSelectedItem():
            JOptionPane.showMessageDialog(self.dialog_parent,'Refresh and select a completed output first.');return
        paired=self.mode=='standalone' and self.kind.getSelectedIndex()==1
        baselines=[row for row in self.rows if row['kind']=='baseline']
        if paired and self.baseline.getSelectedIndex()<0:
            JOptionPane.showMessageDialog(self.dialog_parent,'Archive or select a baseline first.');return
        baseline_id=baselines[self.baseline.getSelectedIndex()]['id'] if paired else None
        if JOptionPane.showConfirmDialog(self.dialog_parent,
            'Confirm the native compute finished successfully and no compute is running.\nSave a snapshot named "'+label+'" from '+str(self.output.getSelectedItem())+'?\nArchive again after each compute you want to keep.',
            'Archive current results',JOptionPane.OK_CANCEL_OPTION)!=JOptionPane.OK_OPTION:return
        self.start('archive',label=label,code=str(self.output.getSelectedItem()),kind='result' if paired else 'baseline',baseline_id=baseline_id,confirmed=True)
    def plot(self,event):
        rows=self.selection()
        if len(rows) not in (1,2):
            JOptionPane.showMessageDialog(self.dialog_parent,'Select one or two saved archives (Ctrl-click for two).');return
        self.start('plot',ids=[row['id'] for row in rows])
    def delete(self,event):
        rows=self.selection()
        if len(rows)!=1:
            JOptionPane.showMessageDialog(self.dialog_parent,'Select one archive to delete.');return
        row=rows[0]
        if JOptionPane.showConfirmDialog(self.dialog_parent,
            'Permanently delete "'+row['label']+'", saved '+display_time(row.get('created_utc'))+'?\nLive model results and other archives are kept. Exported plots are retained.\nDeletion cannot be undone; referenced baselines are protected.',
            'Delete saved archive',JOptionPane.YES_NO_OPTION,JOptionPane.WARNING_MESSAGE)!=JOptionPane.YES_OPTION:return
        self.start('delete',id=row['id'],confirmed=True)
    def completed(self,request,result):
        action=request['action']
        if action=='list':
            rows=result['runs']
            if rows is None:rows=self.rows if self.context==request['context'] else []
            self.context=request['context'];self.rows=rows;self.model.clear()
            indices=[]
            for index,row in enumerate(self.rows):
                stamp=display_time(row.get('created_utc'))
                self.model.addElement(row['label']+' | '+row['kind']+' | '+stamp+' | '+row['id'][-8:])
                if row['id'] in self.want_selection:indices.append(index)
            self.runs.setSelectedIndices(indices);self.want_selection=[]
            previous=self.output.getSelectedItem();self.output.removeAllItems()
            for code in result['outputs']:self.output.addItem(code)
            if previous in result['outputs']:self.output.setSelectedItem(previous)
            self.baseline.removeAllItems()
            for row in self.rows:
                if row['kind']=='baseline':self.baseline.addItem(row['label']+' / '+display_time(row.get('created_utc')))
            text=self.notice or ('Saved archives: '+str(len(self.rows))+'. Refresh does not save live results.')
            self.notice=None
            if result.get('notices'):text+=' '+ ' '.join(result['notices'])
            self.status.setText(text)
        elif action in ('archive','delete'):
            if action=='archive':
                row=result['saved'];self.want_selection=[row['id']];self.archive_name.setText('')
                self.rows.insert(0,row)
                self.model.insertElementAt(row['label']+' | '+row['kind']+' | '+display_time(row['created_utc'])+' | '+row['id'][-8:],0)
                self.runs.setSelectedIndex(0)
                self.notice='Archived "'+row['label']+'" at '+display_time(row['created_utc'])+'.'
            else:self.notice='Deleted "'+result['label']+'".'
            self.message(self.notice);self.refresh()
        elif action=='plot':self.status.setText('Opened saved plots: '+result['path'])
