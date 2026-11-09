"""Read-only parallel-versus-serial Salem FLOW comparison for members 1985/1986."""
from pathlib import Path
from datetime import datetime

from pydsstools.heclib.dss import HecDss

ROOT = Path(
    r"C:\Projects\FIRO\watershed"
    r"\NWP_Willamette_Master_2026_10_21_RTS_V2"
)
RESULTS = ROOT / "scripts" / "parallel-safe-io-redesign" / "results"

parallel_dirs = sorted(
    RESULTS.glob("parallel-two-member-*"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)
serial_dirs = sorted(
    RESULTS.glob("serial-two-member-*"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)

parallel_dss = parallel_dirs[0] / "simulation.dss"
serial_dss = serial_dirs[0] / "simulation.dss"

members = (1985, 1986)

report = RESULTS / (
    "Salem-flow-parallel-vs-serial-"
    + datetime.now().strftime("%Y%m%dT%H%M%S")
    + ".txt"
)

def find_paths(dss, member):
    fpart = "C:{:06d}|Con_Season0".format(member)
    matches = []

    for raw in dss.getPathnameList("/*/*/*/*/*/*/"):
        path = str(raw)
        parts = path.split("/")

        if len(parts) != 8:
            continue

        # /A/B/C/D/E/F/
        if parts[2].strip().upper() != "WILLAMETTE_AT SALEM":
            continue
        if parts[3].strip().upper() != "FLOW":
            continue
        if parts[5].strip().upper() != "1DAY":
            continue
        if parts[6].strip().upper() != fpart.upper():
            continue

        matches.append(path)

    if not matches:
        raise RuntimeError(
            "No Salem daily FLOW paths found for member {}".format(member)
        )

    return sorted(matches)

def metadata(ts):
    return (
        str(getattr(ts, "units", "")),
        str(getattr(ts, "type", "")),
        str(getattr(ts, "interval", "")),
    )

def compare(left, right):
    left_times = list(left.pytimes)
    right_times = list(right.pytimes)

    left_values = list(left.values)
    right_values = list(right.values)

    same_times = left_times == right_times

    if len(left_values) != len(right_values):
        same_values = False
    else:
        same_values = True

        for left_value, right_value in zip(left_values, right_values):
            if left_value == right_value:
                continue

            try:
                if (
                    float(left_value) != float(left_value)
                    and float(right_value) != float(right_value)
                ):
                    continue
            except Exception:
                pass

            same_values = False
            break

    same_series = same_times and same_values
    same_metadata = metadata(left) == metadata(right)

    return (
        same_series and same_metadata,
        same_series,
        same_metadata,
        len(left_values),
    )

lines = [
    "SALEM FLOW: PARALLEL VS SERIAL COMPARISON",
    "Created: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "",
    "Parallel DSS: " + str(parallel_dss),
    "Serial DSS:   " + str(serial_dss),
    "",
]

all_match = True

with HecDss.Open(str(parallel_dss)) as parallel, HecDss.Open(str(serial_dss)) as serial:
    for member in members:
        parallel_paths = find_paths(parallel, member)
        serial_paths = find_paths(serial, member)

        lines.append("MEMBER: " + str(member))

        if parallel_paths != serial_paths:
            all_match = False
            lines.append("RESULT: MISMATCH — different physical DSS path sets")
            lines.append("Parallel paths:")
            lines.extend(parallel_paths)
            lines.append("Serial paths:")
            lines.extend(serial_paths)
            lines.append("")
            continue

        for path in parallel_paths:
            parallel_ts = parallel.read_ts(path)
            serial_ts = serial.read_ts(path)

            matched, same_values, same_meta, samples = compare(
                parallel_ts,
                serial_ts,
            )

            lines.extend([
                "Path: " + path,
                "Samples compared: " + str(samples),
                "Values/timestamps identical: " + str(same_values),
                "Units/type/interval identical: " + str(same_meta),
                "RESULT: " + ("MATCH" if matched else "MISMATCH"),
                "",
            ])

            if not matched:
                all_match = False

report.write_text("\n".join(lines), encoding="utf-8")

print("Report:", report)

if all_match:
    print(
        "RESULT: Salem daily FLOW is identical for members 1985 and 1986 "
        "across all physical DSS blocks."
    )
else:
    print("RESULT: Salem daily FLOW differs; inspect the report.")
    raise SystemExit(1)