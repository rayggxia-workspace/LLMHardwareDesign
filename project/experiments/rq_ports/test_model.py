import copy
import struct
import unittest
import numpy as np
from model import Graph,build,audit_schedule,beats,chunks
from numeric import packetize,receive

class Contracts(unittest.TestCase):
    def test_known_packet_granularity(self):
        wire=lambda n:sum(64+beats(v,word=64)*64 for _,v in chunks(n))
        self.assertEqual(wire(64),wire(16));self.assertEqual(wire(64),128)
        self.assertEqual(wire(1024)-wire(256),768)
        self.assertEqual(wire(1984),2048);self.assertEqual(wire(1985),2176)

    def test_known_schedules(self):
        g=Graph();g.add('a',3,('port',));g.add('b',3,('port',));s=g.schedule('fifo')
        self.assertEqual(s['cycles'],6);audit_schedule(g,s)
        g=Graph();g.add('a',3,('x',));g.add('b',3,('y',));s=g.schedule('critical')
        self.assertEqual(s['cycles'],3);audit_schedule(g,s)

    def test_capacity_and_empty_span(self):
        g=Graph()
        with self.assertRaises(ValueError):g.memory('S0',16,32760,())
        with self.assertRaises(ValueError):g.memory('S0',0,0,())
        with self.assertRaises(ValueError):beats(-1)

    def test_readback_rejects_resource_overlap(self):
        g=Graph();g.add('a',3,('x',));g.add('b',3,('x',));s=g.schedule('fifo')
        s['trace'][1]=[0,3];s['cycles']=3
        with self.assertRaises(AssertionError):audit_schedule(g,s)

    def test_rejects_dependency_tamper(self):
        g=Graph();a=g.add('a',3,('x',));g.add('b',2,('y',),(a,));s=g.schedule('fifo')
        s['trace'][1]=[0,2]
        with self.assertRaises(AssertionError):audit_schedule(g,s)

    def test_packet_bits_and_complete_k(self):
        a=np.arange(512,dtype='<i4').reshape(32,16)
        packets=packetize(a,1024,1)
        self.assertTrue(np.array_equal(a,receive(packets,1024,a.shape,'<i4',1)))
        corrupted=bytearray(packets[0]);struct.pack_into('<I',corrupted,28,896)
        with self.assertRaises(ValueError):receive([bytes(corrupted),*packets[1:]],1024,a.shape,'<i4',1)
        padded=np.arange(17,dtype='<i4').reshape(1,17)
        padded_packets=packetize(padded,1024,1)
        corrupted=bytearray(padded_packets[-1]);corrupted[-1]=1
        with self.assertRaises(ValueError):receive([bytes(corrupted)],1024,padded.shape,'<i4',1)

    def test_rq_interface_interval_and_credit(self):
        for place in ('near','shared'):
            g=build(1,1024,'dynamic_row',place,1,2,8);s=g.schedule('fifo');audit_schedule(g,s)
            starts=[s['trace'][n['id']][0] for n in g.nodes if n['label']=='RQ32 batch']
            self.assertGreaterEqual(min(b-a for a,b in zip(starts,starts[1:])),28)
            for job in range(4):
                chunks_=[n for n in g.nodes if n['label']=='matrix K128' and n['job']==job]
                self.assertEqual(sum(n['k_count'] for n in chunks_),1024)

    def test_early_rounding_counterexample(self):
        self.assertEqual(round(1/2)+round(1/2),0);self.assertEqual(round((1+1)/2),1)

if __name__=='__main__':unittest.main(verbosity=2)
