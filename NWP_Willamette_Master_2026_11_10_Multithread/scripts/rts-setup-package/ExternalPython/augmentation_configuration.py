"""Portable configuration tables for the existing standalone calculator."""
import csv
import math
from pathlib import Path
import tempfile
from augmentation_calculation import read_config
from baseline_versions import atomic_json
CONFIG_NAME = 'MinFlowSalemAlbanyConfig.csv'

def read_configuration(path):
    """Read the installed CSV without editing it; retain every variable."""
    read_config(path)  # Use the same validation as the calculator.
    with open(path, encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.reader(handle))
    start = next(i for i, row in enumerate(rows) if row and row[0].strip() == 'Variable')
    header = [cell.strip() for cell in rows[start]]
    while header and not header[-1]:
        header.pop()
    body = [[cell.strip() for cell in (row[:len(header)] + [''] * len(header))[:len(header)]]
            for row in rows[start + 1:] if row and row[0].strip() and not row[0].lstrip().startswith('#')]
    return {'schema': 1, 'name': 'configuration', 'columns': header, 'rows': body,
            'calculation': {'forecast_days': 10, 'wy_type_mode': 'storage-maf'}}

def write_configuration_csv(config, destination):
    if config.get('schema') != 1 or not str(config.get('name', '')).strip():
        raise ValueError('A configuration name is required')
    columns, rows = config['columns'], config['rows']
    if not columns or columns[0] != 'Variable' or any(len(row) != len(columns) for row in rows):
        raise ValueError('Configuration table has missing or extra cells')
    numeric = {'MaxConElev', 'MinConElev', 'MinConStor', 'SummerBufferElev', 'MaxRelease', 'TravelTimeDays'}
    for row in rows:
        if row[0] in numeric and any(not math.isfinite(float(value)) for value in row[1:]):
            raise ValueError('Nonfinite numeric configuration value: ' + row[0])
    calculation = config['calculation']
    days=calculation['forecast_days']
    if (isinstance(days,bool) or int(days)!=float(days) or int(days)<1
            or calculation['wy_type_mode'] not in ('fixed-abundant','storage-maf')):
        raise ValueError('Invalid calculation settings')
    destination = Path(destination)
    with destination.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    read_config(destination)

def save_configuration(config, destination):
    """Portable JSON has no simulation dates, member IDs or baseline reference."""
    with tempfile.TemporaryDirectory(prefix='rts-config-') as directory:
        write_configuration_csv(config, Path(directory) / CONFIG_NAME)
    allowed = {key: config[key] for key in ('schema', 'name', 'columns', 'rows', 'calculation')}
    atomic_json(destination, allowed)
    print('Saved reusable configuration:', destination, flush=True)
