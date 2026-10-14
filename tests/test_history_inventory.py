import json
import tempfile
import unittest
from pathlib import Path
from scripts.history_inventory import inventory


class HistoryInventoryTests(unittest.TestCase):
    def test_missing_months_not_assumed_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = inventory(Path(folder), 2024, 2024, "2024-02")
            self.assertEqual([r["status"] for r in rows], ["MISSING", "MISSING"])

    def test_partial_month_is_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "month_2024-01" / "manifest.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"month": "2024-01", "status": "COLLECTED",
                "days": [{"date": "2024-01-01", "status": "OK", "candidate_races": 1}],
                "partitions": [{"race_id": "one"}], "quarantine": [], "participants": 12}))
            self.assertEqual(inventory(root, 2024, 2024, "2024-01")[0]["status"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()

class CalendarIntegrityTests(unittest.TestCase):
    def manifest(self, root, dates):
        path = root / 'month_2024-01' / 'manifest.json'
        path.parent.mkdir()
        path.write_text(json.dumps({'month':'2024-01', 'status':'COLLECTED',
            'days':[{'date':d,'status':'OK','candidate_races':0} for d in dates],
            'partitions':[], 'quarantine':[], 'participants':0, 'candidate_races':0}))

    def test_dates_from_wrong_month_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.manifest(root, [f'2024-02-{i:02d}' for i in range(1,29)])
            with self.assertRaisesRegex(ValueError,'outside month'):
                inventory(root,2024,2024,'2024-01')

    def test_duplicate_dates_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.manifest(root,['2024-01-01']*31)
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                inventory(root,2024,2024,'2024-01')

    def test_full_calendar_without_source_proof_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.manifest(root,[f'2024-01-{i:02d}' for i in range(1,32)])
            row=inventory(root,2024,2024,'2024-01')[0]
            self.assertEqual(row['status'],'PARTIAL')
            self.assertFalse(row['source_verified'])
            self.assertTrue(row['issues'])
