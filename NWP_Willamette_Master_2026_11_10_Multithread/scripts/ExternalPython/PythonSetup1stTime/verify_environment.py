"""Check installed versions, archive reader, and real DSS7 read/write behavior."""
from importlib.metadata import version
from pathlib import Path
import sys
import tempfile


def main():
    import numpy as np
    import pandas as pd
    import plotly
    import pyarrow as pa
    import pyarrow.parquet as pq
    import cwms
    import requests
    import certifi
    from pydsstools.heclib.dss import HecDss
    from pydsstools.core import TimeSeriesContainer
    assert sys.version_info[:2] == (3, 9), 'Use the supplied Python 3.9 environment'
    assert version('pydsstools') == '2.4.0', 'The workflow currently requires the pydsstools 2.4 API'
    assert np.__version__ == '1.22.4', 'Update NumPy using the supplied YAML'
    assert pd.__version__ == '2.3.2', 'Update pandas using the supplied YAML'
    assert pa.__version__ == '21.0.0', 'Use PyArrow from the working environment specification'
    assert plotly.__version__ == '5.24.1', 'Use Plotly from the working environment specification'
    with tempfile.TemporaryDirectory(prefix='workflow-environment-') as temp:
        directory = Path(temp)
        table = pd.DataFrame({'value': [1.25, 2.5, 3.75]})
        pq.write_table(pa.Table.from_pandas(table), directory / 'check.parquet')
        pd.testing.assert_frame_equal(pq.read_table(directory / 'check.parquet').to_pandas(), table)
        pathname = '//ENVIRONMENT/FLOW//1Day/C:001981|/'
        container = TimeSeriesContainer()
        container.pathname = pathname
        container.startDateTime = '01JAN2026 00:00'
        container.numberValues = 3
        container.interval = 1440
        container.units = 'CFS'
        container.type = 'PER-AVER'
        container.values = np.array([1.25, 2.5, 3.75])
        dss = directory / 'check.dss'
        with HecDss.Open(str(dss), version=7) as handle:
            handle.put_ts(container)
        with HecDss.Open(str(dss)) as handle:
            assert handle.getPathnameList('/*/*/*/*/*/*/'), 'DSS catalog is empty'
            result = handle.read_ts(pathname, trim_missing=True)
            np.testing.assert_allclose(result.values, container.values)
    print('Python:', sys.version.split()[0])
    for name in ('pydsstools', 'numpy', 'pandas', 'plotly', 'pyarrow', 'cwms-python'):
        print(name + ': ' + version(name))
    print('PASS: imports, Parquet round trip, DSS7 write/catalog/read round trip')


if __name__ == '__main__':
    main()
