import json
from pathlib import Path
import tempfile
import unittest
from assemble_spef import assemble
from native_inventory import sha
from stitch_rc import parse


SOURCE='''*SPEF "ieee 1481-1999"
*DESIGN "source"
*C_UNIT 1 PF
*R_UNIT 1 OHM
*NAME_MAP
*1 late
*2 cell
*PORTS
late O
*D_NET *1 0.25
*CONN
*P late O
*I *2:Z O *D BUF_X1
*CAP
1 *1:1 0.25
*RES
1 late *1:1 0.125
2 *1:1 *2:Z 0.375
*END
'''


class SpefTest(unittest.TestCase):
    def test_native_rc_identity_and_flat_divider_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);native=root/'native.spef';native.write_text(SOURCE)
            lib={'resource':{'views':{'odb':{'path':str(root/'native.odb')}},
                'inventory':{'files':{'native/6_final.spef':{'sha256':sha(native)}}}}}
            base={'assemblies':[{'id':g,'template':'resource'} for g in ('first','second')],'endpoints':{}}
            out=root/'assembled.spef';assemble(base,lib,{'nets':{}},out)
            header,nets,ports=parse(out.read_text())
            self.assertEqual(set(ports),{'first/late','second/late'})
            self.assertIn(r'first\/late',header);self.assertIn('SRC_resource_BUF_X1',out.read_text())
            self.assertEqual(len(nets),2)
            for row in nets.values():
                self.assertEqual([r[-1] for r in row['res']],['0.125','0.375'])
                self.assertEqual([c[-1] for c in row['caps']],['0.25'])


if __name__=='__main__':unittest.main()
