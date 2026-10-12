import copy
import unittest
from datetime import datetime, timezone
from turf_lab.manual_value import compare


def inputs():
    prediction={'race_id':'2026-10-12_R1C1','scheduled_start':'2026-10-12T14:00:00+02:00',
      'predicted_at':'2026-10-12T13:00:00+02:00','feature_cutoff':'2026-10-12T12:00:00+02:00',
      'validation_status':'experimental','uncertainty':'high','data_quality_pass':True,
      'runners':[{'number':1,'horse_id':'HORSE-A-MOTHER-FATHER','name':'A','probability':0.6,'status':'PARTANT'},
                 {'number':2,'horse_id':'HORSE-B-MOTHER-FATHER','name':'B','probability':0.4,'status':'PARTANT'}]}
    quotes={'race_id':prediction['race_id'],'observed_at':'2026-10-12T13:45:00+02:00',
      'runners_verified_at':'2026-10-12T13:46:00+02:00','source':'PMU_MANUAL_SCREENSHOT',
      'transcription_verified':True,'image_sha256':'a'*64,'odds_format':'DECIMAL_TOTAL_RETURN',
      'quotes':[{'number':r['number'],'horse_id':r['horse_id'],'name':r['name'],'decimal_odds':2.0} for r in prediction['runners']]}
    now=datetime(2026,10,12,11,47,tzinfo=timezone.utc)
    return prediction,quotes,now


class ManualValueTests(unittest.TestCase):
    def test_formula_and_experimental_model_no_bet(self):
        p,q,n=inputs();original=copy.deepcopy(p)
        r=compare(p,q,n)
        self.assertAlmostEqual(r['rows'][0]['ev'],0.2)
        self.assertEqual(r['status'],'NO BET')
        self.assertEqual(p,original)

    def test_ambiguous_odds_rejected(self):
        p,q,n=inputs();q['odds_format']='UNKNOWN'
        self.assertIn('ambiguous_odds_convention',compare(p,q,n)['reasons'])

    def test_quote_cannot_change_probability(self):
        p,q,n=inputs();a=compare(p,q,n);q['quotes'][0]['decimal_odds']=100
        b=compare(p,q,n)
        self.assertEqual([r['probability'] for r in a['rows']],[r['probability'] for r in b['rows']])

    def test_wrong_horse_number_rejected(self):
        p,q,n=inputs();q['quotes'][0]['number']=8
        self.assertIn('runner_number_or_name_mismatch',compare(p,q,n)['reasons'])

    def test_future_quotes_or_started_race_rejected(self):
        p,q,n=inputs();q['observed_at']='2026-10-12T13:58:00+02:00'
        self.assertIn('invalid_chronology_or_race_started',compare(p,q,n)['reasons'])
        p,q,n=inputs();n=datetime(2026,10,12,12,1,tzinfo=timezone.utc)
        self.assertIn('invalid_chronology_or_race_started',compare(p,q,n)['reasons'])

    def test_non_runner_requires_updated_probabilities(self):
        p,q,n=inputs();p['runners'][1]['status']='NON_PARTANT';q['quotes']=q['quotes'][:1]
        self.assertIn('probabilities_not_normalized_for_active_field',compare(p,q,n)['reasons'])

    def test_missing_and_duplicate_quotes_fail_closed(self):
        p,q,n=inputs();q['quotes']=[q['quotes'][0],q['quotes'][0]]
        self.assertIn('quote_field_does_not_match_active_runners',compare(p,q,n)['reasons'])


if __name__=='__main__':unittest.main()
