import unittest
from contracts import protocol,config,KEYS
class StrictEvidence(unittest.TestCase):
 def test_missing_protocol(self):
  for x in ({},{'actual_M_active_reset':True},{k:('false'if k=='SRAM_retained'else True)for k in KEYS},{k:1 for k in KEYS}):
   with self.assertRaises(ValueError):protocol(x)
 def test_complete_protocol(self):protocol({k:True for k in KEYS})
 def test_wrong_variant(self):
  for x in ({},{'profile':True},{'profile':3},{'profile':1,'stall':2}):
   with self.assertRaises(ValueError):config(x,1,0)
 def test_exact_variant(self):config({'profile':1,'stall':0},1,0)
if __name__=='__main__':unittest.main()
