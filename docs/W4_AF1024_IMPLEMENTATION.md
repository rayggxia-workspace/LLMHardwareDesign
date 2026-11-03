# L4-AF1024：完整A至双行F的固定纵向组合

Issue151 / PR152，Melodydt；2026-11-03 Asia/Shanghai。输入ddc6b42dc3cc134e5184ef251df5fa9e6f7b8c10，实跑源码 **b3e14e27e1c38afc697d383e33f5d8d90be62267**。r03通过（r01/r02失败保留） / **95849 / zenanyan-af1024 / node1 / c64 / 8CPU / COMPLETED 0:0 / 00:26:07**，34预声明CASE及12份实际流长度/SHA通过。接收范围是H1024/Sq2完整整数A输出真实进入H1024/I3072 F两次调用，不是trained模型质量或L5一般网络。

## 1. 改动、动机与资源

新增[父顶层](../project/rtl/block_connection_w4/block_w4_af1024_top.sv)及[独立TB](../project/tb/block_connection_w4/block_w4_af1024_tb.sv)，原样实例一个[AFULL](W4_AFULL_IMPLEMENTATION.md)和一个[baseline F1024](W4_F1024_IMPLEMENTATION.md)，旧52份RTL/TB/include及source-lock全部不改。A产生Y0/Y1，F逐行计算post-A RMS→gate/up→SwiGLU→down→以Y为原残差得到Z；不能将F残差误用成A原X。

总原生宏为M2/N2/E2/G1/S2/T2/R0，共11叶实例；两个局控及新父FSM/路由/metadata另计。这是两个子块固定协调，不是单资源大岛或第三种新功能岛。父新增gamma_bank128×128bit=2048B，供两行独立F gamma回放，没有4096B Y数组；Y保存在真实A_T，F既有输入holding及S/T成本仍计入各子核。gamma FF不靠reset清数据，只有完整新帧写完才有效。

## 2. 任务、帧和两个参数端点

父接单独立捕获generation32、A/F version16并负有终态义务。父输入576字/9216B，index10、generation、last仅575：0..447送A原448字，重建child last447；448..575写父128字F gamma。只有父全部接受且A真实input_stored后才允许父start。父gamma接受是实际FF写入，不伪造S ACK；随后两次F帧都需再真实写F S。

A/F两个权重口保留不同原生ABI。A generation32/seq16/index4，K/V/Q/Wo head/group/chunk，共6MiB；F job16/seq16/index5、matrix/group/chunk，每行9MiB实际重放、两行18MiB，外加只读row关联。A接受错/旧tag严格失败；F按既有合同可drain较旧job/seq。不能把父generation等同Fjob或假装两端已统一成一般MEM协议。F version0在父接受job后形成held errorDONE，不发A job或数据。

F finite ID mirror只按真实F start递增，随coherent child_reset清；正常父任务结束不清。父在job握手时检查至少两次F启动容量；mirror>FFFD则接单后保持错误终态且不发A job，避免row0用完最后ID导致row1无限等待。每次start另有保护。reset会重建F ID域，provider须停止/清在途旧流，不承诺跨独立warm reset或无界晚返回隔离。

## 3. Y捕获、目的写ACK与源T退休

| 顺序 | 实际动作 |
|---|---|
| A计算 | 完整H1024/Sq2/KV8/Q16/D128/context/Wo/原X残差，Y两行全部提交到A_T |
| F捕获一个Y字 | 父只发一次f_in_valid，F既有holding接受；父f_y_pending置1，A_T此时不take |
| 等目的S ACK | F公开in_ready在该非末帧输入的S写ACK后才重开；pending且ready重新成立、无失帧/metadata错误才让A_T take |
| 行末gamma | 每行128个Y都已真实S写ACK并源退休，再回放父128gamma字；F最后gamma写ACK建立stored后才start |
| F0执行与输出 | A_T停在index128，整个F0计算/host输出/实际T RELEASE/DONE消费期间保活第二行 |
| F1执行 | F0闭合才取Y1；最后Y先目的ACK再A take，A实际RELEASE/DONE可独立被父收取；F1继续完成 |
| 父正常DONE | A及两次F终态均正常消费、全部真实子T释放、host256字后才成功 |

