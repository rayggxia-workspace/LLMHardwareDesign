import unittest
from placement import Graph,beats,candidate


class Placement(unittest.TestCase):
    def test_physical_tail_accounting(self):
        self.assertEqual([beats(n) for n in (0,1,63,64,65)],[0,1,1,1,2])
        self.assertEqual(beats(2,63),2)
    def test_independent_scheduler_resource_oracle(self):
        for mode,expected in (("1RW",12),("1R1W",10),("2RW",10)):
            g=Graph(mode);g.memory(0,False,640,());g.memory(0,True,128,())
            self.assertEqual(g.schedule()[0],expected if mode!="2RW" else 6)
    def test_constraints_and_resource_equality(self):
        near=candidate("near","internal",1,"1RW",4,2,32,1024,"static")
        shared=candidate("shared","internal",1,"1RW",4,2,32,1024,"static")
        self.assertTrue(near["feasible"] and shared["feasible"])
        self.assertEqual(near["resource_busy"]["rq"],shared["resource_busy"]["rq"])
        self.assertEqual(near["resource_busy"]["matrix"],shared["resource_busy"]["matrix"])
        self.assertEqual(near["resource_busy"]["vector"],shared["resource_busy"]["vector"])
        self.assertEqual(near["rq_parameter_bytes"],shared["rq_parameter_bytes"])
        self.assertEqual(near["state_working_bytes"],4096)
        self.assertLess(near["link_beats"],shared["link_beats"])
    def test_no_free_state_reuse_when_tiling(self):
        a=candidate("near","internal",1,"1R1W",1,1,32,1024,"static")
        b=candidate("near","internal",1,"1R1W",8,1,32,1024,"static")
        self.assertEqual(a["resource_busy"]["vector"],b["resource_busy"]["vector"])
    def test_capacity_buffer_reachability_and_parameters(self):
        for args,why in [(("near","internal",1,"1RW",4,2,32,16384,"static"),"per-bank capacity"),
                         (("near","internal",1,"1RW",16,2,32,1024,"static"),"finite boundary buffer"),
                         (("near","cross",1,"1RW",4,2,32,1024,"static","forward_only"),"static connection unreachable")]:
            self.assertIn(why,candidate(*args)["rejected"])
        a=candidate("near","internal",1,"1RW",4,2,32,1024,"static")
        b=candidate("near","internal",1,"1RW",4,2,32,1024,"dynamic_row")
        self.assertEqual(a["rq_parameter_bytes"],16*5)
        self.assertEqual(b["rq_parameter_bytes"],32*16*5)
        self.assertIn("private state working capacity",candidate("near","internal",1,"1RW",4,2,32,16384,"static")["rejected"])


if __name__=="__main__":unittest.main(verbosity=2)
