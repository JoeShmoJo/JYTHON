# Utility script to:
# 1) Delete alt directories and .dss output files from the /runs/ directory.
# 2) delete simulations that are not in the "wy ResSimOnly" or "FRA_*" analysis periods
# This is a good thing to do before packaging up your watershed to send to someone else.  This does not
# descriminate between alternatives, so use it carefully.  It is also a useful tool for cleaning up
# watersheds before recreating simulations with the ~WATSimulationCreator script.
# To use, double click and let run.  If you want to use the output, rename the $WATERSHED.sty.fraOnly 
# study file to $WATERSHED.sty.  All this does is modify the .sty file and create the .fraOnly version.
# This script DOES NOT delete the .simulation and .container files in  /wat/sims/ associated, so you 
# may need to manually delete them.
#
# - EAH 3/8/2016 (with help from KAR and KBD)
#
# - RAA 8/4/2021 added functionality to run this script via .bat file

from __future__ import with_statement

import os
import sys
import shutil
from glob import glob

if os.path.dirname(__file__) != os.getcwd():
    print("Assuming that this is running via batch file. Changing current working directory to directory of this script")
    os.chdir(os.path.dirname(__file__))
    batchRun = True
else:
    batchRun = False
print("Current working directory: %s" %(os.getcwd()))
alt_directories = []
standaloneComputes = []
# remove alt directories from runs directory.
# FRA directory
fraDirs = glob(".\\runs\\*\\FRA_50year\\")
# Deterministic historical events
histEvents = glob(".\\runs\\*\\wy_*\\")
# Deterministic synthetic events
synthEvents = glob(".\\runs\\*\\*\\*.dss")
alt_directories = fraDirs + histEvents + synthEvents + standaloneComputes
print("Removing runs .dss files.")
for alt in set([r.split("\\")[2] for r in alt_directories]):
    print("\tDeleting %s results" % alt)
    shutil.rmtree(".\\runs\\%s\\" % alt)
# ResSim standalone computes
standaloneComputes = glob(".\\rss\\*\\simulation.dss")
for f in standaloneComputes:
     print("\tDeleting %s" % f)
     os.remove(f)
# hotStart files
rssHotstarts = glob(".\\rss\\hotstarts\\*.dss") + \
               glob(".\\rss\\hotstarts\\*.nhs") + \
               glob(".\\rss\\hotstarts\\*.nhs.bak")
runHotstarts = glob(".\\runs\\*\\*\\hotstarts\\*.*")
for f in rssHotstarts + runHotstarts:
    print("\tDeleting %s" % f)
    os.remove(f)
    
    

if not batchRun:
    print("done")
    os.system("pause")