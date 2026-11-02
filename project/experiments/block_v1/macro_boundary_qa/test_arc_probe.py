"""Fail-closed source patch scope; native builds/EDA are separate evidence."""
import unittest
# Use the suite's existing canonical audit module before importing patchers.
import test_audit
from audit import Invalid
from build_arc_probe import patches


MODEL='''#include "Path.hh"
namespace sta {
min_max_(MinMax::max()),
const MinMax *min_max = MinMax::max();
Arrival data_delay = src_path->arrival();
          Arrival delay = path->arrival();
          OutputDelays &delays = output_pin_delays[output_pin];
          Arrival delay = path->arrival();
          RiseFallMinMax &delays = clk_delays[clk_edge];
}
'''
GRAPH='''namespace sta {
    const ArcDelay load_delay = delayDiff(gate_delay, intrinsic_delay, this);
    annotateLoadDelays(drvr_vertex, drvr_rf, gate_result, load_pin_index_map,
                       load_delay, false, scene, min_max);
}
'''


class NativeComponentPatch(unittest.TestCase):
    def test_native_wire_annotation_and_clock_output_are_preserved(self):
        model,graph=patches(MODEL,GRAPH,'min')
        self.assertIn('annotateLoadDelays(drvr_vertex, drvr_rf, gate_result, load_pin_index_map,\n                       load_delay, false, scene, min_max);',graph)
        self.assertIn('Arrival delay = path->arrival();\n          RiseFallMinMax &delays = clk_delays[clk_edge];',model)
        self.assertIn('qaNativeInputDriveDelay(boundary_start, sta_)',model)
        self.assertNotIn('boundary_start->arrival()',model)

    def test_missing_or_duplicate_native_component_capture_is_rejected(self):
        marker='const ArcDelay load_delay = delayDiff(gate_delay, intrinsic_delay, this);'
        for graph in [GRAPH.replace(marker,''),GRAPH.replace(marker,marker*2)]:
            with self.assertRaisesRegex(Invalid,'native drive component target'):
                patches(MODEL,graph,'max')

    def test_duplicate_native_namespace_is_rejected(self):
        with self.assertRaisesRegex(Invalid,'namespace target'):
            patches(MODEL,GRAPH+'\nnamespace sta {','min')


if __name__=='__main__':unittest.main()
