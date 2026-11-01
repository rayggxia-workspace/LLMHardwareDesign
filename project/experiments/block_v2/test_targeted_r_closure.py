"""Reject unsafe target sets before they can generate an executable Tcl ECO."""
import copy
import json
import unittest

from targeted_r_closure import config_bytes


class ClosureTargets(unittest.TestCase):
    def setUp(self):
        self.data=dict(diagnostic_completed=True,source_bytes_unchanged=True,native_leaf_accepted=False,
            actual_design='outputs/100/pnr/r',actual_spef='outputs/104/diagnostic.spef',
            hold_targets=[dict(endpoint='$auto$ff.cc:337:slice$123',startpoint='reset',hold_slack_ns=-.022,setup_slack_ns=.135)],
            hold_paths=[dict(endpoint='$auto$ff.cc:337:slice$123',startpoint='reset',slack_ns=-.022)],
            resize_targets=[dict(instance='wire'+str(592286-i),master='BUF_X2' if i==1 else 'BUF_X1',min_slack_ns=.8,
                protected=0,signal_only=True,single_fanout=True) for i in range(10)])

    def run_config(self,data):return config_bytes((json.dumps(data)+'\n').encode())

    def test_valid_deterministic(self):
        first=self.run_config(self.data);self.assertEqual(first,self.run_config(copy.deepcopy(self.data)))
        self.assertIn(b'{$auto$ff.cc:337:slice$123}',first)

    def test_rejects_scope_headroom_and_code_injection(self):
        cases=[]
        for field,value in [('endpoint','x};exec touch evil;{'),('startpoint','clk'),('hold_slack_ns',-.031),('hold_slack_ns',.051),('setup_slack_ns',.099),('setup_slack_ns',float('nan'))]:
            d=copy.deepcopy(self.data);d['hold_targets'][0][field]=value;cases.append(d)
        for field,value in [('instance','clock_buf'),('master','INV_X1'),('protected',1),('signal_only',False),('single_fanout',False),('min_slack_ns',.299)]:
            d=copy.deepcopy(self.data);d['resize_targets'][0][field]=value;cases.append(d)
        d=copy.deepcopy(self.data);d['hold_targets']*=2;cases.append(d)
        d=copy.deepcopy(self.data);d['actual_design']='outputs/097/pnr/r';cases.append(d)
        d=copy.deepcopy(self.data);d['hold_paths'][0]['endpoint']='$auto$ff.cc:337:slice$999';cases.append(d)
        for d in cases:
            with self.subTest(data=d),self.assertRaises(AssertionError):self.run_config(d)


if __name__=='__main__':unittest.main()
