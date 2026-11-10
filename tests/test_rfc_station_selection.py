import ast
from pathlib import Path
import tempfile
import types
import typing
import unittest

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / 'NWP_Willamette_Master_2026_11_10_Multithread'
LOCAL = 'WTLO3 VIDO3 SLMO3 MNRO3 MEHO3 LOPO3 JFFO3 JASO3 HARO3 GOSO3 FOSO3 CORO3 ALBO3'.split()
NATURAL = 'TRBO3 SUVO3 SPRO3 PHIO3 LSMO3 HCRO3 GPRO3 FRNO3 FALO3 DORO3 DETO3 COTO3 CGRO3 BLUO3'.split()
EXPECTED = {**{s:('FLOW-LOC','unadjusted') for s in LOCAL},
            **{s:('FLOW-UNREG','natural') for s in NATURAL}}


def load_selection(path):
    tree = ast.parse(path.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [n.id for n in node.targets if isinstance(n,ast.Name)]
            if any(n.startswith(('BASE_URL_', 'SITES_', 'GROUP_TO_')) or n == 'SPECS' for n in names):
                keep.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in ('load_espf10','_build_path'):
            keep.append(node)
    namespace = dict(Dict=typing.Dict,List=typing.List,Tuple=typing.Tuple,pd=types.SimpleNamespace(DataFrame=object))
    exec(compile(ast.Module(body=keep,type_ignores=[]),str(path),'exec'),namespace)
    return namespace


class RfcSelectionTests(unittest.TestCase):
    def test_all_four_copies_match_requested_station_products(self):
        for folder in ('scripts/ExternalPython','scripts/rts-setup-package/ExternalPython'):
            downloader = load_selection(WS / folder / 'RFC_Downloader_Module.py')
            osi = load_selection(WS / folder / 'OSI_Ensemble_Year.py')
            actual = {}
            for spec in downloader['SPECS']:
                product = 'natural' if '/natural/' in spec['base_url'] else 'unadjusted'
                for site in spec['sites']:
                    station = site + '3'
                    self.assertNotIn(station,actual)
                    actual[station] = (downloader['GROUP_TO_BPART'][spec['name']], product)
                    suffix = 'N_SQIN' if product == 'natural' else 'XE_SQIN'
                    self.assertEqual(spec['base_url'] + spec['pattern'].format(site=site),
                        'https://www.nwrfc.noaa.gov/chpsesp/ensemble/%s/%s%s.ESPF10.csv' % (product,station,suffix))
                    self.assertEqual(downloader['_build_path'](site,actual[station][0],'1Day','C:001982|'),
                                     '//%s/%s//1Day/C:001982|/' % (station,actual[station][0]))
            self.assertEqual(actual,EXPECTED)
            self.assertEqual(osi['GROUP_TO_SITES'],{s['name']:s['sites'] for s in downloader['SPECS']})
            self.assertEqual(osi['GROUP_TO_BPART'],downloader['GROUP_TO_BPART'])

    def test_loader_requests_exactly_the_27_urls_once(self):
        module = load_selection(WS / 'scripts/ExternalPython/RFC_Downloader_Module.py')
        urls = []
        class Session:
            headers = {}
            def get(self,url,timeout):
                urls.append(url)
                return types.SimpleNamespace(status_code=200,text='fixture')
        with tempfile.TemporaryDirectory() as directory:
            flag = Path(directory) / 'done'
            flag.touch()
            module.update(requests=types.SimpleNamespace(Session=Session,RequestException=RuntimeError),
                          RAW_DONE_FLAG=flag,
                          _parse_nwrfc_espf_csv_to_cfs=lambda text:types.SimpleNamespace(shape=(2,43)))
            data, misses = module['load_espf10'](debug=False)
        self.assertEqual(misses,[])
        self.assertEqual(len(urls),27)
        self.assertEqual(len(set(urls)),27)
        self.assertEqual(sum(len(sites) for sites in data.values()),27)


if __name__ == '__main__':
    unittest.main()
