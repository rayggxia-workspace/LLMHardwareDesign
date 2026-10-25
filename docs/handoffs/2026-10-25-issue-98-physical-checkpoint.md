# Issue98 阶段交付与继续执行入口

- 仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue98；负责人Liangruizhi，实际认证ID182389313，邮箱2663955430@qq.com；分支task/98-integrated-physical。
- 独立worktree D:/Projects/LLMHardwareDesign-integrated-physical；临时D:/Projects/Codex/integrated-physical-20261025-01；服务器/public/home/yuzelu/RuizhiLiang/issue98-integrated-physical-20261025；仅lrz-i98-*。根会话统一push/PR，不自合并。
- 首次可发布checkpoint fdd643640426eba10efecf066cee11bc15e553f9；后续独立接收代码继续提交，当前分支head以git核实；本记录不是整项完成交接。发布前重新git status/identity/origin/Issue/PR/看板。

已证实93原映射完整51记录×两条件门级通过，67接受命令/路，原始收据SHA78e43e09196115d943f92ec746e70e104751e2ae55fd6ed6154e767a506ae613。唯一gate driver例外为末次epoch直接Q注入改正常命令，未证明terminal gate注入。精确93 postphysical长跑继续，不能继承raw结论。97已接收的每精确gate均4×2正常输出，RTL50command内部注入另列。

93历史真实DRT DRC0/routed1/天线0、全DEF层账和实际RCX/独立SPEF读回已成立，但严格全cap20超限；97历史GRT同为20。精确OpenSTA native过滤<1fF负cap裕量，因此旧native0不能升级严格电气通过。0.80批量后93仍4cap/6hold、97cap0/68hold；保持时间主要因buffer卸载数据变快。唯一50ps/4096 incremental hold候选实际完成91355/56，接收/新gate/97详细route继续。不得重复已运行作业、不自动追加阈值/无限修复。

恢复第一步：读取最新Issue98评论/本报告及本人sacct；查每目录manifest/receipt后再决定重跑。原目录不可覆盖。新结果最终accepted必须有完整stage SHA、graph/所有FF、pin/面积、全部setup/hold、严格maxcap/slew、实际全RC和精确postgate。fanout库/SDC未限定；固定输入slew不等于真实upstream driver。

源码各phase binding/source.zip，实际argv/log/input/config/library/source/result SHA全部留server；精选checkpoint1的7原收据已PC独立字节核过，更多归档与原Git全源接收仍pending。管理结构check_project、source AST通过；已实际执行的业务/负例结果以报告和receipt为准。所有失败/中间未闭合阶段留存。

交付状态：本地代码/报告已提交，根会话发布PR待读回；本记录不宣称远端代码已上传。Issue当前in_progress，审查人待指定；未合并/审查不done。注册沿此前registry PR5 pending；当前worktree无config/board.json，配置看板/权限最终由根会话读回，不能把Issue评论当Projects同步。管理员/审查人待指定。

原则性制造缺项：真实工艺/PVT/SRAM Lib/LEF/宏时序与物理阻挡、PG/tap/fill/LVS及真实上游driver；现Nangate研究logic island不manufacturable。M2–M10信号/边界M5–M6与成员55/63的M1–M8固定、M9–M10可定制且引出M8不同，不移植资格或接管成员任务。


## checkpoint3恢复更新

97已闭合的是detail9702（91422）及独立detail-receive9702（91426），精确gate为jointpost97-receive01（91421），读取checkpoint3原收据及SHA，不重跑。所有历史native/strict失败保留，不能用当前PASS覆盖旧失败。93 joint9302最终DRT detail9303已全检查通过，尚等91391/91392→91393完成完整51×2gate；必须将该精确gate送入新receive_detail输出目录后才允许accepted。旧CTS/cap gate虽已完成，不适用于此最终网表。

已准备package_results.py/verify_bundle.py，最终归档必须等声明范围活跃输出静止，包含原失败/所有源码/实际binary，排除可再生obj中间文件并明列；独立byte receiver逐成员验证，不解压执行。74phase来源已通过原Git批量核验。源码phase74=7ead034候选6/接收修复，phase75=9cede8c归档与只读预算/摘要工具。候选6入口negative-entry01真实通过。

当前唯一耗时项93final gate保留原10500s/10800s边界。根已批准仅当真实超时且没有数值失败时，对同精确源/binary/51driver/input预登记一次16000s child/280min新out；不得更改原job或缩短记录。所有普通改动和提交仍由本worker完成，root负责精确snapshot发布PR，不写活动目录；未审查合并不done。

## checkpoint4 接续

持续草稿 https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/111 已发布8449e0e，root保存远端字节回执。97新slew全集接收detail-receive9703/receipt SHA4691173d1376bba0af92be2b4de6ac4abcfc644848b85163e3a8963c74220ec8；没有改变原物理结论。两核四个双load重SHA负例拒绝。97冻结部分delivery97-01在服务器和D盘均有5451成员独立SHA通过，压缩SHA4a1f9e3449abceeaafb7e3e176b3de010bf3ccc5c10aac510c00456db1dc05f1；非整个Issue最终包。

恢复先查91391/91392与条件保护91579/91580（原91553/91554未运行即取消），读final93-budget-s0/s1/guard.json。仅ORIGINAL_FINISHED或SOLE_EXACT_RETRY_EXECUTED可送完整接收，ERROR/RUNNING/prefix不可升级。唯一新out jointpost93s002/s102；receive_guarded93.py选择后仍调用原51×2独立接收，新receive_detail绑定精确gate，无第二次预算延长。失败与未执行依赖保留。

累计默认diff检查因原冻结CRLF失败，工作区检查及显式core.whitespace=cr-at-eol累计检查通过，不能混淆；不改写冻结源/JSON。Issue in_progress，登记PR5 pending，缺看板配置/权限交root读回，未done。