这个ACK观察依赖原baseline F的公开入口合同：Y位于F帧0..127而非末字255，捕获后ready降低，S响应退休后恢复；失帧fatal门阻止将错误清帧后的ready误当成功ACK。只加1bit控制信用，不读子私有S端口作控制，不增加Y holding。TB使用真实S ACK独立核验，不能把该定向技巧当任意网络的STORED_ACK协议。完整端口与phase见[合同](rtl-contracts/AF1024_PORTS_AND_LIFETIME.md)。

## 4. 错误、取消、完成与复用

父input及A/F output元数据先检查后转发，坏A字不进入F、坏F字不发布host。F装帧出错会清frame且没有子DONE，父从已捕获frame的busy/stored丢失形成自身错误终态，不能永远等子start/DONE。父接单后部分输入、prestart、装帧/等ACK/计算/输出取消都有held DONE；未接单abort不造DONE，hardreset直接取消不补终态。

父sat只观察当前已启动并拥有的子任务，F两次调用间不采旧flag；error/partial/words按实际最终host前缀记录，已写S或输出不回滚。错误协调reset两个子树并作废在途；正常DONE后无需reset复用。父成功绝不只看last、ready或某个子DONE，不能用host take替代一般远端stored ACK。

## 5. 数值、独立参考与非退化探针

采用同S16 Fin10、S8 Fin7、epsilon_code1，Y逐bit进入F的原输入/Norm/残差，没有S8窄化或Fin12转换。F gamma为独立synthetic per-channel raw16+(5c)%17，和A gamma1024..1088不同；F权重采用明确seed17，非训练checkpoint。Fin12/W9候选不可裸接此baseline。

独立AFULL数学构造真实Y，再独立F参考计算两行全部Norm/gate/up/mid/down/Z。F全部43008个raw dot按完整K直接另算，K1024 gate/up与K3072 down均不逐chunk量化；9MiB的589824个权重拍及9437184编码核布局。A原完整30720投影/Wo数学自检同时重跑，G2564数学节点与冻结表逐项相等。实际新组合TB对A核读写ACK/版本/计数及最终Y数值；A内部逐stage数学资格沿同字节AFULL原回执，不声称本轮重新逐项核完全部A内部数学。F各关键stage实际写值逐项核对。

base两行mid非零2999/3036项，down各1024元素非零，最终Z各1024元素都不同于Y且无clip；排除了gamma0或纯残差旁路。错用A gamma使2048个Z改变，错F权重2044、交换Y行2046、重复Y0为Y1改变1023、丢Y0改变1024。future_changed只改X1，最终Z0 bit不变；boundary饱和按实际数学计算/冻结文件接收，不硬编码测试名。

## 6. 实际服务器验证与计数

r01/95839（源码2263b2e02c01095b7310ea153e29156f6bbe8f95）自然FAILED1:0/12:51，前三正常fixture及前18CASE已过，第19项坏F参数触发合法errorDONE/reset后，TB仍以旧计数要求已取消的A_T保活而误报。r02/95845（源79cd731f63398d26c09ee334b39a47e5ac5775ca）仅排held errorDONE并加子核关闭检查，仍在DONE已消费但tracking尚清理的两拍窗口误触发同一断言，前18CASE后FAILED。r03将保活条件进一步限定在真实obligation仍有效期间，保留正常/背压及提前成功DONE检查，并将原真实坏F参数用例前移第7项，34项无删、无fake A/Y；RTL/golden未改，完整重跑。所有失败源、输入和日志保留，不把任一失败改写为通过。

34预声明CASE严格顺序通过，覆盖版本0/两ID准入、输入最后ACK、真实A/F元数据、每Y capture→S ACK→A retire、首/末Y ACK背压、A_T跨F0保活、独立gamma/参数版本、F末gammaACK、父子DONE背压、native/helper错误、A strict/F stale策略、取消/reset/前缀/正常恢复。定向故障需要真实执行A，不用假Y绕过计算。

