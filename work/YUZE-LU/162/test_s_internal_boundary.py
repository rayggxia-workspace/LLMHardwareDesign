"""Reject accidental transfer of the old external-S physical boundary."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'project/experiments/control_v1'))
from boundary_links import validate

class Boundary(unittest.TestCase):
    def fixture(self):
        types=['block_feed_s_macro','control_reset_distribution']+['fixture_'+str(i)for i in range(18)]
        instances={'macro_s':types[0],'reset_distribution':types[1]}
        instances.update({'instance_'+str(i):t for i,t in enumerate(types[2:])})
        instances.update({'queue_'+str(i):types[2]for i in range(6)})
        instances['link_macro_1_0']='control_link8'
        proof=dict(owner='block_feed_s_macro M1-M10',all_four_gates_fresh=True,no_new_registers=True,no_latency_or_protocol_change=True)
        manifest=dict(leaves={t:{}for t in types+['control_link8']})
        manifest['leaves'][types[0]]['S_internal_drive']=proof
        graph=dict(instances=instances,instance_count=27,S_internal_drive=copy.deepcopy(proof),S_external_link_instances=0,
                   boundary_links=dict(original_topology_exact_contraction=True,payload_register_bits=0,new_state_bits=1,
                       links=[dict(instance='link_macro_1_0',source_instance='macro_1',state_bits=1,payload_register_bits=0)]))
        return manifest,graph

    def test_new_s_keeps_other_fixed_state_owners(self):
        manifest,graph=self.fixture();validate(manifest,graph)

    def test_old_s_links_or_missing_new_qualification_rejected(self):
        for corruption in ['source','instance','missing','stale','latency']:
            with self.subTest(corruption=corruption):
                manifest,graph=self.fixture()
                if corruption=='source':graph['boundary_links']['links'][0]['source_instance']='macro_s'
                elif corruption=='instance':
                    graph['instances']['link_macro_s_0']=graph['instances'].pop('link_macro_1_0')
                    graph['boundary_links']['links'][0]['instance']='link_macro_s_0'
                elif corruption=='missing':del graph['S_internal_drive']
                elif corruption=='stale':graph['S_external_link_instances']=99
                else:
                    manifest['leaves']['block_feed_s_macro']['S_internal_drive']['no_latency_or_protocol_change']=False
                    graph['S_internal_drive']['no_latency_or_protocol_change']=False
                with self.assertRaises(AssertionError):validate(manifest,graph)

if __name__=='__main__':unittest.main()
