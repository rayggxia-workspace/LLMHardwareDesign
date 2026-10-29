"""Negative controls for exact same-net geometry repair scope."""
import tempfile
import unittest
from pathlib import Path
from linkfix_s_patch import PATCHES,verify_def_change


class ScopeControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.before=Path(self.tmp.name)/'before.def';self.after=Path(self.tmp.name)/'after.def'
        old=b'VERSION 5.8 ;\nNETS 3 ;\n';new=old
        for _,name,(x0,y0,x1,y1)in PATCHES:
            prefix=b'- '+name+b' ( u A ) + ROUTED metal2 ( 1 2 ) ( 3 2 ) '
            old+=prefix+b';\n'
            new+=prefix+('NEW metal2 ( %d %d ) RECT ( 0 0 %d %d ) ;\n'%(x0,y0,x1-x0,y1-y0)).encode()
        tail=b'- untouched ( z A ) + ROUTED metal3 ( 5 6 ) ( 7 6 ) ;\nEND NETS\n'
        self.before.write_bytes(old+tail);self.after.write_bytes(new+tail)

    def test_exact_additions(self):
        verify_def_change(self.before,self.after)

    def test_other_net_edit_rejected(self):
        self.after.write_bytes(self.after.read_bytes().replace(b'( 7 6 )',b'( 8 6 )'))
        with self.assertRaises(AssertionError):verify_def_change(self.before,self.after)

    def test_extra_target_edit_rejected(self):
        self.after.write_bytes(self.after.read_bytes().replace(b'( 3 2 )',b'( 4 2 )',1))
        with self.assertRaises(AssertionError):verify_def_change(self.before,self.after)


if __name__=='__main__':unittest.main()
