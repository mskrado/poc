import json
import subprocess
import sys
import unittest
from pathlib import Path
from payback_calculator import calculate_payback


class AcceptanceTests(unittest.TestCase):
    def model(self, **overrides):
        inputs = dict(exit_cost_per_role=70000000/660, roles_cut=1,
                      loaded_annual_cost_per_role=180000, agent_annual_run_cost=24000,
                      residual_share=.2, residual_staffing_cost=180000,
                      implementation_cost=12000)
        inputs.update(overrides)
        return calculate_payback(**inputs)

    def test_worked_example(self):
        r = self.model()
        self.assertEqual(r['net_monthly_saving'], 10000)
        self.assertAlmostEqual(r['payback_months'], 11.806060606060607)
        self.assertAlmostEqual(r['net_position_24_months'], 121939.39393939394)

    def test_no_payback_zero(self):
        r = self.model(agent_annual_run_cost=144000)
        self.assertIsNone(r['payback_months'])
        self.assertEqual(r['status'], 'no payback')

    def test_no_payback_negative(self):
        r = self.model(agent_annual_run_cost=200000)
        self.assertLess(r['net_monthly_saving'], 0)
        self.assertIsNone(r['payback_months'])

    def test_zero_upfront(self):
        self.assertEqual(self.model(exit_cost_per_role=0, implementation_cost=0)['payback_months'], 0)

    def test_share_boundaries(self):
        self.assertEqual(self.model(residual_share=0)['residual_annual_cost'], 0)
        self.assertEqual(self.model(residual_share=1)['residual_annual_cost'], 180000)

    def test_multiple_roles_scope(self):
        r = self.model(roles_cut=2)
        self.assertEqual(r['baseline_annual_cost'], 360000)
        self.assertAlmostEqual(r['upfront_cost'], 2*70000000/660+12000)
        self.assertEqual(r['residual_annual_cost'], 36000)

    def test_unit_mode(self):
        r = self.model(residual_staffing_cost=None, human_unit_cost=18, annual_units=10000)
        self.assertEqual(r, self.model())

    def test_invalid(self):
        for overrides in ({'roles_cut':0}, {'roles_cut':1.5}, {'roles_cut':True},
                          {'residual_share':1.1}, {'residual_share':-.1},
                          {'agent_annual_run_cost':float('nan')},
                          {'exit_cost_per_role':float('inf')}, {'implementation_cost':-1},
                          {'residual_staffing_cost':None}, {'human_unit_cost':2},
                          {'human_unit_cost':2, 'annual_units':3},
                          {'residual_staffing_cost':-1},
                          {'residual_staffing_cost':None, 'human_unit_cost':-1, 'annual_units':1}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.model(**overrides)

    def test_overflow(self):
        with self.assertRaises(ValueError):
            self.model(loaded_annual_cost_per_role=1e308, roles_cut=100)

    def test_sensitivity(self):
        rows = self.model()['sensitivity']
        self.assertEqual([r['residual_share'] for r in rows], [.05,.1,.2,.3])
        self.assertEqual([r['net_monthly_saving'] for r in rows], [12250,11500,10000,8500])

    def test_cli(self):
        script = str(Path(__file__).with_name('payback_calculator.py'))
        args = [sys.executable, script, '--exit-cost-per-role','100000', '--roles-cut','1',
                '--loaded-annual-cost-per-role','180000','--agent-annual-run-cost','24000',
                '--residual-share','.2','--residual-staffing-cost','180000']
        r = subprocess.run(args, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout)['payback_months'], 10)
        bad = subprocess.run(args+['--residual-share','2'], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)


if __name__ == '__main__':
    unittest.main()
