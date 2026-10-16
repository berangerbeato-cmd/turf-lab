import unittest
from copy import deepcopy
from scripts.compare_place_quote import compare


class PlaceQuoteTests(unittest.TestCase):
    def fixture(self):
        ticket = dict(race_id='synthetic', selection=[4], market='place3',
            selection_method='classic_max_probability', field_size=12, nonrunners=0,
            prediction_evidence='synthetic', calibration_evidence='synthetic', field_evidence='synthetic',
            probability=.5, created_at='2026-10-15T10:00:00Z')
        quote = dict(race_id='synthetic', selection=[4], market='place3', operator='synthetic',
            source_evidence='synthetic', start_evidence='synthetic', kind='probable', includes_stake=True,
            observed_at='2026-10-15T10:45:00Z', verified_start_at='2026-10-15T11:00:00Z',
            unit_stake=2, return_low=3.4, return_high=4.6)
        return ticket, quote

    def test_unit_normalization_and_range_crossing_break_even(self):
        t, q = self.fixture()
        result = compare(t, q)
        self.assertEqual(result['break_even_total_return_per_euro'], 2)
        self.assertAlmostEqual(result['conditional_net_return_scenarios'][0], -.15)
        self.assertAlmostEqual(result['conditional_net_return_scenarios'][1], .15)
        self.assertFalse(result['lower_quote_above_model_break_even'])

    def test_reject_noncomparable_or_unverifiable_quotes(self):
        for patch in [dict(selection=[5]), dict(market='win'), dict(includes_stake=False),
                      dict(kind='final'), dict(source_evidence=''), dict(unit_stake=0),
                      dict(return_low=float('nan')), dict(return_low=5),
                      dict(observed_at='2026-10-15T11:00:00Z'),
                      dict(observed_at='2026-10-15T10:45:00')]:
            t, q = self.fixture()
            q.update(patch)
            with self.assertRaises(ValueError): compare(t, q)

    def test_reject_changed_field_and_unsupported_selection(self):
        for patch in [dict(nonrunners=1), dict(selection_method='highest_ev'), dict(probability=1)]:
            t, q = self.fixture()
            t.update(patch)
            with self.assertRaises(ValueError): compare(t, q)
