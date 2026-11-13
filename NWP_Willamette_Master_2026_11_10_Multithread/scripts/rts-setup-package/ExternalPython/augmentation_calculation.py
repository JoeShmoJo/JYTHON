"""Existing configurable augmentation calculation, shared with RTS preparation.

Only calculation helpers are loaded; no legacy top-level job is executed.
"""
import ast
import csv
from pathlib import Path
import types
import numpy as np
import pandas as pd
from dss3 import dss_datetimes

def load_functions(source, namespace):
    # Only function definitions: importing the old module would run its entire
    # standalone compute against CONFIG.SIM_NAME and open simulation.dss.
    tree = ast.parse(source.read_text(encoding='utf-8-sig'))
    module = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)], type_ignores=[])
    exec(compile(module, str(source), 'exec'), namespace)
    return types.SimpleNamespace(**namespace)

def read_config(path):
    # Excel-style comment rows may contain commas followed by empty cells.
    # pandas comment='#' can retain their suffix as an apparent header.
    # Locate the actual Variable header using CSV parsing, not line splitting.
    with open(path, encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.reader(handle))
    header_index = next((i for i, row in enumerate(rows)
                         if row and row[0].strip() == 'Variable'), None)
    if header_index is None:
        raise ValueError('No Variable header found in ' + str(path))
    header = [cell.strip() for cell in rows[header_index]]
    while header and not header[-1]:
        header.pop()
    if len(set(header)) != len(header) or any(not cell for cell in header):
        raise ValueError('Empty or duplicate configuration column names')
    records = []
    for row in rows[header_index + 1:]:
        if not row or not row[0].strip() or row[0].lstrip().startswith('#'):
            continue
        if any(cell.strip() for cell in row[len(header):]):
            raise ValueError('Unexpected extra configuration cells: ' + row[0])
        records.append((row[:len(header)] + [''] * len(header))[:len(header)])
    table = pd.DataFrame(records, columns=header).fillna('')
    table['Variable'] = table['Variable'].str.strip()
    if table['Variable'].duplicated().any():
        raise ValueError('Duplicate configuration variables')
    table = table.set_index('Variable')
    aliases, flags, floors, limits, travel = {}, {}, {}, {}, {}
    for name in table.columns:
        aliases[name] = table.loc['Abbreviation', name].strip()
        flags[name] = {}
        for gauge in ('Salem', 'Albany'):
            text = table.loc['Supports' + gauge, name].strip().upper()
            if text not in ('TRUE', 'FALSE'):
                raise ValueError('Invalid Supports{} for {}'.format(gauge, name))
            flags[name][gauge] = text == 'TRUE'
        floors[name] = float(table.loc['MinConStor', name])
        limits[name] = float(table.loc['MaxRelease', name])
        travel[name] = int(table.loc['TravelTimeDays', name])
        if not np.isfinite(floors[name]) or not np.isfinite(limits[name]) or floors[name] < 0 or limits[name] < 0 or travel[name] < 0:
            raise ValueError('Invalid floor, release limit, or travel time for ' + name)
    if len(set(aliases.values())) != len(aliases):
        raise ValueError('Duplicate abbreviations')
    # Current SV applies only to SupportsSalem reservoirs. Do not prepare a
    # scheme that it cannot faithfully consume.
    if any(flags[name]['Salem'] != flags[name]['Albany'] for name in flags):
        raise ValueError('Current model requires identical Salem/Albany supporting reservoirs')
    selected = [name for name in aliases if flags[name]['Salem']]
    if not selected or 'Hills Creek' in selected or 'Lookout Point' not in selected:
        raise ValueError('This version requires Lookout Point/Hills Creek combined, with Hills Creek not independently selected')
    return aliases, flags, floors, limits, travel, selected

def read_series(dss, path, units):
    record = dss.read_ts(path, trim_missing=True)
    actual_units = str(record.data_units).strip().upper()
    if actual_units not in units:
        raise ValueError('{}: unexpected units {}'.format(path, actual_units))
    series = pd.Series(np.asarray(record.values, dtype=float), index=pd.DatetimeIndex(dss_datetimes(record))).sort_index()
    if series.empty or series.index.has_duplicates:
        raise ValueError('Empty series or duplicate timestamps: ' + path)
    return series

