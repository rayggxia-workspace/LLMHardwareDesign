# Block v1 原生层 hold 与 DRC 修复入口

关联 [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，草稿 [PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。批准计划及其 SHA256 不变，当前仍未取得完整合格物理 Block。

## 现有失败与有限修复

093 的边缘 T6KA 已完成 route/final，但独立 094A STA 的 104356 个端点中有四个 hold 违例，精确最差值 −0.000622502 ns；setup 最差 +5.227097988 ns，cap/slew 计数均为零。原始报告和输入哈希在 `work/YUZE-LU/121/results/run094-t6ka-sta-intermediate/`。该证据为运行中的接收器中间结果，不能替代完整终态。

固定 ORFS 的 `repair_timing_helper` 将 `HOLD_SLACK_MARGIN` 传给 `repair_timing -hold_margin`；global route 阶段按真实 GRT 寄生执行修复，然后详细布线改变寄生。因此增加一次有界分支：从同一 080 封存 CTS 重跑 route/final，保持 `CAP_MARGIN=40`，增加 `HOLD_SLACK_MARGIN=0.005`（ns，即 5 ps）。这是更严格的预制修复目标。SDC、Liberty、时钟、外部负载、面积/修复预算及独立零违例门槛不变；新增 buffer 和所有单元完整计价。不是把验收 slack 容差放宽到 −5 ps。

`native_pipeline_hold5.json` 将候选、独立接收分别指向 104、105。先运行边缘 T6KA；内部候选仍需根据真实 DRC 定位决定修复，避免无依据重跑。后续对照必须使用一致的合格合同和公平成本。105、宏视图、最终网表行为的 worker 入口均支持该严格配置；入口存在不代表任务已经部署、运行或通过。

配置接收要求原配置字节加精确两行目标、实际 make 变量读回、记录和 receipt 哈希一致。Linux 实际上传源码的正例通过；缺 hold、追加限值、错误 hold 读回、错误单位、错误分支、关闭 LEC、过期哈希和跨 pipeline 八个负例被拒，见 `work/YUZE-LU/121/results/native-hold5-config-controls.json`。这仅证明配置约束，不证明修复后的时序或 DRC。

## 先定位实际导体再修复 DRC

094C 保留全部 61 项独立 DRC：三个 M10 间距和 58 个天线违例。技术 LEF 未给出天线规则，库中的 ANTENNA_X1 扩散面积为 0；不能因 router 报零天线而豁免独立检查，也不能编造 diode/gate/diffusion 面积。

新增只读 `native_drc_locate.py/.tcl`：绑定失败接收 receipt、原 lyrdb、源物理 receipt、输入哈希和最终 ODB。对原始 marker 建立带一 DBU 包络的窗口，在实际 native wire/via/PG/BTerm 矩形中保留全部相交候选，导出候选网络及其端口、ITerm、master 和实例包围盒。运行前后重核原 ODB/报告哈希；不修改、修复或导出新数据库。

解析真实 61 个 marker，拒绝新层、未知规则、NaN、奇数坐标和多几何五种坏输入；Tcl 完整性检查通过，见 `work/YUZE-LU/121/results/native-drc-location-controls.json`。实际 OpenROAD 执行另行接收。矩形命中不是多边形所有权或 GDS 电气连通证明，未命中项保留，不把定位脚本 passed 当作 DRC 清零。

后续据实际网络选择预制接入/缓冲/布线修复，并重跑完整原生 DRC/STA/PG/连接/功能。十二层分布式 RC、原生与新增层拼接、完整 C8、宏边界、共同底座和两产品仍须分别完成，不能以本次配置与定位控制缩小总目标。

## 运行与资源

使用现有 `bundle.py` 从已提交 Git 字节封装；新 run 目录与 manifest 不覆盖旧失败证据。103 使用 `native-drc-locate-c`，104 使用 `native-hold5-run-transaction6k-A`；通过统一 dispatcher 计入全 Issue121 的八 allocation 上限，包括 PENDING 和提交不确定状态。其他成员任务不变，不因耗时取消既有作业。
