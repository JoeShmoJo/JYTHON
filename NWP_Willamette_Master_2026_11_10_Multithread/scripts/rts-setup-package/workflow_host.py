"""Jython-compatible workflow routing. Selection never installs or rewrites scripts."""
import os


def detect_runtime():
    try:
        from usace.cavi.client import CAVI
    except ImportError:
        return 'standalone'
    # Class availability alone is insufficient: require a running CAVI frame.
    return 'rts' if CAVI.getCaviFrame() is not None else 'standalone'


def menu_path(scripts, mode):
    if mode not in ('rts', 'standalone'):
        raise ValueError('Unknown workflow host: '+str(mode))
    filename = 'RTS_WORKFLOW_MENU.py' if mode=='rts' else 'STANDALONE_WORKFLOW_UI.py'
    path = os.path.join(scripts,filename)
    if not os.path.isfile(path):
        raise RuntimeError('Bundled workflow UI is missing: '+path)
    return path


def launch(scripts, mode=None, execute=None):
    mode = detect_runtime() if mode is None else mode
    filename = menu_path(scripts,mode)
    print('Workflow host: '+mode+'; UI: '+filename)
    if execute is not None:
        return execute(filename)
    namespace = {'__name__':'__main__','__file__':filename}
    with open(filename,'rb') as handle:
        code = compile(handle.read(),filename,'exec')
    eval(code,namespace,namespace)
