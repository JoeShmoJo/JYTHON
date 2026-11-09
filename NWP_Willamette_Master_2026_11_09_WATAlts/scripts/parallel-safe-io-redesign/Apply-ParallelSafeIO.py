"""Apply a reversible Java-NIO I/O redesign test to the standalone watershed.

This patch avoids Jython PyFile open/read/close/write operations in the
native ensemble-worker path. It does not modify application JARs, DSS files,
CSV values, model alternatives, or the native executor pool.
"""
from __future__ import print_function

from datetime import datetime
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(
    r"C:\Projects\FIRO\watershed"
    r"\NWP_Willamette_Master_2026_10_21_RTS_V2"
)
SCRIPTS = ROOT / "scripts"
STAGE = SCRIPTS / "parallel-safe-io-redesign"

CFILE = SCRIPTS / "NWDJyLib" / "cFile.py"
RUNTIME = SCRIPTS / "standalone_baseline_runtime.py"
ALT_SETUP = SCRIPTS / "externalSVs" / "Alternative_Setup.py"
CONTROLLER = SCRIPTS / "externalSVs" / "ControllerExternalSV.py"

CONTROLLER_ORIGINAL = (
    SCRIPTS
    / "parallel-init-mitigation-test"
    / "backup-20261021T092451"
    / "ControllerExternalSV.py.original"
)


def normalize(value):
    return value.replace("\r\n", "\n").replace("\r", "\n")


def read_text(path):
    return normalize(path.read_text(encoding="utf-8-sig"))


def replace_once(text, old, new, label):
    old = normalize(old)
    new = normalize(new)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "{}: expected one matching block, found {}.".format(label, count)
        )
    return text.replace(old, new, 1)


def replace_section(text, start_marker, end_marker, replacement, label):
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("{}: start marker not found.".format(label))
    end = text.find(end_marker, start)
    if end < 0 or end <= start:
        raise RuntimeError("{}: end marker not found.".format(label))
    return text[:start] + normalize(replacement) + text[end:]


