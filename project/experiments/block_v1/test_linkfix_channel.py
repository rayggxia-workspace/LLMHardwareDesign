"""Channel-routing controls for the actual coincident-column bus failure."""
import unittest
from linkfix_channel import Channels


class ChannelControls(unittest.TestCase):
    def test_two_overlapping_vertical_pairs_do_not_share_metal(self):
        ends={'a':[(12,20),(12,60)],'b':[(12,24),(12,64)]}
        router=Channels(80,90,ends)
        a=router.route('a',*ends['a']);b=router.route('b',*ends['b'])
        self.assertFalse(set(a)&set(b))
        self.assertEqual((a[0][1:],a[-1][1:]),tuple(ends['a']))
        self.assertEqual((b[0][1:],b[-1][1:]),tuple(ends['b']))
        for cut in router.cuts:
            for other in router.cuts-{cut}:
                self.assertGreater(abs(cut[0]-other[0])+abs(cut[1]-other[1]),1)

    def test_different_nets_cannot_claim_one_terminal(self):
        with self.assertRaises(AssertionError):
            Channels(30,30,{'a':[(8,8),(12,12)],'b':[(8,8),(16,16)]})

    def test_dense_column_preserves_access_for_later_receivers(self):
        ends={str(i):[(8+2*i,40),(40,8+2*i)]for i in range(12)}
        router=Channels(90,90,ends,access=True,access_depth=2)
        paths=[router.route(str(i),*ends[str(i)])for i in range(12)]
        for i,path in enumerate(paths):
            self.assertEqual(path[0],(0,*ends[str(i)][0]))
            self.assertEqual(path[-1],(0,*ends[str(i)][1]))
            for other in paths[:i]:self.assertFalse(set(path)&set(other))

    def test_orthogonal_tracks_route_dense_row_to_column(self):
        ends={str(i):[(8+2*i,40),(40,8+2*i)]for i in range(12)}
        router=Channels(90,90,ends,access=True,access_depth=2,orthogonal=True)
        paths=[router.route(str(i),*ends[str(i)])for i in range(12)]
        for i,path in enumerate(paths):
            self.assertEqual(path[0],(0,*ends[str(i)][0]))
            self.assertEqual(path[-1],(0,*ends[str(i)][1]))
            for other in paths[:i]:self.assertFalse(set(path)&set(other))
        for cut in router.cuts:
            for other in router.cuts-{cut}:
                self.assertGreater(abs(cut[0]-other[0])+abs(cut[1]-other[1]),1)

    def test_aligned_paired_rows_have_disjoint_straight_tracks(self):
        ends={'a':[(12,20),(12,60)],'b':[(12,40),(12,62)],
              'c':[(14,20),(14,60)],'d':[(14,40),(14,62)]}
        router=Channels(60,80,ends)
        paths=[router.seed_aligned(k,*ends[k],-1 if ends[k][0][1]==20 else 0)for k in ends]
        for i,path in enumerate(paths):
            for other in paths[:i]:self.assertFalse(set(path)&set(other))
        for cut in router.cuts:
            for other in router.cuts-{cut}:self.assertGreater(abs(cut[0]-other[0])+abs(cut[1]-other[1]),1)
        with self.assertRaises(AssertionError):router.seed_aligned('bad',(20,10),(22,30),0)


if __name__=='__main__':unittest.main()
