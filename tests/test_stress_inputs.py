import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'tools/build_stress_inputs.py'
spec = importlib.util.spec_from_file_location('stress_inputs', path)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class StressInputsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [ ['Inflow','Known Flow','old.dss','','DETO3','FLOW-UNREG','1DAY','C:003002|'],
                      ['WY','Input Time Series','wy.dss','ALL_ABUNDANT','','STOR','1DAY','WY_TYPE'] ]
        self.paths = ['//DETO3/FLOW-UNREG/01Jan2026/1Day/C:%06d|/' % m
                      for m in range(1982,2025)]
        self.paths += ['/ALL_ABUNDANT//STOR/01Jan2026/1Day/WY_TYPE/',
                       '//Lookout Point-Pool/Flow-OUT/01Jan2026/1Day/C:001982|Con_Season0/',
                       '//DETO3/FLOW-UNREG/01Jan2026/1Day/C:003000|/']

    def test_exactly_1000_members_and_no_output_or_synthetic_records(self):
        copies, mapping, expected = builder.build_plan(self.paths,self.rows)
        self.assertEqual(len(copies),1001)
        self.assertEqual(len(expected),1001)
        self.assertEqual([m['target_member'] for m in mapping],list(range(1982,2982)))
        self.assertEqual(mapping[43],dict(target_member=2025,source_member=1982))
        self.assertFalse(any('Con_Season' in dst or '003000|' in dst for _,dst in copies))

    def test_in_place_skips_original_members_and_common_records(self):
        copies, _, _ = builder.build_plan(self.paths,self.rows)
        additions = builder.in_place_copies(copies,self.paths)
        self.assertEqual(len(additions),957)
        self.assertTrue(all(2025 <= int(dst.split('/')[6][2:8]) <= 2981
                            for _,dst in additions))

    def test_in_place_rejects_existing_target_before_writes(self):
        copies, _, _ = builder.build_plan(self.paths,self.rows)
        existing = self.paths + ['//DETO3/FLOW-UNREG/01Jan2026/1Day/C:002025|/']
        with self.assertRaisesRegex(ValueError,'Target input already exists'):
            builder.in_place_copies(copies,existing)

    def test_custom_range_avoids_existing_future_members(self):
        existing = self.paths + ['//DETO3/FLOW-UNREG/01Jan2026/1Day/C:002025|/']
        copies, mapping, _ = builder.build_plan(existing,self.rows,first_member=4000)
        additions = builder.in_place_copies(copies,existing)
        self.assertEqual(len(additions),1000)
        self.assertEqual(mapping[0],dict(target_member=4000,source_member=1982))
        self.assertEqual(mapping[-1]['target_member'],4999)

    def test_collision_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate source'):
            builder.build_plan(self.paths+[self.paths[0]],self.rows)

    def test_missing_source_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'differs for source member 1983'):
            # Remove the record from 1983, not the reference member.
            builder.build_plan([p for p in self.paths if '001983|' not in p],self.rows)

    def test_missing_common_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'common inputs absent'):
            builder.build_plan([p for p in self.paths if 'ALL_ABUNDANT' not in p],self.rows)


if __name__ == '__main__':
    unittest.main()
