"""Check desktop dependencies and an actual modern DSS7 round trip."""
import importlib
import importlib.metadata
import pathlib
import tempfile
import argparse
import json
import sys
import struct
import inspect


def main():
    import numpy as np
    import pandas as pd
    from pydsstools.core import TimeSeriesContainer
    from pydsstools.heclib.dss import HecDss
    from cwms.cwms_types import Data
    from dataretrieval import waterdata
    from check_archive import check_archive
    root = pathlib.Path(__file__).resolve().parent
    wheels = json.loads((root / 'wheels-win64-py311.json').read_text())
    for wheel in wheels:
        assert importlib.metadata.version(wheel['name']) == wheel['version'], wheel['name']
    for package, module in [
        ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('pydsstools', 'pydsstools'), ('cwms-python', 'cwms'),
        ('plotly', 'plotly.graph_objects'), ('requests', 'requests'),
        ('urllib3', 'urllib3'), ('rasterio', 'rasterio'),
        ('pyproj', 'pyproj'), ('affine', 'affine'), ('pydantic', 'pydantic'),
        ('pyarrow', 'pyarrow.parquet'), ('matplotlib', 'matplotlib.figure'),
        ('dataretrieval', 'dataretrieval.waterdata'),
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
    with tempfile.TemporaryDirectory() as folder:
        frame = pd.DataFrame({'forecast': [1.25, 2.5, np.nan]},
                             index=pd.date_range('2026-01-01', periods=3))
        path = pathlib.Path(folder) / 'forecast.parquet'
        frame.to_parquet(path, engine='pyarrow', compression='snappy')
        pd.testing.assert_frame_equal(pd.read_parquet(path, engine='pyarrow'), frame,
                                      check_freq=False)
        from matplotlib.figure import Figure
        figure = Figure()
        figure.subplots().plot(frame.index, frame['forecast'])
        figure.savefig(pathlib.Path(folder) / 'forecast.png')
    print('PASS: PyArrow Parquet round trip and Matplotlib PNG rendering')
    check_archive(root)
    query = dict(monitoring_location_id='USGS-TEST', parameter_code='00060',
                 time='2026-01-01T00:00:00Z/2026-01-02T00:00:00Z')
    inspect.signature(waterdata.get_continuous).bind(**query)
    inspect.signature(waterdata.get_daily).bind(**query, skip_geometry=True)
    print('PASS: USGS waterdata API argument compatibility (no live request)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--report', type=pathlib.Path)
    args = parser.parse_args()
    assert sys.version_info[:2] == (3, 11) and struct.calcsize('P') == 8
    if args.preflight:
        assert sys.platform == 'win32', 'Windows x64 Python is required'
        print('PASS: Windows x64 Python 3.11')
    else:
        main()
        if args.report:
            args.report.write_text(json.dumps(dict(status='passed', python=sys.version,
                packages={w['name']: importlib.metadata.version(w['name']) for w in
                    json.loads((pathlib.Path(__file__).parent/'wheels-win64-py311.json').read_text())},
                limitations=['No live CWMS/USGS requests or real HEC model compute']), indent=2)+'\n')
