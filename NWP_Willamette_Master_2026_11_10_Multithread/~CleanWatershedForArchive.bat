REM Adapted from EventDataSummaryTool's edst.bat file
REM Launches Jython interpreter and runs a Jython script
REM ..\JavaRuntime64\bin\java.exe                       # launch JVM
REM -Djava.library.path=lib                             # tell JVM to load DLLs from lib directory
REM -cp "jar/*;jar/sys/*;jar/ext/*;jar/sys/jython.jar"  # set classpath, jython last
REM org.python.util.jython                              # tell JVM to run Jython interpreter
REM -Dpython.console=                                   # disable jline library for ACEIT/security incompatibility
REM -Dpython.path="jar\sys\jythonLib.jar\lib"           # point to the jythonLib.jar file for the python.path variable
REM ^                                                   # continues current command on next line
REM "path_to_script.py"                                 # file path to Jython script

REM Make sure to call the setupJython batch file so that control returns to the caller (this batch file) after running the setupJython batch file
REM Use pause at the end of this script to keep command line window open after script execution (any key will close window)
REM Alternative command instead of pause: cmd /k (Downside: will need to manually exit the window)

setlocal enabledelayedexpansion
set runDirectory=%CD%

call "%runDirectory%\setupJython.bat"

..\JavaRuntime64\bin\java.exe -Djava.library.path=lib -cp "jar/*;jar/sys/*;jar/sys/excel/*;jar/ext/*;jar/sys/jython.jar" org.python.util.jython -Dpython.console= -Dpython.path="jar\sys\jythonLib.jar\lib" ^
"%runDirectory%\~CleanWatershedForArchive.py"

pause