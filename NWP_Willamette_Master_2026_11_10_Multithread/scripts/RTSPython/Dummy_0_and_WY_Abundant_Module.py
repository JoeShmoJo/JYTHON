

from dss3 import dss_datetimes
import os
import hashlib
import shutil
import tempfile
import uuid
import urllib3
import requests
import numpy as np
import pandas as pd
from datetime import timezone

import cwms
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer

import CONFIG as cfg
from pathlib import Path
from typing import Dict, Tuple, List
# reload CONFIG to pick up changes without restarting kernel (optional, for interactive dev)
import importlib
importlib.reload(cfg)

# ============================================================
# DEFINE SIMULATION NAME (explicit override)
# ============================================================

SIM_NAME = cfg.SIM_NAME          # <-- set your simulation name here



sim_dir = SIM_NAME.replace(" ", "_")

# ============================================================
# SCRIPT LOCATION
# ============================================================

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# ============================================================
# BUILD RELATIVE PATH FROM SCRIPT LOCATION
# Go up one directory from script, then:
#    rss/<simulation_name>/simulation.dss
# ============================================================

DSS_PATH = (
    SCRIPT_DIR.parent.parent
    / "rss"
    / sim_dir
    / "simulation.dss"
).resolve()   # <-- forces full absolute path

from extraction_context import load_context
CONTEXT = load_context()
if CONTEXT is not None:
    DSS_PATH = CONTEXT.dss_path

DSS_FILE_OUT = str(getattr(cfg, 'DSS_FILE_OUT', DSS_PATH))

print("DSS_FILE_OUT:", DSS_FILE_OUT)


def _write_series(fid, pathname: str, series: pd.Series, units: str, interval_min: int, dss_type: str, decimals: int = 2):
    if series is None or series.empty:
        return False

    series = series.sort_index()
    start_dt = series.index[0].strftime("%d%b%Y %H%M").upper()

    _tsc_arguments = {}
    _tsc_arguments['pathname'] = pathname
    _tsc_arguments['start_time'] = start_dt
    _tsc_arguments['count'] = len(series)
    _tsc_arguments['data_units'] = units
    _tsc_arguments['data_type'] = dss_type
    _tsc_arguments['interval'] = interval_min
    values = series.to_numpy(dtype="float64")
    _tsc_arguments['values'] = values if decimals is None else np.round(values, decimals)


    tsc = TimeSeriesContainer(**_tsc_arguments)
    fid.put_ts(tsc)
    return True

def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_dummy_series(fid, pathname):
    parts = pathname.split("/")
    parts[4] = "*"
    records = sorted(fid.search_path("/".join(parts)))
    pieces = []
    for record in records:
        ts = fid.read_ts(record)
        values = np.asarray(ts.values, dtype="float64")
        valid = np.isfinite(values) & (np.abs(values) < 1e30)
        # These generated daily series use small exact values. Refuse to
        # silently reduce precision if an unexpected study series is present.
        if not np.array_equal(values[valid], values[valid].astype("float32").astype("float64")):
            raise ValueError("Dummy series has values requiring double precision: " + record)
        values = values.copy()
        values[~valid] = np.nan
        pieces.append(pd.Series(values, index=pd.DatetimeIndex(dss_datetimes(ts))))
    if not pieces:
        return records, pd.Series(dtype="float64")
    existing = pd.concat(pieces).sort_index()
    if existing.index.has_duplicates:
        raise ValueError("Overlapping dummy record timestamps: " + pathname)
    return records, existing


