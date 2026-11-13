"""Exercise the actual documented loader against synthetic station ZIPs."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def verify_sources(root):
    source = json.loads((root/'source-manifest.json').read_text())
    for relative, expected in source['files'].items():
        # Git archive honors core.autocrlf on Windows. Verify the same source
        # content in either LF or CRLF form; do not ignore any code changes.
        content = (root/relative).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Archive verification source differs from the manifest: '+relative)


def check_archive(root):
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    verify_sources(root)
    sys.path.insert(0, str(root/'archive_backend'))
    import RFC_Archive_Module as archive
    frame = pd.DataFrame({
        'FCST_VALID_TIME_GMT': pd.date_range('2026-01-01 18:00', periods=12, freq='6h'),
        '1981': np.arange(1, 13, dtype=float), '1982': np.arange(2, 14, dtype=float)})
    table = pa.Table.from_pandas(frame, preserve_index=False)
    attrs = {'UNITS': 'KCFS', 'YEARS': 'WYR', 'ISSUED': '2026-01-01_12:00_GMT'}
    table = table.replace_schema_metadata({**(table.schema.metadata or {}),
                                          b'PANDAS_ATTRS': json.dumps(attrs).encode()})
    buffer = pa.BufferOutputStream()
    pq.write_table(table, buffer, compression='snappy')
    raw = buffer.getvalue().to_pybytes()
    specs = list(archive.archive_specs())
    assert len(specs) == 27
    with tempfile.TemporaryDirectory(prefix='archive-check-') as folder:
        directory = Path(folder)
        for station, name, parameter, flow in specs:
            with ZipFile(directory/(name+'.zip'), 'w', compression=ZIP_DEFLATED) as bundle:
                bundle.writestr('nested/'+name+'_'+parameter+'.ESPFM_2026010112.parquet', raw)
        window = {'archive_cycle': '2026010112', 'start_utc': '2026-01-02T00:00:00Z',
                  'start': '2026-01-02 00:00', 'end': '2026-01-03 00:00',
                  'lookback': '2026-01-01', 'utc_offset_hours': 0}
        with contextlib.redirect_stdout(io.StringIO()):
            frames, receipts = archive.load_archive(directory, window, 1981,
                                                    selected_members=[1981, 1982, 3000])
        assert len(frames) == len(receipts) == 27
        for result in frames.values():
            assert result.loc[pd.Timestamp('2026-01-02'), 1981] == 4500.0
            assert result.loc[pd.Timestamp('2026-01-02'), 3000] == 4750.0
            assert result.loc[pd.Timestamp('2026-01-03'), 1981] == 8500.0
        assert all(r['sha256'] == hashlib.sha256(raw).hexdigest() for r in receipts)
        invalid = table.replace_schema_metadata({b'PANDAS_ATTRS': b'{"UNITS":"CFS","YEARS":"WYR"}'})
        try:
            archive.parse_table(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('Archive loader accepted incorrect units')
        (directory/(specs[0][1]+'.zip')).unlink()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                archive.load_archive(directory, window, 1981)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('Archive loader accepted a missing station ZIP')
    print('PASS: actual archive loader: 27 station ZIPs, Parquet metadata, daily CFS, percentiles and rejection checks')
