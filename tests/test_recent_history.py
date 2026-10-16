import unittest
from datetime import date
from unittest.mock import patch
from scripts.refresh_recent_history import required_days, require_fresh
class RecentHistoryTests(unittest.TestCase):
    def test_yesterday_only(self):
        self.assertEqual(required_days(date(2026,10,16)), ['2026-10-14','2026-10-15'])
    def test_missing_and_incomplete_fail_closed(self):
        for value in (None,dict(status='INCOMPLETE',records=[])):
            with patch('scripts.refresh_recent_history.read_day',return_value=value):
                with self.assertRaises(ValueError): require_fresh(date(2026,10,16))
    def test_complete_history_accepted(self):
        with patch('scripts.refresh_recent_history.read_day',return_value=dict(status='COMPLETE',records=[])):
            self.assertEqual(require_fresh(date(2026,10,16)),[])