def _replace_dummy_series(dss_path, updates):
    """Rebuild only generated records on a verified copy, never the live DSS.

    pydsstools 2.4 writes regular series as floats and cannot overwrite the
    existing double-precision blocks in-place. Keep out-of-window data and
    unrelated records; retain a full backup before publishing the staged file.
    Run only while native compute/extraction is stopped.
    """
    target = Path(dss_path)
    if not target.is_file():
        raise FileNotFoundError("Simulation DSS missing: " + str(target))
    before = _file_digest(target)
    with tempfile.TemporaryDirectory(prefix="dummy-write-", dir=str(target.parent)) as directory:
        original = Path(directory) / "original.dss"
        staged = Path(directory) / "staged.dss"
        shutil.copy2(target, original)
        if _file_digest(original) != before:
            raise RuntimeError("Simulation DSS changed while copying; stop compute/extraction and retry")
        shutil.copy2(original, staged)
        expected = []
        with HecDss.Open(str(staged)) as fid:
            for pathname, update, units in updates:
                records, existing = _read_dummy_series(fid, pathname)
                merged = existing.reindex(existing.index.union(update.index)).sort_index()
                merged.loc[update.index] = update.to_numpy()
                # Delete only these generated records, only on the staged copy.
                for record in records:
                    fid.del_path(record)
                # Missing-value padding returned by DSS reads can be large.
                # Trim padding without removing valid out-of-window history.
                first, last = merged.first_valid_index(), merged.last_valid_index()
                merged = merged.loc[first:last]
                if not (merged.index.to_series().diff().dropna() == pd.Timedelta(days=1)).all():
                    raise ValueError("Dummy series must have a continuous daily index: " + pathname)
                values = merged.to_numpy(copy=True)
                values[np.isnan(values)] = -3.4028234663852886e38
                stored = pd.Series(values, index=merged.index)
                _write_series(fid, pathname, stored, units, 1440, "INST-VAL", decimals=None)
                expected.append((pathname, merged))
        # Reopen the staged DSS and verify values and coverage before replacing.
        with HecDss.Open(str(staged)) as fid:
            for pathname, wanted in expected:
                _, actual = _read_dummy_series(fid, pathname)
                if not wanted.index.isin(actual.index).all():
                    raise RuntimeError("Staged dummy coverage verification failed: " + pathname)
                if not np.array_equal(actual.reindex(wanted.index).to_numpy(),
                                      wanted.to_numpy(), equal_nan=True):
                    raise RuntimeError("Staged dummy value verification failed: " + pathname)
        if _file_digest(target) != before:
            raise RuntimeError("Simulation DSS changed during staging; no replacement made")
        backups = target.parent / "dummy-input-backups"
        backups.mkdir(exist_ok=True)
        backup = backups / ("simulation-before-dummy-" + uuid.uuid4().hex + ".dss")
        shutil.copy2(original, backup)
        if _file_digest(backup) != before:
            raise RuntimeError("Backup verification failed; no replacement made")
        if _file_digest(target) != before:
            raise RuntimeError("Simulation DSS changed before replacement; no replacement made")
        os.replace(staged, target)
        print("Pre-write DSS backup:", backup, flush=True)


# =====================================================================
# WRITE DUMMY RECORDS TO forecast.dss
# =====================================================================

def write_dummy_records():
    # Use your already constructed DSS_FILE_OUT
    dss_path = DSS_FILE_OUT

    # Anchor at UTC midnight, strip timezone for DSS
    window = getattr(cfg, 'SIMULATION_WINDOW', None)
    if window:
        start = pd.Timestamp(window['lookback']).floor('D') - pd.Timedelta(days=1)
        end = pd.Timestamp(window['end']).ceil('D') + pd.Timedelta(days=1)
    else:
        today = pd.Timestamp.utcnow().normalize()
        start = (today - pd.Timedelta(days=365)).tz_localize(None)
        end = (today + pd.Timedelta(days=365)).tz_localize(None)

    if CONTEXT:
        start = pd.Timestamp(CONTEXT.lookback).normalize() - pd.Timedelta(days=1)
        end = pd.Timestamp(CONTEXT.end).normalize() + pd.Timedelta(days=1)

    # -----------------------------------------------------------------
    # 1) Daily WY_TYPE record (all values = 4)
    # Path: /ALL_ABUNDANT//STOR//1DAY/WY_TYPE/
    # -----------------------------------------------------------------


    wy_path = "/ALL_ABUNDANT//STOR//1DAY/WY_TYPE/"
    daily_index = pd.date_range(start=start, end=end, freq="D")
    wy_series = pd.Series(4.0, index=daily_index)

    # -----------------------------------------------------------------
    # 2) Hourly ZERO flow record (all values = 0)
    # Path: /ZERO/ZERO/FLOW//1HOUR/DUMMY/
    # -----------------------------------------------------------------
    zero_path = "/ZERO/ZERO/FLOW//1DAY/DUMMY/"
    daily_index = pd.date_range(start=start, end=end, freq="D")
    zero_series = pd.Series(0.0, index=daily_index)

    # -----------------------------------------------------------------
    # Write to DSS
    # -----------------------------------------------------------------
    _replace_dummy_series(dss_path, [
        (wy_path, wy_series, "UNSPEC"),
        (zero_path, zero_series, "CFS"),
    ])

    print("Dummy records written to:")
    print(dss_path)
    print(f"{wy_path}  ({start.date()} -> {end.date()})")
    print(f"{zero_path} ({start.date()} -> {end.date()})")

if __name__ == "__main__":
    write_dummy_records()
    if CONTEXT:
        from write_ensemble_dummies import copy_dummies
        copy_dummies(DSS_FILE_OUT)
