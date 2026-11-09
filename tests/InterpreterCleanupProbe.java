/* Standalone Jython cleanup reproducer. No HEC code or data is used.
 * Run with Java source-file mode and the Jython 2.7.3 standalone JAR.
 * No arguments reproduces the wait; pass watershed scripts/ to test the fix.
 */
import org.python.core.PySystemState;
import org.python.util.PythonInterpreter;
import java.util.concurrent.*;
public class InterpreterCleanupProbe {
  public static void main(String[] args) throws Exception {
    final PySystemState shared = new PySystemState();
    PythonInterpreter primer = new PythonInterpreter(null, shared);
    primer.exec("import logging\n");
    if (args.length > 0) {
      primer.set("scripts_path", args[0]);
      primer.exec("import sys\nsys.path.insert(0, scripts_path)\nfrom NWDJyLib import cLoadModules\n");
    }
    final CountDownLatch imported = new CountDownLatch(1);
    final CountDownLatch release = new CountDownLatch(1);
    ExecutorService workers = Executors.newFixedThreadPool(2, r -> {Thread t = new Thread(r); t.setDaemon(false);return t;});
    workers.submit(() -> {
      PythonInterpreter first = new PythonInterpreter(null, shared);
      first.exec("import logging\nlogging.warning('worker registered')\n");
      imported.countDown();
      try {release.await();} catch(InterruptedException e) {Thread.currentThread().interrupt();}
    });
    if (!imported.await(15, TimeUnit.SECONDS)) throw new RuntimeException("Import did not finish");
    Future<?> cleanup = workers.submit(() -> {
      PythonInterpreter second = new PythonInterpreter(null, shared);
      second.exec("x = 1\n");
      second.close();
    });
    boolean timedOut = false;
    try {
      cleanup.get(3, TimeUnit.SECONDS);
      System.out.println("Cleanup completed");
    } catch (TimeoutException e) {
      timedOut = true;
      System.out.println("Cleanup is waiting; relevant stacks:");
      for (java.util.Map.Entry<Thread,StackTraceElement[]> item : Thread.getAllStackTraces().entrySet()) {
        for (StackTraceElement frame:item.getValue()) {
          if(frame.getClassName().contains("PythonInterpreter")) {
            System.out.println(item.getKey());
            for(StackTraceElement f:item.getValue()) System.out.println("  "+f);
            break;
          }
        }
      }
    } finally {release.countDown();workers.shutdownNow();}
    if (args.length > 0 && timedOut) throw new AssertionError("Fix did not prevent cleanup wait");
    if (args.length == 0 && !timedOut) throw new AssertionError("Control did not reproduce cleanup wait");
  }
}