| 每正常完整父任务 | 已通过TB断言 |
|---|---:|
| A普通S请求/ACK | 各806408 |
| 两行F普通S请求/ACK | 各1776152 |
| 总S请求/ACK | 各2582560=2078592W+503968R |
| M命令 | A30336+F80896=111232 |
| N / E / G | 2856原生命令 /1280服务 /768服务3072pair |
| A / F权重 | 6MiB /18MiB，合24MiB实际传输 |
| Y捕获/真实ACK/源退休 | 各256字，至多1个pending信用 |
| gamma | 父128字捕获、两F帧256字回放写ACK |
| T | take768，RELEASE4（A两lease、F两次各1lease） |
| 最终host / 父DONE | 256字4096B /一次保持终态 |

混合全局原文：`cycles=157772686 jobs=37 input=16710 AS=14532003/14532003 FS=10662751/10662750 AM=546065/546065 FM=485454/485454 Aweights=7077908 Fweights=7078914 Atake=7296 Ftake=1153 Arelease=23 Frelease=9 Ycapture=2689 Yretire=2688 gamma=2561 host=1153 done=34`。含准入拒绝、故障、取消、hardreset及前缀；CASE数不等于正常任务数，不能用聚合统计替代正常帧守恒或作为系统吞吐/PPA结论。

三fixture每组actual input9216B、Aweight6291456B、Fweight18874368B、Z4096B，12份真实握手流按原序导出，长度/SHA与独立golden/固定合同一致。r03的26运行输入Git blob及服务器SHA、123生成文件前后固定SHA；三次运行共78份输入出现次数逐SHA重核，42轻量文本和归档SHA `1d5526218ee8141adaaf94f83fe54d30655e300346da05a5d2681e627530c185` 全核对。原始binary/vector/weights/build仅本人服务器。[实跑回执](../work/Melodydt/151/af1024/evidence/runs/r03/results/run-receipt.json)、[证据索引](../work/Melodydt/151/af1024/evidence/evidence-manifest.json)、[交付检查](../work/Melodydt/151/af1024/final-checks.json)。

Verilator5.042/g++11.4.0/Python3.10.12，容器与argv见回执。--assert启用，-j8构建/单线程仿真，仅-Wno-fatal；保留42warnings（16TIMESCALEMOD、10WIDTHEXPAND、16WIDTHTRUNC），非lintclean。旧52源回归、完整模型推理/质量、官方框架/代表性评估和EDA未执行。此轮接收固定synthetic整数纵向组合，不放宽旧24GAP。

## 7. PDF覆盖、交付与后续门

按用户新增要求，每完成本研究一步都更新现有交流PDF并同名覆盖，不创建版本、不推Git、不发送他人。本轮已覆盖原路径 `work/Melodydt/151/local-share-2026-11-02-v2/output/pdf/七宏功能岛方案交流_2026-11-02_更新版.pdf`，10页，SHA `c1d3ec12dd05fbff0a82373efab03f7961144be502d57216b6bdd268eadd801d`，全部渲染/文本/链接及视觉QA通过；[本地PDF索引](../work/Melodydt/151/af1024/local-PDF-index.json)。文件名中的旧日期保留，正文日期与当前结果更新，未来接续须继续同路径覆盖。

服务器yuzelu@10.129.166.172；任务/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af1024-ddc6b42-20261103，input-r03/runs/r03，日志slurm/zenanyan-af1024-95849.out/.err及runs/r03/logs；真实submit已留证，复跑使用新input/output/job不覆盖r03。无本任务在跑作业、无自动监测。工作af1024-ddc6b42/integrated是隔离API包无.git/HEAD/index/暂存，不改main/旧包/ref-project；仅用户授权的现有本地PDF被覆盖。

当前仍L4。下一 **L4-QUALITY**：固定当前baseline误差/clip与代表性cal/eval门，做官方框架对照/W8复核、完整A/F组合数值与其它样本变体准入；合成整数功能不转为trained质量。L5母控/一般跨岛stored ACK、D/H/X、MEM/永久程序/M11-M12物理分别接收。PR152待审查未合并，Issue交付回in_review而非done；登记PR5 pending，看板unverified/同步pending，处理人待指定。
