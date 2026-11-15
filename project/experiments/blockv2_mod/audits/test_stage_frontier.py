import unittest,struct
from native_stage_schedule import reserve,dependencies,verify_construction
from native_macro_work import measure
from native_diverse_beam import retain

def call(owner,after=()):
 raw=bytearray(128);struct.pack_into('<I',raw,0,0x314c5244)
 return {'group':owner,'descriptor_hex':raw.hex(),'after':list(after)}
D=measure({'calls':[call('P0')]})['work_units']

class StageTests(unittest.TestCase):
 def test_independent_ready_work_overlaps(self):
  a=reserve([call('P0')],{})
  c=reserve([call('P2')],a['resources'])
  self.assertEqual(c['start'],0);self.assertEqual(c['end'],a['end'])
 def test_child_is_selected_after_producer_but_overlaps_next_tile(self):
  a0=reserve([call('P0')],{})
  a1=reserve([call('P0')],a0['resources'])
  b0=reserve([call('P1')],a1['resources'],a0['end'])
  self.assertEqual(b0['start'],a0['end'])
  self.assertEqual(b0['end'],a1['end'])
 def test_release_owner_before_unrelated_tail(self):
  a=reserve([call('P0'),call('P1',[0])],{})
  c=reserve([call('P0')],a['resources'])
  self.assertEqual(c['start'],D);self.assertEqual(a['end'],2*D)
 def test_preserve_busy_controller(self):
  a=reserve([call('P0'),call('P0',[0])],{})
  b=reserve([call('P0')],a['resources'])
  self.assertEqual(b['start'],2*D)
 def test_workspace_lifetime_covers_other_owner_tail(self):
  a=reserve([call('P0'),call('P1',[0])],{},shared_keys=['scratch'])
  b=reserve([call('P2')],a['resources'],shared_keys=['scratch'])
  self.assertEqual(b['start'],a['end'])
 def test_emitted_dependencies_match_resource_release(self):
  rows,tails,terminal=dependencies([call('P0'),call('P1',[0])],0,(),{})
  more,tails,_=dependencies([call('P0')],2,(),tails)
  self.assertEqual(more[0]['after'],[0])
  self.assertEqual(measure({'calls':rows+more})['work_units'],2*D)
 def test_parent_commit_dependency_survives_other_owner(self):
  _,tails,parent=dependencies([call('P0')],0,(),{})
  rows,_,_=dependencies([call('P1')],1,parent,tails)
  self.assertIn(0,rows[0]['after'])
 def test_reject_child_selected_before_parent(self):
  with self.assertRaisesRegex(ValueError,'before producer'):
   verify_construction(['B','A'],{'A':[],'B':['A']})
 def test_independent_choice_order_is_not_fixed(self):
  graph={'A':[],'B':['A'],'C':[]}
  for order in (['A','C','B'],['C','A','B'],['A','B','C']):
   self.assertTrue(verify_construction(order,graph)['producer_before_consumer'])
 def test_wait_does_not_join_unrelated_running_branch(self):
  from native_mother_dag import actions,verify_actions
  calls=[dict(call('P0'),index=0,target=0,finish_proxy=10),
   dict(call('P2'),index=1,target=2,finish_proxy=100),
   dict(call('P1',[0]),index=2,target=1,finish_proxy=20)]
  program,_=actions(calls,wait_policy='predicted_first')
  self.assertTrue(verify_actions(calls,program)['passed'])
  wait_a=next(i for i,a in enumerate(program) if a['op']=='WAIT' and a['mask']==1)
  start_b=next(i for i,a in enumerate(program) if a['op']=='CALL' and a['call_index']==2)
  wait_c=next(i for i,a in enumerate(program) if a['op']=='WAIT' and a['mask']==4)
  self.assertLess(wait_a,start_b);self.assertLess(start_b,wait_c)
 def test_full_graph_masks_do_not_require_decimal_serialization(self):
  label={'time':1,'bytes':1,'remaining':0,'remaining_bytes':0,'done':1<<31034,
   'ready':(),'ends':{},'resources':{},'history':None,
   'state':{'backed':1<<100000,'memory':{}}}
  self.assertEqual(len(retain([label,label,label],3,{'P0':1024})),1)
 def test_distinct_tradeoffs_are_retained(self):
  def label(t,b,dirty):
   return {'time':t,'bytes':b,'remaining':0,'remaining_bytes':0,'done':1,'ready':(),
    'ends':{'A':t},'resources':{'P0':t},'history':None,
    'state':{'backed':0,'memory':{'P0':{i*32:{'address':i*512,'dirty':True} for i in range(dirty)}}}}
  fast=label(1,100,2);cheap=label(10,1,2);small=label(20,20,0)
  kept=retain([fast,cheap,small],3,{'P0':1024})
  self.assertEqual({x['time'] for x in kept},{1,10,20})
if __name__=='__main__':unittest.main()
