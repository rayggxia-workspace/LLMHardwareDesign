"""Real geometric boundary cases behind the zero-wire feedthrough bug."""
import unittest
from check_access import check_rows


def row(link,box,layer='metal5',kind='ITERM'):
    return dict(net='n',layer=layer,kind=kind,link=link,**dict(zip(['x0','y0','x1','y1'],box)))


class ZeroWireAccess(unittest.TestCase):
    def run_rows(self,a,b):
        marker=row('missing',[0,0,0,0],'UNROUTED','UNROUTED')
        return check_rows(iter([marker,a,b]),True)

    def test_overlapping_real_terminals_need_no_extra_wire(self):
        self.assertTrue(self.run_rows(row('I:u/A',[100,100,380,380]),row('B:p',[100,100,380,380],kind='BTERM'))['pass'])

    def test_one_DBU_gap_still_fails(self):
        self.assertFalse(self.run_rows(row('I:u/A',[100,100,380,380]),row('B:p',[381,100,661,380],kind='BTERM'))['pass'])

    def test_closed_metal_edge_touch_connects(self):
        self.assertTrue(self.run_rows(row('I:u/A',[100,100,380,380]),row('B:p',[380,100,660,380],kind='BTERM'))['pass'])

    def test_XY_overlap_on_different_layers_without_via_fails(self):
        self.assertFalse(self.run_rows(row('I:u/A',[100,100,380,380]),row('B:p',[100,100,380,380],'metal6','BTERM'))['pass'])

    def test_no_real_terminal_geometry_never_passes(self):
        r=check_rows(iter([row('missing',[0,0,0,0],'UNROUTED','UNROUTED')]),True)
        self.assertFalse(r['pass'])


if __name__=='__main__':unittest.main()
