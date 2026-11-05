import tempfile,unittest
from pathlib import Path
from router_conflict_snapshot import inspect,inputs


class SnapshotTest(unittest.TestCase):
    def test_global_diagnostic_known_scene_grids(self):
        from global_snapshot_analysis import validate_graph_grid
        graph={'instances':dict({'macro_r':'r_stream_local'},**{'instance_'+str(i):'type'for i in range(344)})}
        for grid in [(2345,2345),(3070,3252)]:
            validate_graph_grid([*grid,11149],range(11149),graph)

    def test_global_diagnostic_rejects_unknown_or_incomplete_scene(self):
        from global_snapshot_analysis import validate_graph_grid
        graph={'instances':dict({'macro_r':'r_stream_local'},**{'instance_'+str(i):'type'for i in range(344)})}
        cases=[([3252,3070,11149],range(11149),graph),([3070,3251,11149],range(11149),graph),
               ([3070,3252,11148],range(11149),graph),([3070,3252,11149],range(11148),graph),
               ([3070,3252,11149],range(11149),{'instances':{k:v for k,v in graph['instances'].items()if k!='macro_r'}})]
        for header,nets,scene in cases:
            with self.subTest(header=header,count=len(nets),instances=len(scene['instances'])):
                with self.assertRaises(AssertionError):validate_graph_grid(header,nets,scene)

    def check_paths(self,nets,paths,parents=None):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'paths.txt';lines=[str(len(nets))]
            for name,branches in paths.items():
                lines.append(name+' '+str(len(branches)))
                for branch in branches:lines.append(str(len(branch))+' '+' '.join(str(v)for point in branch for v in point))
            p.write_text('\n'.join(lines)+'\n')
            return inspect(p,nets,24,24,{n:-1 for n in nets},parents)

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

    def test_interface_attribution_counts_every_incidence(self):
        r=self.check_paths({'h':[(5,8),(9,8)],'v':[(7,6),(7,10)]},
            {'h':[[(x,8,0)for x in range(5,10)]],'v':[[(7,y,0)for y in range(6,11)]]},
            {'h':['M','S'],'v':['V','S']})
        self.assertEqual(r['conflict_incidence_by_cluster_set'],{'M|S':1,'V|S':1})
        self.assertEqual(sum(r['conflict_incidence_by_cluster_set'].values()),r['conflict_nodes']+r['excess_occupancy'])

    def test_disconnected_fragments_rejected(self):
        with self.assertRaises(AssertionError):self.check_paths({'h':[(5,8),(9,8)]},{'h':[[(5,8,0)],[(9,8,0)]]})

    def test_odd_via_rejected(self):
        with self.assertRaises(AssertionError):self.check_paths({'h':[(5,6),(5,7)]},{'h':[[(5,6,0),(5,6,1),(5,7,1),(5,7,0)]]})


class InputHeaderTest(unittest.TestCase):
    def read(self,suffix):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'input.txt';p.write_text('24 24 1 162 1 4 0 1 1 1 0 0'+suffix+'\nnet_a 2 5 6 7 8 -1\n')
            return inputs(p)
    def test_all_supported_headers_preserve_every_terminal(self):
        for suffix in ['', ' 2', ' 2 1', ' 2 1 1', ' 2 0 0 8', ' 2 0 1 32', ' 2 1 1 2', ' 2 0 0 8 0', ' 2 0 1 8 1']:
            h,nets,limits=self.read(suffix)
            self.assertEqual(nets,{'net_a':[(5,6),(7,8)]});self.assertEqual(limits,{'net_a':-1})
            self.assertEqual(len(h),12+len(suffix.split()))
    def test_malformed_options_rejected(self):
        for suffix in [' 4',' 2 2',' 2 1 2',' 2 1 1 0',' 2 0 0 3',' 2 0 0 33',' 2 0 0 8 2',' 2 0 0 8 1 0']:
            with self.assertRaises(AssertionError):self.read(suffix)

    def test_direction_cost_is_independent_of_bidirectional_and_adaptive(self):
        # tree_router.cpp validates each of these header fields independently.
        # The actual19700 header has bidirectional=1, adaptive=0, cost=8.
        for bidirectional in (0,1):
            for adaptive in (0,1):
                for cost in (2,8,32):
                    for finite in (0,1):
                        h,nets,limits=self.read(f' 1 {bidirectional} {adaptive} {cost} {finite}')
                        self.assertEqual(h[12:],[1,bidirectional,adaptive,cost,finite])
                        self.assertEqual(nets,{'net_a':[(5,6),(7,8)]})
                        self.assertEqual(limits,{'net_a':-1})

if __name__=='__main__':unittest.main()
