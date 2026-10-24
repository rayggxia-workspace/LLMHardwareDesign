import copy, unittest
from fractions import Fraction
from collections import Counter
import grouped_service as g

class GroupedCalendar(unittest.TestCase):
    def summary(self):
        b=g.base.Builder('r32_d8',1)
        for name,n in [('const.out_weight_w8',2560*4096),('const.out_scale_q31',2560*4),('const.out_scale_exp',2560*2),('const.out_bias_q12',2560*4),('ext.out',2560*4)]:b.add(name,'EXT',n)
        return {'inventory':b.inventory,'allocations':list(b.alloc.values()),'used_bytes':dict(b.used)}
    def test_actual_signed_high_digits_and_products(self):
        cases=[(-(1<<63),-(1<<31)),((1<<63)-1,(1<<31)-1),(-1,-1),(0,0),(7,-11),(-20000000000,1337)]
        for a,b in cases:
            digits=g.signed_digits(a,64);self.assertTrue(all(-128<=v<=127 for v in digits));self.assertEqual(sum(v<<(7*i) for i,v in enumerate(digits)),a);self.assertEqual(g.rq_product_micro(a,b,64),a*b)
        with self.assertRaises(ValueError):g.signed_digits(1<<63,64)
    def test_core_recipe_matches_shared_probe_and_extra_cost_explicit(self):
        for pbits,expected in [('64',265),('128',837)]:
            r=g.RQ_RECIPES[pbits];self.assertEqual(r['products']+r['wide_adds']*r['wide_add_byte_ops'],expected);self.assertEqual(sum(r['RNE_breakdown'].values()),r['RNE_byte_ops'])
    def test_inventory_conserved_no_private_M_ALU(self):
        src=self.summary();a=g.Builder(src,'near_m');b=g.Builder(src,'shared_v')
        self.assertEqual(a.inventory,b.inventory);self.assertEqual(a.alloc,b.alloc);self.assertFalse(a.inventory['grouped_kernel']['new_private_M_ALU'])
        self.assertEqual(a.inventory['matrix']['effective_PEs_single_row'],16);self.assertEqual(a.inventory['lanes']['S8_lanes'],8)
        self.assertTrue(all(a.used[k]<=a.cap[k] for k in a.cap))
    def test_engine_every_operand_uses_bank_and_bus(self):
        b=g.Builder(self.summary(),'near_m');body=[];r=b.engine(body,b.obj('product'),4,128);w=b.engine(body,b.obj('product'),0,256,'write')
        self.assertEqual([x['name'] for x in r['resources']],['bank.M','BUS']);self.assertEqual([x['name'] for x in w['resources']],['BUS','bank.M'])
        self.assertEqual(r['counts']['wire_bytes'],r['counts']['engine_wire_bytes']);self.assertEqual(r['counts']['src_beats'],9);self.assertEqual(r['counts']['dst_beats'],0);self.assertEqual(r['counts']['engine_local_beats'],9);self.assertEqual(r['counts']['engine_wire_bytes'],160);self.assertLessEqual(w['FIFO_peak_bytes'],2048)
    def test_all_matrix_group_sizes_charge_exact_full_group(self):
        for k in (256,512,4096):
            b=g.Builder(self.summary(),'near_m');body=[];b.matrix_group(body,0,k);b.count_tree(body,1)
            self.assertEqual(b.totals['matrix_mac'],16*k);self.assertEqual(b.totals['copy_byte'],16*k+64)
    def test_grouped_rq_45_products_44_adds_and_i128(self):
        for groups,products,adds,pbits in [(1,25,24,64),(8,45,44,128),(16,45,44,128)]:
            b=g.Builder(self.summary(),'near_m');body=[];b.rq(body,'local.m_acc' if groups==1 else b.obj('sum'),groups);b.count_tree(body,1)
            self.assertEqual(b.totals['wide_s8_product'],16*products);self.assertEqual(b.totals['wide_add'+str(pbits)],16*adds);self.assertEqual(b.totals['rq_rne'+str(pbits)+'_complete'],16)
            self.assertGreater(b.totals['engine_operand_read_bytes'],0);self.assertGreater(b.totals['engine_operand_write_bytes'],0)
    def test_real_partial_crossing_sharedV_only(self):
        a=g.Builder(self.summary(),'near_m');b=g.Builder(self.summary(),'shared_v');aa=[];bb=[]
        a.align(aa,0,16,[1]*16,1);b.align(bb,0,16,[1]*16,1);a.count_tree(aa,1);b.count_tree(bb,1)
        self.assertEqual(b.totals['payload_bytes']-a.totals['payload_bytes'],64);self.assertEqual(a.totals['engine_operand_read_bytes'],b.totals['engine_operand_read_bytes']);self.assertEqual(a.totals['signextend_i32_i64'],b.totals['signextend_i32_i64'])
    def test_inherited_event_content_bound_despite_new_global_time(self):
        b=g.Builder(self.summary(),'near_m');e={'id':4,'stage':'input_norm.reduce','token':0,'phase':'prefill','start':111,'end':114,'deps':[3],'meta':{'group':2560},'body':[{'kind':'compute','start':0,'end':3,'resources':[{'name':'VR8','start':0,'end':3}],'counts':{'add64':2}}]};digest=g.canonical_sha(e);b.inherit(e)
        self.assertEqual(b.events[0]['inherited_canonical_sha256'],digest);self.assertEqual(g.canonical_sha(b.events[0]),digest);self.assertEqual(b.events[0]['start'],0);self.assertEqual(b.clock,3)
        changed=copy.deepcopy(e);changed['meta']['group']=128;self.assertNotEqual(g.canonical_sha(changed),digest)
if __name__=='__main__':unittest.main()
