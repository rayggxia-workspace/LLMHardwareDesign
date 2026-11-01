# Actual seven finite repair results

Refs #121; PR #122.

94503 naturally FAILED1:0 in07:40 on node13. Cases1-6 PASS, each removes its target marker with zero added. Case0 removes three originals but adds one net113322 Metal Spacing marker and is rejected as a whole; actual per-net filter excludes that modified net. All49 raw bytes/SHA and14 actual server large SHA/size, original inputs and stable outputs verified; failed terminal traceback append preserved. Actual case6 start was before the latest of cases0-5 finished, proving dynamic refill.

Plan918 selects four actual useful per-net edits and one explicitly UNTESTED ring union for net113322, derived from the actual source and added notch halves. No failed half-fill qualifies as passed. A real combined native/entire-DEF check is still required; fresh full final gates/interfaces remain mandatory.
