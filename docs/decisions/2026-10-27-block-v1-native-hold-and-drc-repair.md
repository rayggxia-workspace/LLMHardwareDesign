# Block v1 原生层 hold 与 DRC 修复入口

关联 [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，草稿 [PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。批准计划及其 SHA256 不变，当前仍未取得完整合格物理 Block。

## 现有失败与有限修复

093 的边缘 T6KA 已完成 route/final，但独立 094A STA 的 104356 个端点中有四个 hold 违例，精确最差值 −0.000622502 ns；setup 最差 +5.227097988 ns，cap/slew 计数均为零。原始报告和输入哈希在 `work/YUZE-LU/121/results/run094-t6ka-sta-intermediate/`。该证据为运行中的接收器中间结果，不能替代完整终态。

固定 ORFS 的 `repair_timing_helper` 将 `HOLD_SLACK_MARGIN` 传给 `repair_timing -hold_margin`；global route 阶段按真实 GRT 寄生执行修复，然后详细布线改变寄生。因此增加一次有界分支：从同一 080 封存 CTS 重跑 route/final，保持 `CAP_MARGIN=40`，增加 `HOLD_SLACK_MARGIN=0.005`（ns，即 5 ps）。这是更严格的预制修复目标。SDC、Liberty、时钟、外部负载、面积/修复预算及独立零违例门槛不变；新增 buffer 和所有单元完整计价。不是把验收 slack 容差放宽到 −5 ps。

`native_pipeline_hold5.json` 将候选、独立接收分别指向 105、106。先运行边缘 T6KA；内部候选仍需根据真实 DRC 定位决定修复，避免无依据重跑。后续对照必须使用一致的合格合同和公平成本。106、宏视图、最终网表行为的 worker 入口均支持该严格配置；入口存在不代表任务已经部署、运行或通过。

配置接收要求原配置字节加精确两行目标、实际 make 变量读回、记录和 receipt 哈希一致。Linux 实际上传源码的正例通过；缺 hold、追加限值、错误 hold 读回、错误单位、错误分支、关闭 LEC、过期哈希和跨 pipeline 八个负例被拒，见 `work/YUZE-LU/121/results/native-hold5-config-controls.json`。这仅证明配置约束，不证明修复后的时序或 DRC。

## 先定位实际导体再修复 DRC

094C 保留全部 61 项独立 DRC：三个 M10 间距和 58 个天线违例。技术 LEF 未给出天线规则，库中的 ANTENNA_X1 扩散面积为 0；不能因 router 报零天线而豁免独立检查，也不能编造 diode/gate/diffusion 面积。

新增只读 `native_drc_locate.py/.tcl`：绑定失败接收 receipt、原 lyrdb、源物理 receipt、输入哈希和最终 ODB。对原始 marker 建立带一 DBU 包络的窗口，在实际 native wire/via/PG/BTerm 矩形中保留全部相交候选，导出候选网络及其端口、ITerm、master 和实例包围盒。运行前后重核原 ODB/报告哈希；不修改、修复或导出新数据库。

解析真实 61 个 marker，拒绝新层、未知规则、NaN、奇数坐标和多几何五种坏输入；Tcl 完整性检查通过，见 `work/YUZE-LU/121/results/native-drc-location-controls.json`。实际 OpenROAD 执行另行接收。矩形命中不是多边形所有权或 GDS 电气连通证明，未命中项保留，不把定位脚本 passed 当作 DRC 清零。

后续据实际网络选择预制接入/缓冲/布线修复，并重跑完整原生 DRC/STA/PG/连接/功能。十二层分布式 RC、原生与新增层拼接、完整 C8、宏边界、共同底座和两产品仍须分别完成，不能以本次配置与定位控制缩小总目标。

## 运行与资源

使用现有 `bundle.py` 从已提交 Git 字节封装；新 run 目录与 manifest 不覆盖旧失败证据。103 使用 `native-drc-locate-c`，105 使用 `native-hold5-run-transaction6k-a`；通过统一 dispatcher 计入全 Issue121 的八 allocation 上限，包括 PENDING 和提交不确定状态。其他成员任务不变，不因耗时取消既有作业。

部署后预检发现 104 manifest 使用小写策略后缀，而旧 worker 将其直接传给只接受 A/C 的入口。104 调度状态实际为空、无 Slurm job；保留原部署并停止选择，不能覆写不可变 manifest。worker 已将各 repair 入口策略统一转大写，使用新 105 重新部署；这项预检没有产生物理通过或失败结果。


## 2026-10-27 08:52 CST 实际部署

新增原生DRC只读定位与严格5ps hold修复入口：真实61标记解析/五坏输入、Linux实际源码的配置正例/八负例通过，未替代物理接收。103定位已部署（源码5449132、归档c41fffa3946f15c1ccaa18cd225fe358668285f86f7230204e39fba1e88c7bd5，8CPU/node24）；105边缘T6KA修复与106独立接收已部署（源码a504854、归档d932b5930e7e1e61bfe4108612088be5a6be5d49f811436602c57d4df8372a17，各32CPU/node20和node24），均121成员/849920字节，当前无Slurm job，依统一八槽预算等待。104在预检发现小写策略不兼容后停选，实际未提交，未覆盖原manifest。080 C8C进入最终LEC，中间日志有两个diff1 outputs，严格完整对应门槛保留；094A仍在完整DRC、100双48CPU科学验证仍运行。


## 2026-10-27 09:04 CST 实际定位与精确多边形筛选

100/92147双向joint-node科学验证通过：31:20、MaxRSS7392852K、96CPU内两48CPU；分支与via两方向的细化/外推/远边界/offset/统计/局部电容/互易/保边际错误重连全部通过。103/92154只读原生定位通过：33秒、MaxRSS685692K，扫描220361网/5734869形状、236次命中，61个标记无遗漏。M10三间距项对应read_index[7]/[8]，间距0.13um对0.8um规则；58天线项经原正交多边形精确面积筛选全部单网候选，marker42排除begin_words[5]、保留begin_words[6]，共53个输入网络。105/92157严格5ps边缘T6KA修复在node20/32CPU运行，106独立接收已部署、尚无job。094A完整DRC仍活跃；080 C8C进入RCX，但LEC日志两个未匹配输出边界仍需严格接收。

103记录SHA `0d582637870673975b5a12c2d2864eaf4a3c35f0234411f7a4cffb76dfa4204e`。最初57个天线marker为单包围盒网络、一个为双网络；新增native_drc_geometry.py以整数DBU竖直切片处理凹正交多边形，保留全部原命中及其精确相交面积，排除L形空白区误命中。凹区、正面积、整体面积、边缘接触、离网格、斜边、未绑定locator以及真实marker42八项控制通过。该结果仅收紧导体几何候选，不取代GDS电气连通。

这些输入端候选首级负载为48个CLKBUF_X1与5个BUF_X1；原独立报告agate分别0.0205/0.02625um²，最大ametal28um²、最大ratio1365.85365854。实际core margin20um，不能假定把标准单元直接放到die边缘仍合法。后续须先取得实际GDS输入门/扩散与Liberty负载证据，再确定合法buffer/尺寸/走线修复，全部进入预制库存；不得伪造天线字段、提高300限值或依靠bounding-box推断修复成功。
## 实际库输入门与电气参数探针（续）

`native_cell_pins.tcl` 从实际原生 tech/标准单元 LEF 导出 BUF_X1/2/4/8/16/32、CLKBUF_X1/2/3 和 ANTENNA_X1 的全部非 PG pin 与真实尺寸。`native_cell_gate.rb` 读取同平台实际库 GDS，以与原独立 deck 相同的 poly/contact/metal 连接链从 pin 金属传播，测量 `poly & active` 输入门面积；按原 `(nplus & active) - nwell` 定义列出接触到的扩散候选，不发明 diode factor。用去除 contact 的负例要求输入门连接消失，避免把全单元总门面积误作输入门面积。

`native_cell_gate.py` 绑定平台 LEF/GDS/Liberty/DRC 文件哈希及 094/103 证据。正式正例必须与原单负载输入网的 0.0205/0.02625um² DRC 门面积一致，并读回真实 Liberty 面积、非反相函数及输入/输出电容；所有输入再次核哈希。该探针不修改原生平台或设计，不能直接证明任何修复合格。KLayout 几何连接使用[官方 Region merged/interacting API](https://www.klayout.de/doc/code/class_Region.html)。

实际 Liberty SHA `8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1` 的解析正例已通过：例如 BUF_X8 输入电容 6.585178fF、面积 3.458um²、输出函数 A；BUF_X1 输入 0.974659fF、CLKBUF_X1 输入 0.77983fF。九种缓冲器均实际读取，重复/未闭合 group 被拒，带引号和注释的花括号正确处理。原始库留本地临时资料与服务器，不复制整库进仓库。GDS 门面积与当前设计修复资格仍待安装工具运行。
