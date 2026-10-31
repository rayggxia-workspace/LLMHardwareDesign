# V375 旧版完整DRC与严格LEC

Refs #121 / PR #122。11原始文件SHA/长度、归档输入/稳定输出核验；final-source回执与既有v-375-final-function/source-binding字节一致，严格LEC还绑定同一份三初态最终功能回执。

原生whole-chip DRC空报告、完整未修改FreePDK45 GDS deck 0项，无排除/豁免。独立严格LEC UNSAT/IDENTICAL，公共输入51206、公共输出51195，diff0/diff1均0，所有检查通过。来源仍为f318db6e的旧374最终输出；308源Git blob证明见v-375-final-function/verification.json。

这些补全旧版证据，但374最终setup−0.1232 ns仍失败，delivery/geometry依赖阻塞。不能宣称旧374最终接收，也不能向当前380转移任何最终资格。当前380仍须独立381/382完整验收。
