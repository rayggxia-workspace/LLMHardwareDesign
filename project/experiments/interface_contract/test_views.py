import copy
import json
import tempfile
from pathlib import Path
import unittest
from evidence import checksum_entries, check_observation, config, sha, verify_index, encoded
from views import header_ports, logical_ports, join_views, json_view


def logical(header='input logic [1:0] A, output logic Q', ports=None):
    ports = ports or {'A': {'direction':'input','bits':[2,3]},'Q':{'direction':'output','bits':[4]}}
    return logical_ports(encoded({'creator':'fixture','modules':{'fixture':{'ports':ports}}}),
                         ('module fixture ('+header+'); endmodule').encode(),'fixture')


def physical(logic):
    lib={'source_sha256':'test', 'cell':{'raw_name':'fixture','pg_pins':[],
         'bits':[{'bit_name':n,'raw_name':n,'line':1,'effective_direction':b['direction']}
                 for n,b in logic['bits'].items()]}}
    lef={'source_sha256':'test','macro':{'name':'fixture',
         'pins':[{'name':n,'direction':b['direction'].upper(),'use':'SIGNAL','line':1,
                  'ports':[{'rects':[{'layer':'M1','rect_dbu':[0,0,1,1],'line':2}]}]}
                 for n,b in logic['bits'].items()]}}
    return lib,lef


class ViewTests(unittest.TestCase):
    def test_literal_multidimensional_and_inheritance(self):
        d=header_ports(b'module M(input logic [3:0][7:0] a,b, output wire q); endmodule','M')
        self.assertEqual(d['a']['declared_width'],32)
        self.assertEqual(d['a'],d['b'])

    def test_scalar_and_one_bit_vector(self):
        v=logical('input logic [0:0] a, output logic q',{'a':{'direction':'input','bits':[2]},'q':{'direction':'output','bits':[3]}})
        self.assertEqual(v['ports']['a']['bits'],['a[0]'])
        self.assertEqual(v['ports']['q']['bits'],['q'])

    def test_offset_ascending_lsb_order(self):
        v=logical('input logic [4:6] a',{'a':{'direction':'input','bits':[3,4,5],'offset':4,'upto':1}})
        self.assertEqual(v['ports']['a']['bits'],['a[6]','a[5]','a[4]'])
        self.assertEqual(v['bits']['a[4]']['yosys_bit'],5)

    def test_reversed_header_metadata_rejected(self):
        with self.assertRaises(ValueError):
            logical('input logic [4:6] a',{'a':{'direction':'input','bits':[3,4,5],'offset':4}})

    def test_named_type_width_explicitly_unresolved(self):
        v=logical('input cmd_t cmd',{'cmd':{'direction':'input','bits':[2,3,4]}})
        self.assertIsNone(v['ports']['cmd']['boundary']['declared_width'])
        self.assertEqual(v['ports']['cmd']['width'],3)

    def test_aliases_and_constants_keep_boundary_pins(self):
        v=logical('output logic a,b, output logic [1:0] c',{'a':{'direction':'output','bits':[7]},
             'b':{'direction':'output','bits':[7]},'c':{'direction':'output','bits':['0','1']}})
        self.assertEqual(v['aliases'],[{'yosys_bit':7,'bit_names':['a','b']}])
        self.assertEqual(len(v['constants']),2)
        self.assertEqual(len(v['bits']),4)

    def test_invalid_yosys_bit(self):
        for bad in [True,-1,'2',None]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                logical('input logic a',{'a':{'direction':'input','bits':[bad]}})

    def test_duplicate_json_keys_fail(self):
        with self.assertRaises(ValueError):
            json_view(b'{"ports":{"A":1,"A":2}}')

    def test_width_direction_and_port_set_fail(self):
        for ports in [{'A':{'direction':'input','bits':[2]},'Q':{'direction':'output','bits':[4]}},
                      {'A':{'direction':'output','bits':[2,3]},'Q':{'direction':'output','bits':[4]}},
                      {'A':{'direction':'input','bits':[2,3]}}]:
            with self.subTest(ports=ports),self.assertRaises(ValueError):
                logical(ports=ports)

    def test_exact_name_join_ignores_lexical_order(self):
        v=logical(); lib,lef=physical(v)
        lef['macro']['pins'].reverse()
        lib['cell']['bits'].reverse()
        joined=join_views(v,lib,lef)
        self.assertEqual(joined['bits']['A[0]']['lef']['name'],'A[0]')

    def test_missing_extra_duplicate_and_direction_fail(self):
        for mutation in ['missing','extra','duplicate','direction','wrong_cell','wrong_name']:
            v=logical(); lib,lef=physical(v)
            if mutation=='missing':lib['cell']['bits'].pop()
            if mutation=='extra':lib['cell']['bits'].append({'bit_name':'unused'})
            if mutation=='duplicate':lib['cell']['bits'].append(lib['cell']['bits'][0])
            if mutation=='direction':lib['cell']['bits'][0]['effective_direction']='output'
            if mutation=='wrong_cell':lib['cell']['raw_name']='other'
            if mutation=='wrong_name':lef['macro']['pins'][0]['name']='A[100]'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                join_views(v,lib,lef)

    def test_pg_and_clock_not_erased(self):
        v=logical('input logic clk',{'clk':{'direction':'input','bits':[2]}})
        lib,lef=physical(v)
        lib['cell']['bits'].append({'bit_name':'VDD','raw_name':'VDD','effective_direction':'inout'})
        lef['macro']['pins'].append({'name':'VDD','use':'POWER','direction':'INOUT','ports':[{'rects':[]}]})
        joined=join_views(v,lib,lef)
        self.assertEqual(joined['bits']['clk']['classification'],'shared_clock')
        self.assertEqual(len(joined['power']),1)
        self.assertFalse(joined['power'][0]['supply_connectivity_verified'])

    def test_unsupported_header_fails(self):
        for header in ['input logic [W-1:0] a','input other_t a','input logic a=1','inout logic a']:
            with self.subTest(header=header),self.assertRaises(ValueError):
                logical(header,{'a':{'direction':'input','bits':[2]}})


    def test_real_pg_pin_is_classified_by_explicit_type(self):
        from liberty_profile import parse_liberty
        v=logical('input logic clk',{'clk':{'direction':'input','bits':[2]}})
        _,lef=physical(v)
        lef['macro']['pins'].append({'name':'VDD','use':'POWER','direction':'INOUT','ports':[{'rects':[]}]})
        lib=parse_liberty(b'library (L) { cell (fixture) { pin (clk) {direction:input;} pg_pin (VDD) { pg_type:primary_power; } } }')
        joined=join_views(v,lib,lef)
        self.assertEqual(joined['power'][0]['liberty']['kind'],'pg_pin')
        lef['macro']['pins'][-1]['use']='GROUND'
        with self.assertRaises(ValueError):
            join_views(v,lib,lef)


