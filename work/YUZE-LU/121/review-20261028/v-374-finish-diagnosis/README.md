# V374 最终原生流程与时序诊断

Refs #121 / PR #122。2026-10-29 21:13:54 CST 捕获。源 f318db6eb6dc263e551004a1c32ed321525e9256 / 归档 16ee54c470c8929b6d89fb484b64db12f4f83b38765d86a0cfb0c63c502050a1；14原始文件SHA/字节、最终receipt输入与原归档、同一input.v及既有308源/Git/远端绑定已核验。

六原生阶段全部完成，最终RCX setup −0.12 ns、TNS −37.33 ns，精确关键slack −0.1232 ns；最大product[3][4] → stat_block_sq[66]。hold报告约+0.01 ns，最小group_unit.quotient[15] → group_unit.numerator[15]，尚无独立最终STA资格。

流程内最终LEC UNSAT/IDENTICAL，公共输入51206、公共输出51195；原生详细路由日志最终违规数0。它们不替代独立严格LEC、完整未修改GDS DRC或最终功能。native执行passed与qualified_hard_macro=false分别保留，不能以流程完成宣称300 MHz通过。

下一个选定修正仅调整同一基础V的U80平方和树进位结构，不增周期/资源合同、不缩位或改舍入。新源仍须新功能/算术/映射/测量和全部物理/最终门；本目录不向新源转移最终资格。已启动旧后继正常收尾，R344不取消。
