import json
from pathlib import Path
import tempfile
import unittest
from r_contained_rectangles import markers,compare


class RectangleGuardTest(unittest.TestCase):
    def test_actual_markers_and_reject_foreign_or_unbounded_geometry(self):
        root=Path(__file__).resolve().parents[3]
        raw=(root/'work/YUZE-LU/143/r-input-hold/buffer-129/candidate-native-drc.rpt').read_text()
        rows=markers(raw);self.assertEqual(len(rows),822)
        for broken in (raw.replace('srcs: net:','srcs: net:foreign net:',1),raw.replace('Metal Spacing','Short',1),raw+'unexpected text'):
            with self.assertRaises(AssertionError):markers(broken)

    def test_exact_added_paths_preserve_original_routes_and_connections(self):
        old=b'DESIGN example ;\nNETS 1 ;\n    - n ( ff D ) ( source Z ) + USE SIGNAL\n      + ROUTED metal2 ( 100 200 ) ( 300 * ) ;\nEND NETS\nEND DESIGN\n'
        new=old.replace(b'( 300 * ) ;',b'( 300 * )\n      NEW metal2 ( 120 190 ) RECT ( 0 0 20 20 ) ;')
        plan=[dict(net='n',layer='metal2',box_dbu=[120,190,140,210])]
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.def';b=Path(d)/'b.def';a.write_bytes(old);b.write_bytes(new)
            self.assertEqual(compare(a,b,plan)['added_contained_rectangles'],1)
            for broken in (new.replace(b'ff D',b'wrong D'),new.replace(b'( 300 * )',b'( 400 * )'),new.replace(b'20 20',b'30 20'),new.replace(b'DESIGN example',b'DESIGN bad')):
                b.write_bytes(broken)
                with self.assertRaises(AssertionError):compare(a,b,plan)


if __name__=='__main__':unittest.main()