class EvidenceTests(unittest.TestCase):
    def test_checksum_duplicate_malformed(self):
        line='a'*64+'  boundary.sv\n'
        self.assertEqual(checksum_entries(line.encode())['boundary.sv'],'a'*64)
        for bad in [line+line,'a'*63+'  file\n','g'*64+'  file\n']:
            with self.assertRaises(AssertionError):
                checksum_entries(bad.encode())

    def test_exact_file_membership_and_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'a').write_bytes(b'a');(root/'manifest.json').write_bytes(b'{}')
            files={'a':{'bytes':1,'sha256':sha(b'a')}}
            verify_index(root,files,'manifest.json')
            (root/'extra').write_bytes(b'')
            with self.assertRaises(AssertionError): verify_index(root,files,'manifest.json')
            (root/'extra').unlink()
            (root/'a').write_bytes(b'b')
            with self.assertRaises(AssertionError): verify_index(root,files,'manifest.json')

    def test_capture_changed_stat_path_hash_size(self):
        cfg=config((Path(__file__).parent/'inputs.json').read_bytes())
        item=copy.deepcopy(cfg['files'][0]);item['previous_observed_bytes']=3;item['prior_expected_sha256']=sha(b'abc')
        row={'requested_path':cfg['allowed_root']+'/'+item['relative_path'],
             'resolved_path':cfg['allowed_root']+'/'+item['relative_path'],'stat_before':[1,2,3,4],
             'stat_after':[1,2,3,4],'bytes':3,'sha256':sha(b'abc')}
        check_observation(cfg,item,row,b'abc')
        for field,value in [('resolved_path','/other/file'),('stat_after',[1,2,3,5]),('bytes',4),('sha256','0'*64)]:
            bad={**row,field:value}
            with self.subTest(field=field),self.assertRaises(AssertionError):
                check_observation(cfg,item,bad,b'abc')

    def test_scope_widening_rejected(self):
        data=json.loads((Path(__file__).parent/'inputs.json').read_bytes())
        data['files'][0]['relative_path']='../other'
        with self.assertRaises(AssertionError): config(encoded(data))


if __name__=='__main__':
    unittest.main()
