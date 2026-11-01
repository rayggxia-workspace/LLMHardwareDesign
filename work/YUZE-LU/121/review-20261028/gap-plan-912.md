# Finite five-marker repair queue

Refs #121; PR #122.

2026-11-01 12:37 CST：903/94502自然COMPLETED0:0（13:28）；906完整5标记邻域PASS，548显式RECT、全NET/all-layer/PG/pin/OBS完整且原源保持，12原始/无大文件。新5源b622d31e与907当前拓扑绑定。912派生9个唯一局部方案覆盖五网，打包7真实任务（3/1/1/1/1/1/1），准备6×16动态补位；尚未提交/通过，R未接收、所有fresh最终门/接口仍待。


908 is the unsubmitted initial scalar-cut prefilter (three nets only).910 adds finite existing-tech adjacent enclosure alternatives and Euclidean cut-bbox candidate pruning (five nets).912 packs the same nine unique910 edits into seven independent jobs: one group of three singleton nets and six separate endpoint parameters. These are experiments, not additional macro variants. Scalar metal/OBS and Euclidean cut distances are only candidate pruning; no DRC rule/deck is changed or waived. Same cut and target enclosure are preserved for alternative existing tech vias, original adjacent pad/wires/RECTs retained. Native full-chip/complete DEF checks and fresh fullsignal/all final gates mandatory.
