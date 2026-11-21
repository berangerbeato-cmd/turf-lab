"""Guardrails for the isolated individual-history repair replay."""
import unittest
from datetime import datetime, timezone
from turf_lab.history_repair_shadow import checked_prestart_stamp, merged_recent


class HistoryRepairShadowTests(unittest.TestCase):
    @staticmethod
    def official(day, race, rank, dq=False):
        return {'date': day, 'venue': 'REIMS', 'race_number': race,
                'rank': rank, 'disqualified': dq,
                'arrival_status': 'DISQUALIFIE_POUR_ALLURE_IRREGULIERE' if dq else 'PLACE'}

    @staticmethod
    def archived(day, race, rank, dq=False):
        return {'date': day, 'venue': 'REIMS',
                'race_id': day + '_R4C' + str(race),
                'rank': rank, 'dq': dq,
                'status': 'DISQUALIFIE_POUR_ALLURE_IRREGULIERE' if dq else ''}

    def test_stamps_must_precede_start_and_be_aware(self):
        start = datetime(2026, 11, 21, 17, 37, tzinfo=timezone.utc)
        checked_prestart_stamp('2026-11-21T17:30:00+00:00', start)
        with self.assertRaises(ValueError):
            checked_prestart_stamp('2026-11-21T17:37:00+00:00', start)
        with self.assertRaises(ValueError):
            checked_prestart_stamp('2026-11-21T17:40:00+00:00', start)
        with self.assertRaises(ValueError):
            checked_prestart_stamp('2026-11-21T17:30:00', start)

    def test_combine_individual_and_archived_recent_by_race_identity(self):
        official = [self.official('2026-11-20', 1, 2),
                    self.official('2026-11-17', 2, 1),
                    self.official('2026-11-15', 3, None, True),
                    self.official('2026-11-12', 4, 4)]
        archived = [self.archived('2026-11-17', 2, 1),
                    self.archived('2026-11-09', 5, 3)]
        rows, reason = merged_recent(official, archived, [], '2026-11-21')
        self.assertIsNone(reason)
        self.assertEqual(len(rows), 5)
        self.assertEqual([row['date'] for row in rows],
                         ['2026-11-20', '2026-11-17', '2026-11-15', '2026-11-12', '2026-11-09'])
        self.assertTrue(rows[2]['dq'])

    def test_disagreeing_archive_and_individual_abstains(self):
        official = [self.official('2026-11-20', 1, 1)]
        archived = [self.archived('2026-11-20', 1, 8)]
        with self.assertRaises(ValueError):
            merged_recent(official, archived, [], '2026-11-21')

    def test_unresolved_recent_result_abstains(self):
        official = [self.official(f'2026-11-{day:02d}', day, 4) for day in (20, 18, 16, 14, 12)]
        rows, reason = merged_recent(official, [], [{'date': '2026-11-19',
                                                      'reason': 'unknown_outcome'}], '2026-11-21')
        self.assertIsNone(rows)
        self.assertEqual(reason, 'UNRESOLVED_RECENT_OUTCOME')

    def test_old_unknown_result_does_not_poison_recent_five(self):
        official = [self.official(f'2026-11-{day:02d}', day, 4) for day in (20, 18, 16, 14, 12)]
        rows, reason = merged_recent(official, [], [{'date': '2026-10-19',
                                                      'reason': 'unknown_outcome'}], '2026-11-21')
        self.assertIsNone(reason)
        self.assertEqual(len(rows), 5)

    def test_fewer_than_five_known_starts_abstains(self):
        official = [self.official('2026-11-19', 1, 2)]
        rows, reason = merged_recent(official, [], [], '2026-11-21')
        self.assertIsNone(rows)
        self.assertEqual(reason, 'FEWER_THAN_FIVE_VERIFIED_STARTS')

    def test_nancy_brabois_and_nancy_are_same_venue(self):
        from turf_lab.individual_history_check import venue_key
        self.assertEqual(venue_key('NANCY-BRABOIS'), venue_key('NANCY'))
        official = [self.official('2026-11-15', 8, 5)]
        official[0]['venue'] = 'NANCY'
        archived = [self.archived('2026-11-15', 8, 5)]
        archived[0]['venue'] = 'NANCY-BRABOIS'
        dates = [20, 18, 16, 14]
        official.extend(self.official(f'2026-11-{d:02d}', d, 4) for d in dates)
        rows, reason = merged_recent(official, archived, [], '2026-11-21')
        self.assertIsNone(reason)
        self.assertEqual(len(rows), 5)

    def test_future_start_rejected(self):
        official = [self.official('2026-11-21', 1, 1)]
        with self.assertRaises(ValueError):
            merged_recent(official, [], [], '2026-11-21')

    def test_same_day_multiple_starts_abstains(self):
        official = [self.official('2026-11-20', 1, 1),
                    self.official('2026-11-20', 2, 2),
                    self.official('2026-11-18', 3, 3),
                    self.official('2026-11-16', 4, 1),
                    self.official('2026-11-14', 5, 2)]
        rows, reason = merged_recent(official, [], [], '2026-11-21')
        self.assertIsNone(rows)
        self.assertEqual(reason, 'MULTIPLE_STARTS_SAME_DAY')


if __name__ == '__main__':
    unittest.main()
