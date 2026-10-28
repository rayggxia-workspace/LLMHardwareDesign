"""Counterexamples for the proof checker; synthetic logic, never a P&R library."""
import unittest
from buffer_graph_contract import compare

LIB='cell (BUF_X1) { pin(A) { direction : input; } pin(Z) { direction : output; function : "A"; } }'


class DirectedBufferProof(unittest.TestCase):
    def design(self):
        a={'u0':('BUF_X1','CORE'),'u1':('BUF_X1','CORE')}
        at={('u0','A'):('INPUT','a'),('u0','Z'):('OUTPUT','x'),('u1','A'):('INPUT','x'),('u1','Z'):('OUTPUT','z')}
        ap={'a':('INPUT','a'),'z':('OUTPUT','z')}
        b=dict(a,added=('BUF_X1','CORE'));bt=dict(at);bt['u1','A']=('INPUT','y')
        bt['added','A']=('INPUT','x');bt['added','Z']=('OUTPUT','y')
        return a,at,ap,b,bt,dict(ap)

    def test_directed_identity_insertion(self):
        q=compare(*self.design(),LIB,'synthetic_logic_only.lib')
        self.assertTrue(q['directed_original_driver_reachability']);self.assertEqual(q['added_identity_buffers'],1)

    def test_reverse_buffer_is_not_a_wire(self):
        args=list(self.design());args[4]['added','A']=('INPUT','y');args[4]['added','Z']=('OUTPUT','x')
        with self.assertRaisesRegex(AssertionError,'wrong direction'):compare(*args,LIB,'synthetic_logic_only.lib')

    def test_added_cycle_is_rejected(self):
        args=list(self.design());args[3]['cycle']=('BUF_X1','CORE');args[4]['cycle','A']=('INPUT','y');args[4]['cycle','Z']=('OUTPUT','x')
        with self.assertRaisesRegex(AssertionError,'cycle'):compare(*args,LIB,'synthetic_logic_only.lib')

    def test_original_bits_may_not_merge(self):
        args=list(self.design());args[4]['u1','A']=('INPUT','a')
        with self.assertRaises(AssertionError):compare(*args,LIB,'synthetic_logic_only.lib')

    def test_floating_terminals_are_not_one_electrical_net(self):
        args=list(self.design())
        for index in [0,3]:args[index]['floating']=('BLACKBOX','BLOCK')
        for index in [1,4]:
            args[index]['floating','A']=('INPUT','NULL');args[index]['floating','B']=('INPUT','NULL')
        args[4]['floating','A']=('INPUT','a')
        with self.assertRaisesRegex(AssertionError,'unconnected pin changed'):compare(*args,LIB,'synthetic_logic_only.lib')


if __name__=='__main__':unittest.main()
