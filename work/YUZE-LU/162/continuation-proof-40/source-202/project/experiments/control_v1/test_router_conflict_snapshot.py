import tempfile,unittest
from pathlib import Path
from router_conflict_snapshot import inspect


class SnapshotTest(unittest.TestCase):
    def check_paths(self,nets,paths):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'paths.txt';lines=[str(len(nets))]
            for name,branches in paths.items():
                lines.append(name+' '+str(len(branches)))
                for branch in branches:lines.append(str(len(branch))+' '+' '.join(str(v)for point in branch for v in point))
            p.write_text('\n'.join(lines)+'\n')
            return inspect(p,nets,24,24,{n:-1 for n in nets})

    def test_complete_crossing_counted_and_never_accepted(self):
        r=self.check_paths({'h':[(5,8),(9,8)],'v':[(7,6),(7,10)]},
            {'h':[[(x,8,0)for x in range(5,10)]],'v':[[(7,y,0)for y in range(6,11)]]})
        self.assertEqual((r['conflict_nodes'],r['excess_occupancy'],r['occupied_cells'],r['summed_tree_vertices']),(1,1,9,10))
        self.assertEqual(sum(n['conflict_vertices']for n in r['top_nets']),2)
        self.assertTrue(r['all_trees_flood_verified'])
        self.assertNotIn('passed',r)

    def test_actual_layer_crossing_is_separate_resource(self):
        r=self.check_paths({'h':[(6,6),(8,6)]},{'h':[[(6,6,0),(6,6,1),(7,6,1),(8,6,1),(8,6,0)]]})
        self.assertEqual(r['conflict_nodes'],0)
        self.assertEqual(r['summed_tree_vertices'],5)

    def test_disconnected_fragments_rejected(self):
        with self.assertRaises(AssertionError):self.check_paths({'h':[(5,8),(9,8)]},{'h':[[(5,8,0)],[(9,8,0)]]})

    def test_odd_via_rejected(self):
        with self.assertRaises(AssertionError):self.check_paths({'h':[(5,6),(5,7)]},{'h':[[(5,6,0),(5,6,1),(5,7,1),(5,7,0)]]})


if __name__=='__main__':unittest.main()
