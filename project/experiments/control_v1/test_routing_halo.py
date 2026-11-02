"""Coordinate/identity controls for a routing-only whitespace experiment."""
import copy,unittest
from routing_halo import expand

class HaloControls(unittest.TestCase):
    def test_translation_perimeter_and_identity(self):
        s=dict(width_um=256,height_um=256,placements_um={'a':[64,64],'b':[128,128]},
            orientations={'a':0,'b':0},graph_sha256='source-bound-graph',graph='original.json',
            external_grid_pins={'left':[8,20],'right':[56,22],'top':[24,8],'bottom':[26,56],'corner':[8,8]},
            terminals={'one':[[8,20],[20,20]],'two':[[56,22],[30,30]],'three':[[24,8],[32,32]],
                'four':[[26,56],[34,34]],'five':[[8,8],[36,36]]})
        before=copy.deepcopy(s)
        for halo in [512,1024,2048]:
            r=expand(s,halo);self.assertEqual(s,before)
            self.assertEqual(r['width_um']*r['height_um'],(256+2*halo)**2)
            self.assertEqual(r['placements_um']['b'][0]-r['placements_um']['a'][0],64)
            self.assertEqual(r['graph_sha256'],s['graph_sha256']);self.assertEqual(r['orientations'],s['orientations'])
            nx=r['width_um']//4;ny=r['height_um']//4
            for x,y in r['external_grid_pins'].values():self.assertTrue(x in (8,nx-8)or y in (8,ny-8))
            self.assertEqual(r['terminals']['one'][1],[20+halo//4,20+halo//4])
            self.assertEqual(r['terminals']['one'][0],r['external_grid_pins']['left'])

    def test_rejects_invalid_halo_or_off_perimeter_pin(self):
        with self.assertRaises(AssertionError):expand({},1)
        s=dict(width_um=256,height_um=256,placements_um={},orientations={},graph_sha256='x',external_grid_pins={'bad':[20,20]},terminals={})
        with self.assertRaises(AssertionError):expand(s,512)

if __name__=='__main__':unittest.main()
