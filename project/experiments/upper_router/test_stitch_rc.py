import unittest
from stitch_rc import parse,stitch,field_capacitance


NATIVE='''*SPEF "ieee 1481-1999"
*C_UNIT 1 PF
*R_UNIT 1 OHM
*NAME_MAP
*1 a
*2 b
*3 driver_cell
*4 receiver_cell
*PORTS
a O
b I
*D_NET *1 0.1
*CONN
*P a O
*I *3:Z O
*CAP
1 a 0.1
*RES
1 *3:Z a 1.25
*END

*D_NET *2 0.2
*CONN
*P b I
*I *4:A I
*CAP
1 b 0.2
*RES
1 b *4:A 2.5
*END

'''


class StitchTest(unittest.TestCase):
    def test_asymmetric_native_capture_preserves_each_real_field_load(self):
        binding={'nets':{'A':{'logical_net':'a'},'B':{'logical_net':'b'}}}
        graph={'nets':{n:{'nodes':[0,1]} for n in ('a','b')}}
        scene={'names':['A','B','native signals','PG'],'grounded_indices':[3]}
        rows=[{'net':'A','total_ff':3,'node_self':[[2,.001],[1,.001]],
               'bins':[[1,0,0,-2,.001],[2,1,0,-1,.001]]},
              {'net':'B','total_ff':2,'node_self':[[1,.001],[1,.001]],
               'bins':[[0,0,0,-1,.001],[4,1,0,-1,.001]]}]
        caps=field_capacitance(binding,scene,rows,graph)
        self.assertEqual(caps['coupling'],[{'a':['A',0],'b':['B',0],'ff':1}])
        for name,total in [('A',3),('B',2)]:
            quiet=sum(c['ff'] for c in caps['ground'] if c['net']==name)+sum(c['ff'] for c in caps['coupling'] if name in (c['a'][0],c['b'][0]))
            self.assertEqual(quiet,total)
        self.assertTrue(all(c['miller'] for c in caps['ground'] if c['net']=='A'))
        self.assertEqual([c['miller'] for c in caps['ground'] if c['net']=='B'],[False])

    def test_preserves_real_native_resistors_and_internalizes_ports(self):
        binding={'nets':{'wire':{'logical_net':'logical','driver':'a','sinks':['b']}}}
        graph={'nets':{'logical':{'nodes':[{'id':0},{'id':1},{'id':2}],
                'ports':{'a':0,'b':2},'resistors':[{'a':0,'b':1,'ohm':.3},{'a':1,'b':2,'ohm':.4}]}}}
        caps={'ground':[{'net':'wire','node':1,'ff':5}],'coupling':[]}
        raw=stitch(NATIVE,binding,graph,caps)
        header,nets,ports=parse(raw)
        self.assertFalse(ports)
        self.assertNotIn('*P a',raw);self.assertNotIn('*P b',raw)
        self.assertEqual(len(nets),1)
        net=next(iter(nets.values()))
        self.assertEqual(sorted(float(r[-1]) for r in net['res']),[.3,.4,1.25,2.5])
        self.assertEqual(sorted(float(r[-1]) for r in net['caps']),[.005,.1,.2])
        self.assertEqual(float(net['total']),.305)
        resistors=[tuple(row[:2]) for row in net['res']]
        self.assertIn(('*3:Z','*1:3'),resistors)
        self.assertIn(('*1:5','*4:A'),resistors)


if __name__=='__main__':unittest.main()
