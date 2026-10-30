# R404实际物理配置读回

Refs #121 / PR #122。2026-10-30 01:30:48 CST捕获，93555/node21实际RUNNING。6原始文件SHA/长度核验；新源d1aadb3e/归档f9b9db75的308源Git/远端实际SHA绑定见../r-native-404-start/index.json。

实际die2330×2330um、映射目标0.28、PLACE_DENSITY0.35，CTS_ARGS包含apply_ndr none，GLOBAL_ROUTE_ARGS包含100拥塞迭代，原生M1–M10保持。input.v实际大小/SHA与旧344完全一致，RTL SHA4032c5ed…保持；inherited_physical_stages为空，全部物理阶段重新执行。

捕获时只记录synth完成、floorplan仍在运行，不能把配置生效或早期估计时序当作300MHz最终通过。完整P&R、405独立验收/六文件/完整几何、406全端口接口仍待实际结果。
