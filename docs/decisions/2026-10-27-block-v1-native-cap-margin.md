# 原生电容修复候选：封存 CTS 后标准重布线

2026-10-27 06:38 CST；Refs #121。原计划及 SHA 不变。

080 修正实际轨道后的 T6K-C（92089/node20/32CPU）自然完成六阶段，耗时39:39、MaxRSS 21268324K。其最终原生报告仍有8个 max-cap 违例，最差 slack −4.763801574707031 fF；setup/hold计数均0。报告及回执绑定见 `work/YUZE-LU/121/native-t6kc-080-cap-observation.json` 和 `results/run080-t6kc-terminal/index.json`。这是源报告观察，不是完整独立接收或合格宏。

新增有限修复 cohort 088：四组候选各自依赖对应080成功封存，从同一份CTS检查点重新执行标准ORFS `do-route`、`do-finish`。新配置必须逐字节等于原077配置加一行 `export CAP_MARGIN = 20`。实际安装源码 `util.tcl` 的 `repair_design_helper` 将该值传给 `repair_design -cap_margin`；这是更严格的预制修复目标，不修改Liberty最大电容限值。die、端口、存储、数学、时钟/IO/负载、预算和全部验收门槛不变；修复单元完整计价。四候选采用同一修复策略，不能将不同优化强度的A/C直接当公平结论。

实现 `native_reroute.py` 绑定原080回执、原077准备回执与配置、所有复制的1–4阶段文件；复制到新输出树，不修改原候选。核验原生TECH/RCX、M1–M10、KEEP_VARS=1、LEC_CHECK=1、SEC_CHECK=0及实际CAP_MARGIN=20；每阶段后重新核验来源和副本。最终仍运行标准LEC、RCX与报告，不手工替换失败数字或跳过repair。

`native_pipeline_cap20.json` 是单独的088/089链，保留080/085及历史057/081。模式为 `native-cap20-run-<top>-<A|C>`、`native-cap20-receive-...`、`native-cap20-view-...`。新独立接收器核验088实际配置并用该配置从最终DEF生成GDS；不能默默换回原cap0配置。宏视图必须依赖对应接收通过，并绑定同一pipeline/source，不能跨候选借用合格结论。

当前只完成代码和静态检查，088尚未运行。正式结果必须由回执及独立接收证明；若仍有违例则保留失败，不能放宽电气、面积或功能要求。十二层分布式RC、完整最终网表功能、同源宏视图边界、共同底座和两产品互联仍分别必需。


## 2026-10-27 06:42 CST：部署与配置负例

080 T6KC/92089自然完成39:39，但最终原生报告仍有8个max-cap违例、最差−4.763801575 fF（setup/hold计数0），不能冻结。新增088从对应080封存CTS重跑标准route/final，只有CAP_MARGIN=20这一更严格修复目标；Liberty限值、时钟、负载、预算及检查不变。92106/node20/32CPU正在运行，其他三候选等依赖/空位；089独立接收已部署但尚无作业。配置正例与缺margin、额外限值、LEC关闭、错误读回、旧哈希五种负例已通过。 配置控制见 `work/YUZE-LU/121/native-cap20-config-controls.json`；仅证明配置接收规则，不能替代真实电气结果。088归档SHA 57e9409fb8876105f5c4756699f49237e6c794ec928d11ba93dfad0661a0ab03，源码534fa2e17a764a67f8f9ccd41b65ac807251f856。
