/* Exercise Jython's Java reflection against the confirmed ResSim API shape.
 * This fixture contains no HEC code. Pass the watershed scripts directory.
 */
import java.util.*;
import org.python.util.PythonInterpreter;
public class ReloadModeProbe {
    public static class b {}
    public static class EnsembleAltPluginData {
        private final boolean enabled;
        public EnsembleAltPluginData(boolean enabled) {this.enabled = enabled;}
        public boolean useMultithreadedCompute() {return enabled;}
    }
    public static class Alternative {
        private final boolean enabled;
        public Alternative(boolean enabled) {this.enabled = enabled;}
        public Object getComputeLauncher() {return new b();}
        public List<EnsembleAltPluginData> getPluginDataList() {
            return Collections.singletonList(new EnsembleAltPluginData(enabled));
        }
    }
    public static void main(String[] args) {
        try (PythonInterpreter interpreter = new PythonInterpreter()) {
            interpreter.set("scripts_path", args[0]);
            interpreter.exec("import sys\nsys.path.insert(0, scripts_path)\nfrom NWDJyLib import cLoadModules\n");
            for (boolean enabled : new boolean[]{false, true}) {
                interpreter.set("alternative", new Alternative(enabled));
                interpreter.set("expected_mode", enabled ? "parallel" : "serial");
                interpreter.exec("mode, reason = cLoadModules._computeReloadMode(None, alternative)\nassert mode == expected_mode, (mode, reason)\nassert cLoadModules._effectiveReload(True, mode) == (mode == 'serial')\nprint(mode + ': ' + reason)\n");
            }
        }
    }
}
