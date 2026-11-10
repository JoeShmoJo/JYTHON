"""Explicit leap-day rule-curve policy; never fills unrelated missing dates."""
from datetime import datetime
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
sys.path.insert(0,str(SCRIPTS/'rts-setup-package/ExternalPython'))
import write_rule_curves as curves


class RuleCurveTests(unittest.TestCase):
    def setUp(self):
        self.schedule=curves.annual_table(SCRIPTS/'RTSPython/CON_SEASON_RULE_CURVES.csv')
        self.begin=datetime(2020,2,28);self.end=datetime(2020,3,1)

    def test_linear_uses_actual_adjacent_values_and_preserves_every_other_day(self):
        dates,values=curves.expand(self.schedule,self.begin,self.end,leap_day='linear')
        index=dates.index(datetime(2020,2,29))
        for name in curves.RESERVOIRS:
            self.assertEqual(values[name][index],(self.schedule[(2,28)][name]+self.schedule[(3,1)][name])/2)
            for day,value in zip(dates,values[name]):
                if (day.month,day.day)!=(2,29):self.assertEqual(value,self.schedule[(day.month,day.day)][name])
        self.assertAlmostEqual(values['DETROIT'][index],1512.55)

    def test_explicit_february_29_overrides_policy_and_other_gaps_still_fail(self):
        self.schedule[(2,29)]={name:1234.5 for name in curves.RESERVOIRS}
        dates,values=curves.expand(self.schedule,self.begin,self.end,leap_day='linear')
        self.assertEqual(values['DETROIT'][dates.index(datetime(2020,2,29))],1234.5)
        del self.schedule[(3,1)]
        with self.assertRaisesRegex(ValueError,'2020-03-01'):
            curves.expand(self.schedule,self.begin,self.end,leap_day='linear')

    def test_error_hold_and_nonleap_policies(self):
        with self.assertRaisesRegex(ValueError,'February 29 policy'):
            curves.expand(self.schedule,self.begin,self.end)
        dates,values=curves.expand(self.schedule,self.begin,self.end,leap_day='feb28')
        self.assertEqual(values['DETROIT'][dates.index(datetime(2020,2,29))],self.schedule[(2,28)]['DETROIT'])
        a=curves.expand(self.schedule,datetime(2021,2,28),datetime(2021,3,1),leap_day='linear')
        b=curves.expand(self.schedule,datetime(2021,2,28),datetime(2021,3,1),leap_day='error')
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
