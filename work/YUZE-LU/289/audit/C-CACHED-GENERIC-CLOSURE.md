# C cached actual generic synthesis proof closure

Issue289, supplement to C-PARENT-FUNCTIONAL-PROOF-CHAIN.md. Job119960 completed with EQY DONE PASS: all523 partitions proved. This supersedes the earlier document's pending generic-stage supplement and the479/505 partial result; historical timeout logs remain unchanged.

The reference starts at the actual C-v16 canonical RTLIL and uses standard Yosys `synth -flatten -noabc -extra-map common/lcu_kogge_stone.v`. The implementation is the before-DFF graph captured by the byte-isolated actual synthesis replay. Every top-level and hardmacro pin is retained. Proof matchpoints include only actual FF Q or inversion-alias live bits, explicitly mapped across both graphs. No reset, onehot, or data assumptions were added. Reference frontend and standard normalization remain trusted; hardmacro internals retain separate qualification.

`C-cached-generic-equivalence-receipt.json` binds every partition and actual input SHA. Cached source remains `a0f71497ee0c873649c41d64122e2a906775caaed90dc615a686be053625d0f9`; actual parent synthesized netlist remains `0d42fdd36b5c0ca3f9fc7682a34465dc6ef60732363be81b7eb465a87d7aa0c4`. The previously proved local FF semantics, full ABC CEC, byte-exact replay and synth-to-v18-CTS segments continue from this same graph.

The primary implementation remains cached C. Shared-A is a separately proved fallback and must not replace the primary golden netlist in a final receipt. Final postroute state/data/control equivalence and actual physical acceptance remain pending; this is two-state functional evidence, not a four-state X-propagation or backend signoff claim.
