# Utility script to pop open the change log that should be populated
# when a watershed is getting ready to be archived.
# Pops up a new row with the current timestamp, watershed name, and username

import os
import sys
import time

if os.path.dirname(__file__) != os.getcwd():
    print("Assuming that this is running via batch file. Changing current working directory to directory of this script")
    os.chdir(os.path.dirname(__file__))
print("Current working directory: %s" %(os.getcwd()))

curDir = os.path.dirname(sys.argv[0]) + "\\"
newName = curDir.split("\\")[-2] # the new watershed name (the folder name)
logFileName = os.path.join(curDir, "watershedChangeLog.md")
logFile = open(logFileName, 'a')
logFile.write("\n\n# `%s` [%s / %s]\n" % (newName, time.strftime("%d %b %Y %H:%M"), os.environ["USERNAME"]))
logFile.close()
os.system("notepad.exe %s" % logFileName)

print("done")
os.system("pause")