# Preserve electrical cost strength during local congestion search

2026-11-03 Asia/Shanghai, Issue #162 / PR #163.

Actual source196 diagnostic: all 32 stronger-cost trial outputs were checked
independently. Neither weight1e9 nor1e10 produced a clear selected trial.
The actual native-ground plus minimum-input-pin bound reports respectively
2 and5 high-RC violations, worst ratios1.08446729496 and1.12761974587.
No route admission. Candidate1960 improves the separate read-only local demand
estimate from2.36207 to1.90959; this does not offset its electrical failure.
Default1580 ->1962 replays all16 trial files and placement exactly.

For the explicitly stronger search modes >=1e9, raise the quadratic necessary
electrical-budget cost coefficient from5000 to the selected local cost weight.
This makes the electrical objective retain priority in the enlarged cost scale.
C++ and the independent direct Python oracle use the same stated coefficient,
but continue to compute geometry and local demand separately. The <=1e8 modes
and default are unchanged. Record the coefficient in placement provenance.

Run two bounded16-trial diagnostics and the original default replay in existing
free own slots, then apply the original actual low/base/high necessary bounds.
Penalty strength is search only; zero violations, complete routing, native and
distributed RC, original geometry/PG and300MHz final gates remain mandatory.
No native mask, RTL, final physical acceptor, parent allocation or R task change.
