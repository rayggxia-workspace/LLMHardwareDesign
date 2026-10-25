import unittest
import assemble as A
import verify as V
class Contract(unittest.TestCase):
 def test_input_values_do_not_change_code(self):
  for op,a,b in [('mul_s32_s32',-12345,23456),('udiv_u128',111,0),('div_rne_s128_u64_i32',-5,2),('max_s64',-2,9)]:
   self.assertEqual(A.template(op,a=a,b=b)['words'],A.template(op)['words'])
 def test_shift_is_control_parameter(self):self.assertNotEqual(A.template('rne_s64_i32',0)['words'],A.template('rne_s64_i32',64)['words'])
 def test_no_hardware_wide_opcode(self):
  w=A.template('mul_s64_s32')['words'];self.assertTrue(all(x&15<=11 for x in w[:-1]));self.assertEqual(w[-1],14)
 def test_finite_scratch(self):self.assertLessEqual(A.template('div_rne_s128_u64_i32')['scratch'],256)
 def test_s64_tie(self):self.assertEqual(V.rne(-(1<<63),1<<64),0)
 def test_signed_tie_even(self):self.assertEqual([V.rne(x,2)for x in(-5,-3,3,5)],[-2,-2,2,2])
 def test_32bit_add_guard(self):self.assertFalse(V.scalar({'op':'add_s64','a':str((1<<63)-1),'b':'1','shift':0})['valid'])
 def test_zero_divisor(self):self.assertEqual(V.scalar({'op':'udiv_u128','a':'123','b':'0','shift':0}),{'valid':0})
 def test_shift129_not_silent(self):
  with self.assertRaises(ValueError):A.template('rne_s64_i32',129)
 def test_reserved_frame_half(self):
  for op in('mul_s32_s32','rne_s128_i32','isqrt_u128'):
   self.assertTrue(all(max(t['refs'])<256 for t in A.template(op)['outputs'].values()))
class Reception(unittest.TestCase):
 def fixture(self):
  v={'name':'synthetic','kind':'primitive','op':'signextend_s16_i64','a':-1,'b':0,'shift':0,'expected_status':0,'outputs':{'value':{'refs':list(range(8)),'signed':True},'valid':{'refs':[8],'signed':False}}}
  frame=bytes([255]*8+[1]+[0]*503)
  r={'name':'synthetic','status':0,'tag':100,'frame':frame.hex(),'cycles':10,'observed_active_edges':11,'actions':1,'fetch_lines':1,'frame_read_lines':1,'frame_write_lines':1,'rom_requests':0,'link_transactions':1,'wire_beats':5,'caller_setup_write_lines':32,'caller_result_read_lines':32,'caller_setup_edges':64,'caller_result_edges':64,'completion_hold_and_ack_edges':4}
  return v,r
 def test_independent_signed_output(self):
  v,r=self.fixture();self.assertEqual(V.check([v],[r])['cases'],1)
 def test_semantic_modified_result(self):
  v,r=self.fixture();r['frame']='00'+r['frame'][2:]
  with self.assertRaises(ValueError):V.check([v],[r])
 def test_missing_execution(self):
  v,r=self.fixture()
  with self.assertRaises(ValueError):V.check([v],[])
 def test_unpaid_transport(self):
  v,r=self.fixture();r['wire_beats']=4
  with self.assertRaises(ValueError):V.check([v],[r])
 def test_wrong_completion_tag(self):
  v,r=self.fixture();r['tag']=101
  with self.assertRaises(ValueError):V.check([v],[r])
 def test_missing_caller_cost(self):
  v,r=self.fixture();r['caller_setup_edges']=0
  with self.assertRaises(ValueError):V.check([v],[r])
if __name__=='__main__':unittest.main()