def digest_file(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_manifest(folder, name, paths):
    data = {}
    for path in paths:
        data[str(path.name)] = digest_file(path)
    (folder / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


for path in (CFILE, RUNTIME, ALT_SETUP):
    if not path.is_file():
        raise RuntimeError("Required source file is missing: {}".format(path))

STAGE.mkdir(parents=True, exist_ok=True)

# Restore the controller from the broad-lock test before this I/O test.
if CONTROLLER_ORIGINAL.is_file():
    shutil.copy2(str(CONTROLLER_ORIGINAL), str(CONTROLLER))

controller_text = read_text(CONTROLLER)
if "_PARALLEL_INIT_LOCK" in controller_text:
    raise RuntimeError(
        "ControllerExternalSV still has the prior lock test installed. "
        "Restore it before applying this redesign."
    )

cfile = read_text(CFILE)
runtime = read_text(RUNTIME)
alt_setup = read_text(ALT_SETUP)

if "parallelSafeReadText" in cfile:
    raise RuntimeError("cFile.py already contains a parallel-safe I/O patch.")

stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
backup = STAGE / ("backup-parallel-safe-io-" + stamp)
backup.mkdir()

for path in (CFILE, RUNTIME, ALT_SETUP, CONTROLLER):
    shutil.copy2(str(path), str(backup / path.name))

write_manifest(
    backup,
    "before-sha256.json",
    (backup / CFILE.name, backup / RUNTIME.name, backup / ALT_SETUP.name, backup / CONTROLLER.name),
)

# ---------------------------------------------------------------------
# cFile.py: central Java-NIO reader/writer/digest helpers.
# ---------------------------------------------------------------------
cfile = replace_once(
    cfile,
    "import shutil\n",
    """import shutil
from java.nio.file import Files, Paths
from java.lang import String as JavaString
from java.security import MessageDigest
""",
    "cFile imports",
)

cfile = replace_section(
    cfile,
    "def fileOpenReadClose(txtFileName):",
    "def stripOutCommentLines(txtLines):",
    r'''# Parallel-safe helpers. Java NIO avoids Jython PyFile closer handling
# while native ensemble worker threads initialize scripts and rules.
def _parallelSafeEncoding(encoding):
    value = str(encoding or 'UTF-8').upper().replace('_', '-')
    if value == 'UTF-8-SIG':
        return 'UTF-8'
    return value

def parallelSafeReadText(txtFileName, encoding='UTF-8'):
    if not os.path.exists(txtFileName):
        raise AssertionError("File does not exist: \n%s" % txtFileName)
    raw = Files.readAllBytes(Paths.get(str(txtFileName)))
    text = unicode(JavaString(raw, _parallelSafeEncoding(encoding)))
    if text.startswith(u'\ufeff'):
        text = text[1:]
    return text

def parallelSafeReadTextLines(txtFileName, encoding='UTF-8'):
    return parallelSafeReadText(txtFileName, encoding).splitlines(True)

def parallelSafeDigest(txtFileName):
    if not os.path.exists(txtFileName):
        raise AssertionError("File does not exist: \n%s" % txtFileName)
    digest = MessageDigest.getInstance('SHA-256')
    digest.update(Files.readAllBytes(Paths.get(str(txtFileName))))
    return ''.join('%02x' % (value & 0xff) for value in digest.digest())

def parallelSafeWriteText(txtFileName, text, encoding='UTF-8'):
    target = Paths.get(str(txtFileName))
    parent = target.getParent()
    if parent is not None:
        Files.createDirectories(parent)
    Files.write(
        target,
        JavaString(unicode(text)).getBytes(_parallelSafeEncoding(encoding))
    )
    return None

def fileOpenReadClose(txtFileName):
    """Read text lines through Java NIO instead of Jython PyFile."""
    return parallelSafeReadTextLines(txtFileName, 'UTF-8')

def fileOpenReadCloseWithEncoding(txtFileName, encoding):
    """Read encoded text lines through Java NIO instead of Jython PyFile."""
    return parallelSafeReadTextLines(txtFileName, encoding)

''',
    "cFile read functions",
)

cfile = replace_section(
    cfile,
    "def writeTextToFile(msg, txtFileName):",
    "def getCSVReader(txtLines):",
    r'''def writeTextToFile(msg, txtFileName):
    """Write text through Java NIO instead of Jython PyFile."""
    if isinstance(msg, list):
        msg = ''.join(msg)
    parallelSafeWriteText(txtFileName, msg, 'UTF-8')
    return None

''',
    "cFile writeTextToFile",
)

# ---------------------------------------------------------------------
# standalone_baseline_runtime.py: no worker-side PyFile reads/writes.
# ---------------------------------------------------------------------
runtime = replace_once(
    runtime,
    "import uuid\n",
    """import uuid
from NWDJyLib.cFile import (
    parallelSafeDigest,
    parallelSafeReadText,
    parallelSafeWriteText,
)
""",
    "baseline runtime imports",
)

runtime = replace_section(
    runtime,
    "def digest(path):",
    "def active(network):",
    r'''def digest(path):
    return parallelSafeDigest(path)

def read_json(path):
    return json.loads(parallelSafeReadText(path, 'UTF-8'))

''',
    "baseline runtime digest",
)

runtime = replace_once(
    runtime,
    """            with open(marker) as handle:
                pointer = json.load(handle)
""",
    """            pointer = read_json(marker)
""",
    "baseline pointer read",
)

runtime = replace_once(
    runtime,
    """                with open(filename) as handle:
                    data = json.load(handle)
""",
    """                data = read_json(filename)
""",
    "baseline resolved configuration read",
)

runtime = replace_section(
    runtime,
    "        # Unique immutable receipts avoid concurrent reservoir writes colliding.",
    "    return outcome",
    r'''        # Unique immutable receipts avoid concurrent writes colliding.
        # Java NIO avoids Jython PyFile close handling in native worker threads.
        receipt = {
            'configuration_id': pointer['id'],
            'member': int(match.group(1)) if match else None,
            'output_fpart': str(network.getRssRun().getOutputFPart()),
            'module': module_name,
            'resolved_sha256': pointer['resolved_sha256'],
        }
        parallelSafeWriteText(
            os.path.join(directory, uuid.uuid4().hex + '.json'),
            json.dumps(receipt, sort_keys=True),
            'UTF-8'
        )
''',
    "baseline initialization receipt",
)

# ---------------------------------------------------------------------
# Alternative_Setup.py: remove direct PyFile reads/writes and double-close.
# ---------------------------------------------------------------------
alt_setup = replace_once(
    alt_setup,
    "from externalSVs.baseExternalSV import ExternalSV\n",
    """from externalSVs.baseExternalSV import ExternalSV
from NWDJyLib.cFile import (
    parallelSafeReadText,
    parallelSafeReadTextLines,
    parallelSafeWriteText,
)
""",
    "Alternative_Setup imports",
)

alt_setup = replace_section(
    alt_setup,
    "        wsDefaults = open(wsDefaultSetupConfig, 'r')",
    "        ## read alternative-specific file",
    r'''        wsConfigList = parallelSafeReadTextLines(
            wsDefaultSetupConfig,
            'UTF-8'
        )

''',
    "default alternative configuration read",
)

alt_setup = replace_section(
    alt_setup,
    "        if os.path.exists(altSetupConfig):",
    "        else:\n            network.printWarningMessage",
    r'''        if os.path.exists(altSetupConfig):
            altConfigList = parallelSafeReadTextLines(altSetupConfig, 'UTF-8')
            # Check if aliased alternative, if so read the target file.
            if altConfigList and altConfigList[0][0:6] == "@alias":
                aliasAlt = altConfigList[0].split(" ")[1].strip()
                altSetupConfig = network.makeAbsolutePathFromWatershed(
                    "scripts/alt_config/%s.txt" % aliasAlt
                )
                network.printMessage(
                    "Using aliased alternative file: %s" % altSetupConfig
                )
                self.printLogMessage(
                    "Using aliased alternative file: %s" % altSetupConfig
                )
                altConfigList = parallelSafeReadTextLines(
                    altSetupConfig,
                    'UTF-8'
                )
''',
    "alternative configuration read",
)

alt_setup = replace_section(
    alt_setup,
    "        # Write output to JSON file",
    "\ndef fileToString(fName):",
    r'''        # Write output through Java NIO instead of Jython PyFile.
        try:
            modelReportValues = json.dumps(
                modelReportValues,
                sort_keys=True,
                indent=4,
                separators=(',', ':')
            )
            parallelSafeWriteText(reportName, modelReportValues, 'UTF-8')
        except:
            network.printErrorMessage(
                "Unable to write modelReport file: %s" % reportName
            )

''',
    "Alternative_Setup model report",
)

alt_setup = replace_section(
    alt_setup,
    "def fileToString(fName):",
    "def parseConfigListJSON(configList):",
    r'''def fileToString(fName):
    if os.path.exists(fName):
        return parallelSafeReadText(fName, 'UTF-8')
    return ""

''',
    "Alternative_Setup fileToString",
)

# Validate all intended replacements before touching source files.
for text, required, label in (
    (cfile, "def parallelSafeReadText", "cFile Java-NIO reader"),
    (cfile, "def parallelSafeDigest", "cFile Java-NIO digest"),
    (cfile, "def parallelSafeWriteText", "cFile Java-NIO writer"),
    (runtime, "def read_json(path):", "baseline JSON reader"),
    (runtime, "parallelSafeWriteText(", "baseline receipt writer"),
    (alt_setup, "wsConfigList = parallelSafeReadTextLines(", "Alternative_Setup config reader"),
    (alt_setup, "parallelSafeWriteText(reportName", "Alternative_Setup report writer"),
):
    if required not in text:
        raise RuntimeError("Validation failed: {}".format(label))

# Syntax validation only; imports are not executed.
compile(cfile, str(CFILE), "exec")
compile(runtime, str(RUNTIME), "exec")
compile(alt_setup, str(ALT_SETUP), "exec")

CFILE.write_text(cfile, encoding="utf-8")
RUNTIME.write_text(runtime, encoding="utf-8")
ALT_SETUP.write_text(alt_setup, encoding="utf-8")

write_manifest(
    backup,
    "after-sha256.json",
    (CFILE, RUNTIME, ALT_SETUP, CONTROLLER),
)

steps = [
    "Parallel-Safe Java NIO I/O Redesign Test",
    "Created: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    "",
    "Changed files:",
    str(CFILE),
    str(RUNTIME),
    str(ALT_SETUP),
    "",
    "Changes:",
    "1. Replaced cFile read helpers with Java NIO reads.",
    "2. Added Java NIO SHA-256 and text-write helpers.",
    "3. Replaced baseline configuration/hash/receipt PyFile operations.",
    "4. Replaced Alternative_Setup config/report PyFile operations.",
    "5. Removed the normal-path duplicate Alternative_Setup close behavior.",
    "",
    "Not changed:",
    "No application JAR.",
    "No native executor or worker-state patch.",
    "No DSS file.",
    "No CSV contents.",
    "No alternative selection.",
    "No ControllerExternalSV initialization lock.",
    "",
    "Backup: {}".format(backup),
    "",
    "Required validation:",
    "1. Restart ResSim.",
    "2. Run a serial regression compute.",
    "3. Restart ResSim again.",
    "4. Run exactly two parallel members.",
    "5. Do not accept/archive test results.",
]
(STAGE / "PARALLEL_SAFE_IO_TEST_STEPS.txt").write_text(
    "\n".join(steps) + "\n",
    encoding="utf-8"
)

print("Parallel-safe Java NIO I/O redesign installed for testing only.")
print("Backup:", backup)
print("Steps:", STAGE / "PARALLEL_SAFE_IO_TEST_STEPS.txt")
print("Restart ResSim before testing.")