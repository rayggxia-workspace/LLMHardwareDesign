"""Source-path normalization must never mask changed hardware connectivity."""
import copy,unittest
from topology_receipt import structural


class ReplayComparison(unittest.TestCase):
    def test_only_provenance_may_differ(self):
        old={'cells':{'c':{'type':'BUF','connections':{'A':[1],'Y':[2]},'parameters':{'src':7},'attributes':{'src':'old/leaves.v:1','keep':1}}},'ports':{'src':{'bits':[1]}}}
        new=copy.deepcopy(old);new['cells']['c']['attributes']['src']='replay/leaves.v:1'
        self.assertEqual(structural(old),structural(new))
        for field,value in [('connections',{'A':[2],'Y':[1]}),('type','INV'),('parameters',{'src':8}),('attributes',{'src':'old/leaves.v:1','keep':0})]:
            bad=copy.deepcopy(new);bad['cells']['c'][field]=value
            self.assertNotEqual(structural(old),structural(bad),field)
        bad=copy.deepcopy(new);bad['ports']['src']['bits']=[2]
        self.assertNotEqual(structural(old),structural(bad))


if __name__=='__main__':unittest.main()
