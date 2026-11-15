import unittest,struct
from native_stage_schedule import reserve,dependencies,verify_construction
from native_macro_work import measure
from native_diverse_beam import retain

def call(owner,after=()):
 raw=bytearray(128);struct.pack_into('<I',raw,0,0x314c5244)
 return {'group':owner,'descriptor_hex':raw.hex(),'after':list(after)}
D=measure({'calls':[call('P0')]})['work_units']

class StageTests(unittest.TestCase):
 def test_independent_matrix_ranges_preserve_child_data_edges(self):
  from native_range_frontier import expand
  def tile(value,offset,source=None):
   out={'write':{'value':value,'element_offset':offset,'elements':128}}
   if source:out['read']=[{'root':source,'segments':[{'source_element':offset,'elements':128}]}]
   return out
  tasks={'A':{'kind':'MatMul','tiles':[tile('a',0),tile('a',128)]},
         'B':{'kind':'Add','tiles':[tile('b',0,'a'),tile('b',128,'a')]}}
  _,deps,_,parts=expand(tasks,{'A':[],'B':['A']},['A','B'],serialize_ranges=False)
  a0,a1=parts['A'];b0,b1=parts['B']
  self.assertEqual(deps[a0],[]);self.assertEqual(deps[a1],[])
  self.assertEqual(deps[b0],[a0]);self.assertIn(a1,deps[b1])
  self.assertNotIn(a1,deps[b0])
  _,legacy,_,_=expand(tasks,{'A':[],'B':['A']},['A','B'])
  self.assertIn(a0,legacy[a1])
 def test_mpr_payload_reuses_activation_across_groups(self):
  def descriptor(groups,head16):
   raw=bytearray(128);struct.pack_into('<I',raw,0,0x3152504d)
   raw[74]=groups;struct.pack_into('<H',raw,76,256);raw[82]=1;raw[83]=head16
   return {'calls':[{'descriptor_hex':raw.hex(),'group':'P0','after':[]}]}
  one=measure(descriptor(1,0),cost_model='service-payload/2')
  sixteen=measure(descriptor(16,0),cost_model='service-payload/2')
  head=measure(descriptor(16,1),cost_model='service-payload/2')
  # Additional output groups require weights, not another copy of input per group.
  self.assertEqual(sixteen['ddr_read_bytes_upper']-one['ddr_read_bytes_upper'],15*2*1088)
  self.assertEqual(head['ddr_read_bytes_upper']-sixteen['ddr_read_bytes_upper'],16*2*64)
  self.assertEqual(sixteen['sram_words']-one['sram_words'],15*2)
  old=measure(descriptor(16,0))
  self.assertGreater(old['ddr_read_bytes_upper'],sixteen['ddr_read_bytes_upper'])
 def test_new_cost_reservation_matches_emitted_hints(self):
  from native_stage_schedule import completion_hints
  raw=bytearray(128);struct.pack_into('<I',raw,0,0x3152504d)
  raw[74]=16;struct.pack_into('<H',raw,76,128);raw[82]=1
  c={'descriptor_hex':raw.hex(),'group':'P0','after':[]}
  r=reserve([c],{},cost_model='service-payload/2')
  rows,_,_=dependencies([c],0,(),{})
  self.assertEqual(r['end'],completion_hints(rows,cost_model='service-payload/2')[-1])
 def test_source_depth_cache_matches_full_progress_oracle(self):
  from native_source_depth import SourceDepth
  import random
  rng=random.Random(219)
  for _ in range(20):
   names=list(range(8));deps={p:[q for q in names[:p] if rng.random()<.25] for p in names}
   parents=[p for p in names for _ in range(rng.randint(1,5))]
   parts={p:sum(1<<i for i,v in enumerate(parents) if v==p) for p in names}
   oracle=SourceDepth(names,deps,parts,parents,2)
   order=list(range(len(parents)));rng.shuffle(order);done=opened=0
   for task in order:
    opened=oracle.advance(opened,done,task);done|=1<<task
    exact=sum(1<<p for p in names if done&parts[p] and done&parts[p]!=parts[p])
    self.assertEqual(opened,exact)
    longest={}
    for p in names:longest[p]=int(bool(exact>>p&1))+max((longest[q] for q in deps[p]),default=0)
    self.assertEqual(oracle.legal(opened),max(longest.values())<=2)
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
