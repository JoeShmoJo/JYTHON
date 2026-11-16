# Paste into the standalone ResSim Script Editor (Jython).
import os
import sys
import json
from java.lang import Thread, Runnable, System, ProcessBuilder
from java.io import File
from java.util import ArrayList
from java.awt import GridLayout, BorderLayout
from javax.swing import (JFrame, JPanel, JButton, JTextArea, JScrollPane,
                         JOptionPane, SwingUtilities, WindowConstants, JLabel, JTextField, JComboBox)
from hec.script import ClientAppWrapper

root = str(ClientAppWrapper.getWatershed().getWkspDir())
scripts = os.path.join(root, 'scripts', 'ExternalPython')
script_root = os.path.join(root, 'scripts')
if script_root not in sys.path:
    sys.path.insert(0, script_root)
from workflow_python import python_executable
python = python_executable()

class Call(Runnable):
    def __init__(self, fn): self.fn = fn
    def run(self): self.fn()

class Menu:
    def __init__(self):
        self.busy = False
        self.log = None
        self.frame = JFrame('Standalone ResSim workflow')
        self.frame.setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE)
        self.text = JTextArea(5, 90)
        self.text.setEditable(False)
        self.text.setLineWrap(True)
        self.text.setWrapStyleWord(True)
        self.text.setText('Baseline settings can be saved/loaded/applied through the shared editor. Use one model alternative; recompute after Apply.\nLoaded watershed: ' + root + '\n\nSelect the simulation and alternative below for Baseline Configuration. Extraction and augmentation use the same target and the Standalone job settings saved in Baseline Configuration. Apply settings before running jobs. Finish computes and close DSS views before file-writing steps. Compute manually in ResSim.\n')
        buttons = JPanel(GridLayout(0, 2, 5, 5))
        buttons.add(JLabel('Baseline target simulation (select explicitly)'))
        self.simulation = JComboBox()
        self.simulation.addItem('-- Select simulation --')
        rss = os.path.join(root, 'rss')
        if os.path.isdir(rss):
            for name in sorted(os.listdir(rss)):
                if os.path.isdir(os.path.join(rss, name)):
                    self.simulation.addItem(name)
        buttons.add(self.simulation)
        buttons.add(JLabel('Baseline target alternative (as shown in ResSim)'))
        self.alternative = JTextField('')
        buttons.add(self.alternative)
        buttons.add(JLabel('Simulation type'))
        self.run_type = JComboBox()
        self.run_type.addItem('Ensemble')
        self.run_type.addItem('Single POR')
        buttons.add(self.run_type)
        buttons.add(JButton('Baseline Configuration', actionPerformed=lambda e: self.open_baseline()))
        jobs = [('Extract ensemble inputs', 'extract'),
                ('Extract archived ensemble inputs', 'archive-extract')]
        self.ensemble_buttons = []
        for title, job in jobs:
            button = JButton(title, actionPerformed=lambda e, t=title, j=job: self.start(t, j))
            if job in ('extract','archive-extract','archive-check'): self.ensemble_buttons.append(button)
            buttons.add(button)
        self.run_type.addActionListener(self.update_mode)
        buttons.add(JButton('Augmentation Configuration', actionPerformed=lambda e: self.open_augmentation()))
        buttons.add(JButton('Archive / Plot Results', actionPerformed=lambda e: self.open_results()))
        buttons.add(JButton('Model Check', actionPerformed=lambda e: self.open_results(True)))
        self.frame.add(buttons, BorderLayout.NORTH)
        self.frame.add(JScrollPane(self.text), BorderLayout.CENTER)
        from saved_results_panel import SavedResultsPanel
        self.archives=SavedResultsPanel(self,'standalone',scripts,python,self.archive_context)
        self.frame.add(self.archives,BorderLayout.SOUTH)
        self.frame.pack()
        self.frame.setLocationRelativeTo(None)
        self.frame.setVisible(True)
    def archive_context(self):
        if self.simulation.getSelectedIndex()==0 or not str(self.alternative.getText()).strip():
            raise RuntimeError('Select a simulation and alternative first.')
        simulation=str(self.simulation.getSelectedItem()).replace(' ','_')
        return dict(mode='standalone',dss_path=os.path.join(root,'rss',simulation,'simulation.dss'),
                    model_alternative=str(self.alternative.getText()).strip(),
                    run_type='por' if self.run_type.getSelectedIndex()==1 else 'ensemble')
    def update_mode(self, event):
        for button in self.ensemble_buttons:
            button.setEnabled(self.run_type.getSelectedIndex() == 0)
    def message(self, value):
        SwingUtilities.invokeLater(Call(lambda: self.text.append(value + '\n')))
    def open_baseline(self):
        if self.busy: return
        simulation = str(self.simulation.getSelectedItem())
        alternative = str(self.alternative.getText()).strip()
        if self.simulation.getSelectedIndex() == 0 or not alternative:
            JOptionPane.showMessageDialog(self.frame, 'Select the simulation and enter the alternative shown in ResSim Simulation Control.')
            return
        filename = os.path.join(scripts, 'standalone_configuration.py')
        if not os.path.isfile(filename):
            JOptionPane.showMessageDialog(self.frame, 'Install the standalone configuration editor first.')
            return
        if JOptionPane.showConfirmDialog(self.frame, 'Archive current results first if you want to keep them. Finish all computes before Apply. Confirm this matches ResSim Simulation Control:\nSimulation: ' + simulation + '\nAlternative: ' + alternative + '\nDirectory: ' + os.path.join(root, 'rss', simulation), 'Standalone configuration', JOptionPane.OK_CANCEL_OPTION) != JOptionPane.OK_OPTION:
            return
        directory = os.path.join(root, 'standalone-workflow-logs')
        if not os.path.isdir(directory): os.makedirs(directory)
        self.log = os.path.join(directory, 'configuration-' + str(System.currentTimeMillis()) + '.log')
        command = ArrayList()
        for arg in [python, '-u', filename, '--watershed', root, '--simulation', simulation, '--alternative', alternative, '--run-type', 'por' if self.run_type.getSelectedIndex() == 1 else 'ensemble']: command.add(arg)
        builder = ProcessBuilder(command)
        builder.directory(File(scripts))
        builder.redirectErrorStream(True)
        builder.redirectOutput(File(self.log))
        builder.start()
        self.message('Configuration editor starting. Browser opens after settings load. Log: ' + self.log)
    def open_results(self, model_check=False):
        if self.busy: return
        simulation = str(self.simulation.getSelectedItem())
        alternative = str(self.alternative.getText()).strip()
        if self.simulation.getSelectedIndex() == 0 or not alternative:
            JOptionPane.showMessageDialog(self.frame, 'Select the simulation and alternative first.')
            return
        filename = os.path.join(scripts, 'standalone_results.py')
        if not os.path.isfile(filename): raise RuntimeError('Install the updated standalone workflow first.')
        command = ArrayList()
        for arg in [python, '-u', filename, '--watershed', root, '--simulation', simulation,
                    '--alternative', alternative, '--run-type', 'por' if self.run_type.getSelectedIndex() == 1 else 'ensemble']: command.add(arg)
        if model_check: command.add('--model-check')
        directory = os.path.join(root, 'standalone-workflow-logs')
        if not os.path.isdir(directory): os.makedirs(directory)
        self.log = os.path.join(directory, 'results-' + str(System.currentTimeMillis()) + '.log')
        builder = ProcessBuilder(command);builder.directory(File(scripts))
        builder.redirectErrorStream(True);builder.redirectOutput(File(self.log));builder.start()
        self.message('Saved results browser starting. Log: ' + self.log)
    def open_augmentation(self):
        if self.busy: return
        simulation = str(self.simulation.getSelectedItem())
        alternative = str(self.alternative.getText()).strip()
        if self.simulation.getSelectedIndex() == 0 or not alternative:
            JOptionPane.showMessageDialog(self.frame, 'Select the simulation and alternative first.')
            return
        filename = os.path.join(scripts, 'standalone_augmentation.py')
        if not os.path.isfile(filename): raise RuntimeError('Install the updated standalone augmentation editor first.')
        command = ArrayList()
        for arg in [python, '-u', filename, '--watershed', root, '--simulation', simulation,
                    '--alternative', alternative, '--run-type', 'por' if self.run_type.getSelectedIndex() == 1 else 'ensemble']: command.add(arg)
        directory = os.path.join(root, 'standalone-workflow-logs')
        if not os.path.isdir(directory): os.makedirs(directory)
        self.log = os.path.join(directory, 'augmentation-' + str(System.currentTimeMillis()) + '.log')
        builder = ProcessBuilder(command);builder.directory(File(scripts))
        builder.redirectErrorStream(True);builder.redirectOutput(File(self.log));builder.start()
        self.message('Augmentation configuration starting. Select a saved baseline in the browser. Log: ' + self.log)
    def start(self, title, job):
        if self.busy:
            JOptionPane.showMessageDialog(self.frame, 'A job is already running.')
            return
        simulation = str(self.simulation.getSelectedItem())
        alternative = str(self.alternative.getText()).strip()
        if self.simulation.getSelectedIndex() == 0 or not alternative:
            JOptionPane.showMessageDialog(self.frame, 'Select the simulation and alternative first. Review and Apply Baseline Configuration before running jobs.')
            return
        if job not in ('archive-check','archive-extract') and JOptionPane.showConfirmDialog(self.frame,
            title + '\nSimulation: ' + simulation + '\nAlternative: ' + alternative + '\nUses applied Baseline Configuration job settings. Save Simulation Control dates first. Archive current results first if you want to keep them. Confirm no compute is running and DSS views are closed.',
            'Run standalone scripts', JOptionPane.OK_CANCEL_OPTION) != JOptionPane.OK_OPTION:
            return
        run_type = 'por' if self.run_type.getSelectedIndex() == 1 else 'ensemble'
        if run_type == 'por' and job in ('extract','archive-extract','archive-check'):
            JOptionPane.showMessageDialog(self.frame, 'Use existing POR inputs and compute in ResSim. Ensemble extraction is unavailable in Single POR mode; no OSI copy is needed.')
            return
        self.busy = True
        Thread(Call(lambda: self.run(title, job, simulation, alternative, run_type)), 'Standalone workflow job').start()
    def archive_check(self, simulation, alternative, run_type, extract):
        report_path = self.log + '.check.json'
        check_log = self.log + '.check.log'
        command = ArrayList()
        for arg in [python, '-u', os.path.join(scripts, 'standalone_jobs.py'),
                    '--watershed', root, '--simulation', simulation, '--alternative', alternative,
                    '--run-type', run_type, '--job', 'archive-check', '--report', report_path]: command.add(arg)
        self.message('Checking archive dates and available members. Log: ' + check_log)
        builder = ProcessBuilder(command);builder.directory(File(scripts))
        builder.redirectErrorStream(True);builder.redirectOutput(File(check_log))
        code = builder.start().waitFor()
        if code != 0 or not os.path.isfile(report_path):
            with open(check_log, 'r') as handle: detail = ''.join(handle.readlines()[-14:])
            raise RuntimeError('Archive check failed. ' + detail + '\nLog: ' + check_log)
        with open(report_path, 'r') as handle: report = json.load(handle)
        self.message(report['summary'])
        answer = [False]
        self.archive_report = report
        def display():
            area = JTextArea(report['summary'], 18, 85)
            area.setEditable(False);area.setLineWrap(True);area.setWrapStyleWord(True)
            view = JPanel(BorderLayout(5, 5))
            view.add(JScrollPane(area), BorderLayout.CENTER)
            # Offer all historical members available at every station, retaining
            # only the synthetic members the operator already selected.
            available = sorted(set(report.get('available_years', [])) |
                               (set(report.get('selected_members', [])) & set([3000, 3001, 3002, 3003])))
            groups = []
            for member in available:
                if groups and member == groups[-1][-1] + 1: groups[-1].append(member)
                else: groups.append([member])
            member_text = ','.join(str(group[0]) if len(group) == 1 else
                                   str(group[0]) + '-' + str(group[-1]) for group in groups)
            selection = JTextField(member_text if report.get('available_years') else '', 55)
            selection.setEditable(False)
            copy_row = JPanel(BorderLayout(5, 5))
            copy_row.add(JLabel('Available members to paste into ResSim:'), BorderLayout.NORTH)
            copy_row.add(selection, BorderLayout.CENTER)
            def copy_members(event):
                selection.selectAll();selection.copy();selection.requestFocusInWindow()
            copy_row.add(JButton('Copy members', actionPerformed=copy_members), BorderLayout.EAST)
            view.add(copy_row, BorderLayout.SOUTH)
            if report.get('import_complete'):
                JOptionPane.showMessageDialog(self.frame, view, 'IMPORT COMPLETE - paste members into the alternative editor before computing', JOptionPane.INFORMATION_MESSAGE)
            elif extract and report['compatible']:
                self.message('Check passed. Waiting for Extract inputs or Cancel; no inputs have been imported yet.')
                answer[0] = JOptionPane.showOptionDialog(self.frame, view,
                    'Ready to extract - close Simulation windows/DSS views and finish computes first',
                    JOptionPane.DEFAULT_OPTION, JOptionPane.WARNING_MESSAGE, None,
                    ['Extract inputs', 'Cancel'], 'Extract inputs') == 0
                if not answer[0]: self.message('Extraction cancelled. No inputs imported.')
            else:
                if extract:
                    self.message('EXTRACTION NOT STARTED: archive check requires changes. Correct the archive/date/OSI errors shown in the report, then retry. Alternative member settings are not required before extraction.')
                JOptionPane.showMessageDialog(self.frame, view, 'Extraction not started - changes required' if extract else 'Archive dates / ensemble members',
                    JOptionPane.INFORMATION_MESSAGE if report['compatible'] else JOptionPane.WARNING_MESSAGE)
        self.archive_report_display = display
        SwingUtilities.invokeAndWait(Call(display))
        return answer[0]

    def wait_for_job(self, process, log_path):
        # Keep the detailed log, and mirror it to the GUI while the child runs.
        offset = 0
        while True:
            if os.path.isfile(log_path):
                with open(log_path, 'r') as handle:
                    handle.seek(offset)
                    update = handle.read()
                    offset = handle.tell()
                if update: self.message(update.rstrip())
            if not process.isAlive():
                # A final pass catches output written immediately before exit.
                with open(log_path, 'r') as handle:
                    handle.seek(offset); update = handle.read()
                if update: self.message(update.rstrip())
                return process.waitFor()
            Thread.sleep(300)

    def run(self, title, job, simulation, alternative, run_type):
        try:
            filename = os.path.join(scripts, 'standalone_jobs.py')
            if not os.path.isfile(filename): raise RuntimeError('Install the updated standalone workflow first.')
            directory = os.path.join(root, 'standalone-workflow-logs')
            if not os.path.isdir(directory): os.makedirs(directory)
            self.log = os.path.join(directory, 'job-' + str(System.currentTimeMillis()) + '.log')
            self.message(title + '\nLog: ' + self.log)
            if job in ('archive-check','archive-extract'):
                if not self.archive_check(simulation, alternative, run_type, job == 'archive-extract'): return
            self.message('IMPORTING INPUTS: extraction is running. Progress is written to ' + self.log + '. Wait for IMPORT COMPLETE before computing or starting another job.' if job == 'archive-extract' else 'Running ' + title + '. Log: ' + self.log)
            command = ArrayList()
            for arg in [python, '-u', filename, '--watershed', root, '--simulation', simulation,
                        '--alternative', alternative, '--run-type', run_type, '--job', job]: command.add(arg)
            builder = ProcessBuilder(command)
            builder.directory(File(scripts))
            builder.redirectErrorStream(True)
            builder.redirectOutput(File(self.log))
            code = self.wait_for_job(builder.start(), self.log)
            if code != 0:
                with open(self.log, 'r') as handle:
                    self.message(''.join(handle.readlines()[-12:]))
                raise RuntimeError(title + ' exited with code ' + str(code) + '. See ' + self.log)
            if job == 'archive-extract':
                self.archive_report['import_complete'] = True
                SwingUtilities.invokeAndWait(Call(self.archive_report_display))
            self.message('IMPORT COMPLETE: archived ensemble inputs imported successfully. Compute remains manual in ResSim.' if job == 'archive-extract' else 'Finished. Compute remains manual in ResSim.')
        except Exception as error:
            self.message('FAILED: ' + str(error))
            if job in ('archive-check','archive-extract'):
                detail = str(error)
                SwingUtilities.invokeLater(Call(lambda: JOptionPane.showMessageDialog(self.frame, detail, 'Archive check / extraction failed', JOptionPane.WARNING_MESSAGE)))
        finally:
            self.busy = False

SwingUtilities.invokeLater(Call(Menu))
