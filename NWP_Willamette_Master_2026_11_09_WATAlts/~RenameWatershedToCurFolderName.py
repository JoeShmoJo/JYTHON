# Utility script to rename a watershed
# Basically, all you need to do is rename the base watershed folder
# to the name you want, and then just run this script through Python
# It will rename the .sty, .wksp, and .log files and update the text inside
# (also updates the .bak files)
# them at the top lines to use the new names
# This cuts down the multi-step process that renaming a watershed normally is 
# Make sure the watershed is closed when you run this script
# - RAA 2/5/2021: updated to run with both Python 2 and 3
# - RAA 8/4/2021 added functionality to run this script via .bat file

import os
import sys
import time

if os.path.dirname(__file__) != os.getcwd():
    print("Assuming that this is running via batch file. Changing current working directory to directory of this script")
    os.chdir(os.path.dirname(__file__))
    batchRun = True
else:
    batchRun = False
print("Current working directory: %s" %(os.getcwd()))

def replaceAndRename(origStub, newStub, extension):
    # replace all the contents of a file where "origStub" had been with "newStub"
    # and then rename the file from origStub to newStub
    # extension is the file extension
    fileObj = open(origStub+extension,"r")
    fileContents = str(fileObj.read())
    newContents = str(fileContents)
    newContents = newContents.replace(origStub, newStub)
    fileObj.close()
    fileObj = open(origStub+extension,"w")
    fileObj.write(newContents)
    fileObj.close() 
    # need to rename the file
    os.rename(origStub+extension, newStub+extension)    

print("start")
extensions = [".wksp", ".sty", ".log", ".projection", ".wtrshd"]
curDir = os.path.dirname(sys.argv[0]) + "\\"
newName = curDir.split("\\")[-2] # the new watershed name (the folder name)
for f in os.listdir(curDir): # loop through all files in the directory
    try:
        ext = "." + f.split(".")[-1] # e.g. ".py"
    except:
        continue # the filename is too short
    if ext in extensions:
        oldName = f.split(".")[0]
        try:
            replaceAndRename(oldName, newName, ext)
        except Exception as e:
            print("exception!")
            print(type(e))
            raise e
        print("\nReplaced file: ", f)
        # try to repeat for .bak files if they exist
        try:
            replaceAndRename(oldName, newName, ext + ".bak")
            print("replaced .bak file as well")
        except:
            print("could not replace .bak file")
            pass
logFileName = os.path.join(curDir, "watershedChangeLog.md")
logFile = open(logFileName, 'a')
logFile.write("\n\n# `%s` [%s / %s]\n" % (newName, time.strftime("%d %b %Y %H:%M"), os.environ["USERNAME"]))
logFile.close()
os.system("notepad.exe %s" % logFileName)

if not batchRun:
    print("done")
    os.system("pause")