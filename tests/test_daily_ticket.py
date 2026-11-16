import unittest
from turf_lab.daily_ticket import make_ticket

class DailyTicket(unittest.TestCase):
    def setUp(self):
        self.model='available_history_v3'
        self.protocol={
            'version':'daily_ticket_strategy_v1',
            'model':self.model,
            'simple_gagnant':{'minimum_ev':.10,'max_rank':4},
            'ze5':{'number_of_horses':5,'type':'ZE5_DESORDRE','stake_eur_total':1.0},
        }
        self.p={
            'race_id':'2026-11-16_R1C7',
            'primary_model':self.model,
            'scheduled_start':'2026-11-16T17:25:00+01:00',
            'target_snapshot':{'participants':[{'numPmu':n,'statut':'PARTANT'} for n in range(1,7)]},
            'models':{self.model:{'model_sha256':'frozen'}},
        }
        self.q={
            'race_id':self.p['race_id'],
            'observed_at':'2026-11-16T16:37:00+01:00',
            'quotes':[{'number':n} for n in range(1,7)],
        }
        values=[
            (1,.32,3.5,.12), (2,.21,5,.05), (3,.17,7,.19),
            (4,.14,8,.12), (5,.10,19,.90), (6,.06,20,.20)
        ]
        self.c={
            'race_id':self.p['race_id'],
            'rows':[{'number':n,'name':f'HORSE {n}','odds':odds,
                     'models':{self.model:{'probability':prob,'ev':ev}}}
                    for n,prob,odds,ev in values],
        }

    def test_sg_top3_top4_and_ze5_one_euro(self):
        ticket=make_ticket(self.p,self.q,self.c,self.protocol)
        self.assertEqual([s['number'] for s in ticket['sg']['top3_selection']],[1,3])
        self.assertEqual([s['number'] for s in ticket['sg']['top4_selection']],[1,3,4])
        self.assertEqual(ticket['ze5']['numbers'],[1,2,3,4,5])
        self.assertEqual(ticket['ze5']['stake_eur_total'],1)
        self.assertEqual(ticket['ze5']['status'],'OFFER_UNVERIFIED')
        self.assertFalse(ticket['eligible_for_j15_prospective_sg_comparison'])

    def test_ze5_not_offered(self):
        self.q['ze5_offered']=False
        ticket=make_ticket(self.p,self.q,self.c,self.protocol)
        self.assertEqual(ticket['ze5']['status'],'NOT_OFFERED')
        self.assertEqual(ticket['ze5']['stake_eur_total'],0)

    def test_j15_eligibility_without_changing_capture_time(self):
        self.q['observed_at']='2026-11-16T17:12:00+01:00'
        ticket=make_ticket(self.p,self.q,self.c,self.protocol)
        self.assertTrue(ticket['eligible_for_j15_prospective_sg_comparison'])

    def test_missing_quote_rejected(self):
        self.q['quotes'].pop()
        with self.assertRaises(ValueError):
            make_ticket(self.p,self.q,self.c,self.protocol)

    def test_model_mismatch_rejected(self):
        self.p['primary_model']='v6'
        with self.assertRaises(ValueError):
            make_ticket(self.p,self.q,self.c,self.protocol)

if __name__=='__main__':
    unittest.main()