def read_water_year_type(dss, path, mode):
    if mode == 'fixed-abundant':
        # The existing ALL_ABUNDANT input is an explicit constant code of 4,
        # exported by this state variable with a storage unit label. It is not
        # a physical acre-foot volume. Require an explicit mode and verify it.
        series = read_series(dss, path, {'MAF', 'STOR-MAF', 'AC-FT', 'ACRE-FT', 'AF', 'ACRE-FEET'})
        if not (series.to_numpy(dtype=float) == 4.0).all():
            raise ValueError('fixed-abundant requires every water-year-type value to equal 4; inspect the model input')
        return series
    return read_series(dss, path, {'MAF', 'STOR-MAF'})

def validate_daily(data, start, end):
    data = data.reindex(pd.date_range(start, end, freq='D'))
    values = data.to_numpy(dtype=float)
    invalid = ~np.isfinite(values) | (np.abs(values) > 1e30)
    if invalid.any():
        columns = list(data.columns[invalid.any(axis=0)])
        raise ValueError('Missing/invalid daily inputs: ' + ', '.join(columns))
    return data

def calculate(data, calc, aliases, flags, floors, travel, selected, year, end, forecast_days, median, targets):
    data = data.copy()
    data['LOP_stor'] += data['HCR_stor']
    data['LOP_inflow'] += data['HCR_inflow'] - data['HCR_outflow']
    combined_floors = dict(floors)
    combined_floors['Lookout Point'] += combined_floors['Hills Creek']
    data = calc.compute_net_inflows(data, aliases)
    # The helper already subtracts storage floors. No second subtraction.
    usable = calc.calculate_storage_on_date(data, (4, 1), combined_floors)
    if year not in usable.index:
        raise ValueError('April 1 storage absent')
    period_end = (end.month, end.day)
    pivots = calc.create_net_inflow_pivot_tables(data, aliases, (4, 1), period_end)
    short = calc.create_short_forecast_volume_pivot_tables(pivots, forecast_days, 86400 / 43560.0)
    for name in selected:
        alias = aliases[name]
        if alias not in median or median[alias].empty:
            raise ValueError('Missing median remaining volume for ' + name)
        expected = short[alias].index
        values = median[alias].reindex(expected)
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError('Incomplete median volume schedule for ' + name)
    available = calc.create_total_available_volume_pivot_tables(short, forecast_days, usable, median)
    for gauge, prefix in [('Salem', 'SLM'), ('Albany', 'ALB')]:
        data = calc.create_gauge_minflow_ts(targets[gauge], data, prefix)
        proportions = calc.create_augmentation_proportion_tables(available,
            {name: flags[name][gauge] for name in aliases}, aliases)
        deficits = calc.create_gauge_deficit_pivot_table(data, prefix, (4, 1), period_end)
        # Preserve legacy signed deficit behavior; do not silently redesign it.
        flows = calc.create_agumentation_flow_pivot_tables(proportions, deficits)
        for alias, pivot in flows.items():
            series = calc.melt_pivot_to_series(pivot, alias + '_augmentation_' + prefix + '_flow',
                data.index[0], data.index[-1])
            data[series.name] = series
        for name in selected:
            alias = aliases[name]
            delay = pd.Timedelta(days=travel[name])
            release_start = pd.Timestamp(year=year, month=4, day=1) - delay
            release_end = end - delay
            column = alias + '_min_flow_with_aug_' + prefix
            data[column] = 0.0
            mask = (data.index >= release_start) & (data.index <= release_end)
            # Only require future allocations inside the declared target window.
            # Outside that window augmentation is zero, not an invented extension.
            incoming = data[alias + '_augmentation_' + prefix + '_flow'].reindex(data.index[mask] + delay)
            if not np.isfinite(incoming.to_numpy(dtype=float)).all():
                raise ValueError('Missing travel-shifted allocation for ' + name)
            values = data.loc[mask, alias + '_outflow'].to_numpy() + incoming.to_numpy()
            data.loc[mask, column] = np.clip(values, 0, calc.MAX_FLOW_DICT[name])
    for name in selected:
        alias = aliases[name]
        data[alias + '_min_flow_with_aug'] = data[[alias + '_min_flow_with_aug_SLM',
                                                  alias + '_min_flow_with_aug_ALB']].max(axis=1)
    return data
