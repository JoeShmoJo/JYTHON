"""Jython-compatible desktop Python discovery for both workflow menus."""
import os

ENVIRONMENTS = ('ResSim12Nov2026', 'hydro39')


def python_executable():
    roots = []
    for base in ('LOCALAPPDATA', 'USERPROFILE', 'PROGRAMDATA', 'PROGRAMFILES'):
        directory = os.environ.get(base)
        if directory:
            roots += [os.path.join(directory, name) for name in ('miniconda3', 'anaconda3', 'Miniforge3')]
    roots += [os.path.join(base, name) for base in ('C:\\', r'C:\Programs')
              for name in ('miniconda3', 'anaconda3', 'Miniforge3')]
    # Also support Conda installations explicitly advertised by the launching shell.
    conda = os.environ.get('CONDA_EXE')
    if conda:
        roots.insert(0, os.path.dirname(os.path.dirname(conda)))
    env_dirs = [os.path.join(root, 'envs') for root in roots]
    if os.environ.get('USERPROFILE'):
        env_dirs.append(os.path.join(os.environ['USERPROFILE'], '.conda', 'envs'))
    for environment in ENVIRONMENTS:
        for directory in env_dirs:
            candidate = os.path.join(directory, environment, 'python.exe')
            if os.path.isfile(candidate):
                return candidate
    raise IOError('Could not find ResSim12Nov2026 (or legacy hydro39). Run PythonSetup1stTime/Install-WorkflowEnvironment.ps1.')
