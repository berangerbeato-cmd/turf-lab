import unittest
from turf_lab.ensemble import blend


class EnsembleTests(unittest.TestCase):
    def test_convex_weights_and_nonrunner(self):
        a={1:.8,2:.2,3:0.};b={1:.3,2:.7,3:0.}
        self.assertEqual(blend(a,b,0),a)
        self.assertEqual(blend(a,b,1),b)
        c=blend(a,b,.2)
        self.assertAlmostEqual(c[1],.7)
        self.assertAlmostEqual(sum(c.values()),1)
        self.assertEqual(c[3],0)
        self.assertEqual(a[1],.8)

    def test_invalid_distributions_and_fields(self):
        a={1:.8,2:.2}
        for b,w in [({1:1.},.2),({1:float('nan'),2:0},.2),({1:.8,2:.8},.2),(a,-.1),(a,float('nan'))]:
            with self.assertRaises(ValueError):
                blend(a,b,w)
