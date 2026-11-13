"""Check desktop dependencies and an actual modern DSS7 round trip."""
import importlib
import importlib.metadata
import pathlib
import tempfile

import numpy as np
import pandas as pd
from pydsstools.core import TimeSeriesContainer
from pydsstools.heclib.dss import HecDss
from cwms.cwms_types import Data


def main():
    for package, module in [
        ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('pydsstools', 'pydsstools'), ('cwms-python', 'cwms'),
        ('plotly', 'plotly.graph_objects'), ('requests', 'requests'),
        ('urllib3', 'urllib3'), ('rasterio', 'rasterio'),
        ('pyproj', 'pyproj'), ('affine', 'affine'), ('pydantic', 'pydantic'),
    ]:
        importlib.import_module(module)
        print(package, importlib.metadata.version(package))

    values = np.array([123.25, 456.5, 789.75])
    name = '/TEST/RESERVOIR/FLOW//1DAY/MODERN-ENV-CHECK/'
    with tempfile.TemporaryDirectory() as folder:
        path = str(pathlib.Path(folder) / 'check.dss')
        data = TimeSeriesContainer(
            name, len(values), 1440, values=values,
            start_time='01JAN2026 0000', data_units='CFS', data_type='PER-AVER')
        handle = HecDss.Open(path, version=7)
        try:
            handle.put_ts(data)
        finally:
            handle.close()
        handle = HecDss.Open(path)
        try:
            assert handle.search_path('/*/*/*/*/*/*/', sort=True)
            result = handle.read_ts(name, trim_missing=True)
            np.testing.assert_allclose(result.values, values)
            pd.testing.assert_index_equal(
                pd.DatetimeIndex([t.datetime() for t in result.times]),
                pd.date_range('2026-01-01', periods=3))
            assert result.data_units == 'CFS'
        finally:
            handle.close()
    print('PASS: DSS7 write/reopen/catalog/read, values, timestamps and units')
    payload = {'values': [[1767225600000, 123.25, 0]],
               'value-columns': [{'name': 'date-time', 'ordinal': 1},
                                 {'name': 'value', 'ordinal': 2},
                                 {'name': 'quality-code', 'ordinal': 3}]}
    frame = Data(payload, selector='values').df
    assert frame['value'].iloc[0] == 123.25
    assert frame['date-time'].iloc[0] == pd.Timestamp('2026-01-01', tz='UTC')
    print('PASS: CWMS local-response parsing (no live API request)')


if __name__ == '__main__':
    main()
