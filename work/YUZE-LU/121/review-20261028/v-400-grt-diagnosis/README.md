# V400全局布线阶段证据

Refs #121 / PR #122。93529/node23，源62e3e5776c891a83f8665d0b86a99fb6aa36f188、归档d3ee6032b6124a089b825cacedeb5ce863beaf038cafa8c12a7ccbcf389a17e3。2026-10-30 01:27:52 CST捕获19原始文件，SHA/长度、308归档源Git blobs及远端实际源SHA核验；input.v SHA与最大/最小路径映射见index.json/path-source-mapping.json。

GRT各层拥塞0，总需求5471082/资源9848678=55.55%。setup WNS/TNS报告均为舍入−0.00ns，关键路径显示0.00ns且VIOLATED，不能作为300MHz通过；最大point_op[1]→point_rounded[1][118]。第一最小路径cmd_index[2]→rsp_data[74]，报告+0.01ns。实际M4–M10调整TSV为0.20/native_rules unchanged，命令包含100拥塞迭代，原生规则保持。

随附上游CTS修复LEC为UNSAT/IDENTICAL、51206输入/51195输出、diff0/diff1全0；4983时钟网none读回与原阶段JSON计数/SHA一致。此LEC不是最终网表资格。捕获时已进入详细布线，原93529继续；原ODB不修改，不据阶段时序改RTL或放宽300MHz。最终RCX/独立物理、DRC、功能、严格LEC、六文件/完整几何及401/402接口均待实际结果。
