# #166：718 最终时序及全芯片原生零违规通过，完整 GDS / 192 项功能仍在验收

本记录接续 CHECKPOINT25；当前不构成 R1024 整宏验收。R256111/252 的原资格和 816 文件完整实收保持不变。Issue166 保持 in_progress，PR167 保持 draft，不合并、不修改 main 或其他任务。

718/96335 最终生产 COMPLETED 0:0：原 300MHz / I/O 条件下，最终 RCX setup +67.4889ps、hold +0.210554ps，setup/hold/cap/slew 计数均 0、DRT 0；严格最终 Naja LEC 为 UNSAT/IDENTICAL，VDD/VSS 连通及完整 5041 条时钟网/97499 单元审计通过。最终 ODB SHA256 为 1d848b36183b6fb15fb1cce7b7fe6116119a889030720685133344d039ec2b44；最终 Verilog SHA256 为 c7c59ae0560563f317650e729e88bf173b89ca3b5c5c2b7c17508971c8b98ab8。原 697 的两个真实 Short 已由 704 正式门再次拒绝，失败原件保留。

730/96366 在 718 完整生产成功后实际启动，以同一最终 ODB 完成全部原生全芯片规则检查：0 项违规，complete.rpt 为空。原正控、Short/Spacing/Notch/fixed 负控、固定上游检查器源码/二进制身份、完整 LEF/DEF 几何与连接交换均验证。原生回执 SHA256 为 6c4320805170756138ee2b2745a6143ed86db18cb6e25f4dab590873328b7d79。1 核运行耗时 7:45、TotalCPU 7:08.641、峰值 RSS 21298780K；它是原检查计算的线程配置变更，未修改检查器、规则或任何标记。native_complete 默认仍为 16 线程，增加显式 --threads 1 仅在真实分配允许时使用，各控制和交换流程均使用同一所选线程数。

731 的包装脚本在调用接收器前发生 Python 字符串换行语法错误，日志保留，不能记作原接收器通过。修正仅限包装后，732/96373 调用字节未改的 receive_native / native_interchange 接收器，独立核验原最终源、生产成功、全部工具/源/规则/几何/负控，实际输出 UNMODIFIED_NATIVE_GATE_RECEIVER_PASS，NATIVE_GATE_RECEIPT.json 的 passed 和 native_gate_received 均为 true、qualification 仍为 false。730 原 EARLY 字段与通用 scope 文本不改写，实际计算开始时间晚于 718 成功结束，按真实 sacct 时间解释。

最终链现为：719/96336 保留原完整未修改 GDS、独立 STA/RC/PG/LEC；720 几何已成功；721 仅在精确最终 Verilog/编译器/Liberty/C++/二进制全哈希一致且最终生产门通过后复用成功 672 构建产物，722/96340 全部 192 项重新执行，723 汇总；733/96375 运行字节未改的 complete_evaluation 并接收 730；734/96376 运行原 qualify_package。733 使用 afterany719 只为读取完成回执，程序仍要求全部其他原门成功、原完整 GDS 为 0 且无 error，不能修复任何 GDS/时序/电气失败。720 已成功的过期调度依赖不再提交，但原资格程序中的几何核验保持。仅逐项核实自身 PENDING 后取消重复 724、被替代 725/726 和可选正裕量诊断 727；所有运行作业和其他任务均保留。

节点候选总数仍为 8：node1、13、14、15、17、18、22、23。依据两次完整原生检查实测接近串行，将一个未使用 c96 候选换为 c64 node1，原生/接收/汇合使用 1 核；重测试保持每项 16 核、数组 %36 动态补位，96 核节点最多 6 项、64 核节点最多 4 项。node1 有真实空闲核后，仅调整已核实自身 PENDING 的 722 分区/排除表，使它也可使用 node1，脚本和功能输入不变；三项协议测试已在 node1 通过，后续三项数值用例运行。其余等待是实际 Resources/Priority 与依赖，不是内存不足或人为批次等待。候选池不冒充当前实际独占 6–8 个节点。

默认 project/rtl/r_local_state 已恢复为实际冻结和映射/证明/物理链使用的 c7c247 精确 LF 字节；可选 FINALIZE_PIPELINE 实验原字节保存于 experimental_finalize，并由显式参数选择，不能继承默认物理资格。只是源码入口与实际已运行源对齐，不修改既有冻结归档/作业或交付物。source718-oldrtl-runners.tar SHA256 为 a2a96c8e2a1c3ba39d7161bcca610b2416b4c6f916c7548effb49beceae8e4f7；串行运行控制归档 source729-oldrtl-runners.tar 为 bcbe9038babb7fd7416df1811beeb0f613015e372e5a5e10853ecd17aa44c972。两者均精确 c7 RTL。原完整证明047/映射014继续绑定；旧未结束 SAT 不因耗时取消。

evidence/native-zero26 逐 SHA 实收 111 份原文件、509356 字节，仅小证据，不称整宏实收。远端 600 份实际自身提交索引已更新；ATTEMPT_JOBS.json SHA256 为 f7745295f726e432aa79c919ee6bac2d299f5c6f126ffb48331f06bd170050cf，ATTEMPT_SCHEDULER_INDEX.json 为 945b9400b3c19bee59292d991d8c5b132fac7ab63b99aa8d897af2f4d88d7242，PROGRESS734.json 为 9ef772d9fc0ccc563c6ff8eb116cb572f9c0d3c8c0a347a533c697356efd0c7e（观察快照，不是实时状态）。大 ODB/DEF/版图仍在授权存储按 SHA 绑定。

后续仍须原完整 GDS、独立全部物理门、精确最终 192 项数值/协议全部成功，再生成六文件/实际 PNG/LEF/Lib/源索引完整包并本地逐文件 SHA 接收及实际 PNG 审阅。所有原 300MHz/IO/零违规门不放宽；R1024 未完成前不宣布整体验收。

协作回执：rayggxia-project-collab 1.0.0；负责人 YUZE-LU；[Issue166](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/166)、[PR167](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/167)，登记 management-hub PR5 pending；缺 board.json，看板 unverified / 同步 pending，管理员及审查人待指定。项目结构检查与实际业务门分别记录，结构 CI 不代表物理通过。
