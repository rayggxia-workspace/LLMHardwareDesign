import unittest
from cost_readout import account,packet
class PacketCalls(unittest.TestCase):
 def test_causal_decode_is_not_a_batched_packet(self):
  cost={'A_scale_bytes':2560,'W_scale_bytes':1280,'Y_scale_bytes':16,'bias_S32Q20_bytes':0,'W_i8_bytes':163840,'A_i8_bytes':327680,'INT32_partial_bytes':163840,'row_source_passes_for_16KiB':2}
  r=account({'cost':cost,'linear':'down','profile':'K128','case':'prefix128.decode','rows':32,'outputs':16,'groups':80,'K':10240})
  self.assertEqual(r['final_I8_wire_bytes'],32*128)
  self.assertEqual(r['shared_I32_compact_partial_wire_bytes'],32*packet(5120+80+32))
  self.assertGreater(r['final_I8_wire_bytes'],packet(32*16+16+32))
if __name__=='__main__':unittest.main()
