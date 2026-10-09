import unittest
from validation.compare_signals import compare
class ComparisonTests(unittest.TestCase):
 def test_no_reference_never_validated(self):
  r=compare([],[])
  self.assertFalse(r["HVR"]["validated"])
  self.assertIsNone(r["PbD"]["agreement_rate"])
 def test_missing_observation_not_match(self):
  refs=[{"timestamp_utc":"2026-10-08T10:00:00Z","market":"EURUSD#","indicator":"HVR","expected":"HOLD"}]
  r=compare(refs,[])
  self.assertEqual(r["HVR"]["missing_observations"],1)
  self.assertFalse(r["HVR"]["validated"])
 def test_disagreement_reported(self):
  refs=[{"timestamp_utc":"2026-10-08T10:00:00Z","market":"EURUSD#","indicator":"PbD","expected":"P"}]
  obs=[{"timestamp_utc":"2026-10-08T10:00:00Z","market":"EURUSD#","indicator":"PbD","observed":"D"}]
  r=compare(refs,obs)
  self.assertEqual(len(r["PbD"]["disagreements"]),1)
if __name__=="__main__":unittest.main()
