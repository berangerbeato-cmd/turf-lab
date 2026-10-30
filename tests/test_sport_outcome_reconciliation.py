import copy
import unittest
from scripts.reconcile_sport_outcomes import resolve


class OutcomeReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.raw = {'raceDate': '2026-09-01', 'racecourseCode': 'VIN', 'raceNumber': 2,
                    'raceRunParticipant': {'horseName': 'HORSE', 'place': {'arrivalStatus': 'PLACE'}}}
        self.record = {'date': '2026-09-01', 'race_id': '2026-09-01_R1C2', 'course_number': 2,
                       'course': {'arriveeDefinitive': True, 'discipline': 'ATTELE',
                                  'hippodrome': {'codeHippodrome': 'VIN'}, 'ordreArrivee': [[4], [2]]},
                       'participants': [{'idCheval': 'HORSE-PARENTS', 'nom': 'HORSE', 'numPmu': 2,
                                         'statut': 'PARTANT', 'ordreArrivee': 2}]}

    def result(self, records=None):
        return resolve(self.raw, 'HORSE-PARENTS', [(r, 'archive', 'digest') for r in (records or [self.record])])

    def test_exact_identity_and_agreeing_rank(self):
        self.assertEqual(self.result()['outcome']['rank'], 2)
        self.record['participants'][0]['idCheval'] = 'SAME-NAME-DIFFERENT-HORSE'
        self.assertEqual(self.result()['status'], 'UNRESOLVED_NO_EXACT_ARCHIVE')

    def test_incomplete_rank_is_not_fabricated(self):
        self.record['participants'][0]['ordreArrivee'] = None
        self.assertEqual(self.result()['status'], 'UNRESOLVED_OFFICIAL_OUTCOME')

    def test_stopped_and_fallen_are_not_disqualifications(self):
        for incident in ('ARRETE', 'TOMBE'):
            self.raw['raceRunParticipant']['place']['arrivalStatus'] = incident
            self.record['course']['ordreArrivee'] = [[4]]
            self.record['participants'][0].update(ordreArrivee=None, incident=incident)
            outcome = self.result()['outcome']
            self.assertFalse(outcome['dq'])
            self.assertFalse(outcome['finished'])
            self.assertIsNone(outcome['rank'])

    def test_conflicting_archive_versions(self):
        other = copy.deepcopy(self.record)
        other['course']['ordreArrivee'] = [[2], [4]]
        other['participants'][0]['ordreArrivee'] = 1
        self.assertEqual(self.result([self.record, other])['status'], 'CONFLICT')

    def test_wrong_day_track_course_or_provisional_ignored(self):
        for field, value in [('date', '2026-09-02'), ('course_number', 3)]:
            other = copy.deepcopy(self.record); other[field] = value
            self.assertEqual(self.result([other])['status'], 'UNRESOLVED_NO_EXACT_ARCHIVE')
        self.record['course']['arriveeDefinitive'] = False
        self.assertEqual(self.result()['status'], 'UNRESOLVED_NO_EXACT_ARCHIVE')

    def test_ties_use_competition_ranks(self):
        self.record['course']['ordreArrivee'] = [[4, 5], [2]]
        self.record['participants'][0]['ordreArrivee'] = 3
        self.assertEqual(self.result()['outcome']['rank'], 3)
