# -*- coding: utf-8 -*-
"""
Import smoke test. Run this under ResSim's Jython with ResSim's jars on the
classpath -- see run_smoketest.ps1. No watershed is opened and nothing is
computed, so nothing else in the model gets a chance to fail first.

Two phases:
    1. every Java class the ResSim-side code imports
    2. every ResSim-side module, which exercises those imports for real

Anything that fails prints the exception. Everything that passes prints nothing,
so the output is the list of problems.
"""

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def readList(fileName):
    handle = open(os.path.join(HERE, fileName), "r")
    try:
        names = []
        for line in handle.readlines():
            line = line.strip()
            if line:
                names.append(line)
        return names
    finally:
        handle.close()


def tryImport(name):
    """None if the import worked, otherwise the error text."""
    try:
        __import__(name)
        return None
    except:
        info = sys.exc_info()
        return "%s: %s" %(info[0].__name__, info[1])


def phase(title, names):
    print("")
    print("=== %s (%d) ===" %(title, len(names)))
    failures = []
    for name in names:
        problem = tryImport(name)
        if problem is not None:
            failures.append((name, problem))
            print("  FAIL %s" %name)
            print("       %s" %problem)
    if len(failures) == 0:
        print("  all %d imported cleanly" %len(names))
    return failures


def main():
    print("Jython %s" %sys.version)
    try:
        import java.lang.System as System
        print("Java    %s" %System.getProperty("java.version"))
    except:
        print("Java    could not be determined")

    javaFailures = phase("Java classes", readList("java_classes.txt"))
    moduleFailures = phase("ResSim-side modules", readList("ressim_modules.txt"))

    handle = open(os.path.join(HERE, "smoketest_results.txt"), "w")
    try:
        handle.write("Jython %s\n" %sys.version)
        for label, failures in [("JAVA", javaFailures), ("MODULE", moduleFailures)]:
            for name, problem in failures:
                handle.write("%s\t%s\t%s\n" %(label, name, problem))
    finally:
        handle.close()

    total = len(javaFailures) + len(moduleFailures)
    print("")
    print("%d failure(s). Written to smoketest_results.txt" %total)


main()
