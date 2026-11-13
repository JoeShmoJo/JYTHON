"""Run under Jython 2.7: concurrent per-member status via real Java NIO."""
import copy
import json
import os
import shutil
import sys
import tempfile
import threading
from java.lang import String

scripts=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','NWP_Willamette_Master_2026_11_10_Multithread','scripts'))
sys.path.insert(0,scripts)
from augmentation_diagnostics import Status,initialize_off
from NWDJyLib.cFile import parallelSafeReadText,parallelSafeWriteText

root=tempfile.mkdtemp(prefix='augmentation-native-status-')
errors=[]
try:
    parallelSafeWriteText(os.path.join(root,'standalone-baseline-config-active.json'),json.dumps(dict(id='native-test',model_alternative='Con_Season')),'UTF-8')
    class Alternative:
        def __init__(self,member):self.member=member
        def varGet(self,key):
            if key=='dssOutputFpart':return String('C:%06d|Con_Season0'%self.member)
            if key=='baselineFlowAugMethod':return String('NoFlowAug')
    class Named:
        def getName(self):return 'Con_Season'
    class Run:
        def getDSSOutputFile(self):return os.path.join(root,'simulation.dss')
    class Network:
        def makeAbsolutePathFromWatershed(self,path):return path
        def getRssRun(self):return Run()
        def getAlternative(self):return Named()
    def worker(member):
        try:
            status=Status(Network(),Alternative(member),'NoFlowAug',False)
            status.rule('Lookout Point',0.,'off')
            status.write('cleanup-finished',compute_enabled=False)
        except Exception as error:errors.append(str(error))
    threads=[threading.Thread(target=worker,args=(member,)) for member in range(1981,1997)]
    for thread in threads:thread.start()
    for thread in threads:thread.join()
    assert not errors,repr(errors)
    files=os.listdir(os.path.join(root,'augmentation-status'))
    assert len(files)==16,len(files)
    rows=[json.loads(parallelSafeReadText(os.path.join(root,'augmentation-status',name),'UTF-8')) for name in files]
    assert set(row['member'] for row in rows)==set(range(1981,1997))
    assert all(row['effective_method']=='NoFlowAug' and row['stage']=='cleanup-finished' for row in rows)
    print('PASS: 16 concurrent Jython members write independent effective-method status through Java NIO')
finally:shutil.rmtree(root)
