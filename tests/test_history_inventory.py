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
