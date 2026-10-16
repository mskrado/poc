import os, tempfile, unittest
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import delivery_metrics as dm

def write(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False); f.write(text); f.close(); return f.name

class T(unittest.TestCase):
    def test_known_values(self):
        p = write("deploy_id,commit_time,deploy_time,failed\n"
                  "a,2026-01-01T00:00:00Z,2026-01-01T02:00:00Z,false\n"
                  "b,2026-01-01T00:00:00Z,2026-01-01T04:00:00Z,true\n"
                  "c,2026-01-01T00:00:00Z,2026-01-01T10:00:00Z,no\n"
                  "d,2026-01-01T00:00:00Z,2026-01-02T00:00:00Z,0\n")
        m = dm.metrics(dm.load(p)); os.unlink(p)
        self.assertEqual(m["deploys"], 4); self.assertAlmostEqual(m["change_fail_rate"], 0.25)
        self.assertAlmostEqual(m["lead_time_median_h"], 7.0)
    def test_deploy_before_commit_rejected(self):
        p = write("deploy_id,commit_time,deploy_time,failed\na,2026-01-02T00:00:00Z,2026-01-01T00:00:00Z,false\n")
        self.assertEqual(dm.main([p]), 2); os.unlink(p)
    def test_naive_time_rejected(self):
        p = write("deploy_id,commit_time,deploy_time,failed\na,2026-01-01T00:00:00,2026-01-01T01:00:00,false\n")
        self.assertEqual(dm.main([p]), 2); os.unlink(p)
    def test_example_exit_codes(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        f = os.path.join(root, "examples", "example_deploys.csv")
        self.assertEqual(dm.main([f]), 1)
        self.assertEqual(dm.main([f, "--max-cfr", "0.2"]), 0)

if __name__ == "__main__":
    unittest.main()
