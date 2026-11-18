# SYNC-08：最新v5与递推候选的300/200MHz报告

负责人Melodydt，Issue280 / PR295。2026-11-19 Asia/Shanghai。使用独立目录 `work/Melodydt/280/dual-frequency-v5`，分支 `task/280-recurrent-first-round`；本地根为无.git的导出副本，通过GitHub连接交付。本轮不修改父线账本或服务器作业。

300MHz保留PR281 e29d72a5的E32-18结果、PR294 01141df7的P512第3版外推，以及PR295 ceca86ef/6dd7e42b的Qwen3.5/Falcon状态代理收窄。两频率均为512-bit SRAM、三P、DDR630ps、一个读DMA互斥场景包络，分别报告片上与片上+DDR。

200MHz不是直接对总功耗或吞吐乘2/3。沿用此前配对频率/代表层和直接200MHz上下文采样，将每位置及head的旧200/300响应迁到最新300MHz时间；Decode使用既有整层加权响应。事件能量按固定V/T与次数保留，驻留功率分离漏电后按2/3动态比例重算。M忙时采用配对响应，DDR命令与后台/刷新分别迁移，读DMA动态成本保留、静默按漏电分离。Qwen3.5/Falcon分别使用已完成的200和300MHz同网表R活动标定，只删除匹配状态代理；完整LOAD/EXEC/读回动态与单R整窗静默计一次，Falcon注入代理保留。

旧频率采样主要采用E32-9，当前基线E32-18；没有新增200MHz E32-18代表层或整模型回放。200MHz是明确的频率响应迁移估算。另用“旧200MHz时长+新旧300MHz差值×5000/3334”检查敏感性：P512约0.046%-0.203%、Decode约0.019%-0.067%，不是实际误差界，不包含在能耗样本范围中。

52输入已冻结并逐件SHA核验：37个远端Git blob，14份服务器轻量回执绑定已发布ledger中的SHA，1份R候选模型数值与远端完全一致。28个频率/模型窗口、6161项独立数值关系通过；300MHz全范围与上版一致。两PDF各7页/420显示数值，14页全部目检通过。管理结构检查通过，仅验证管理文件。本轮无新仿真，无新综合/物理实现。

完整复算包解压到新目录，保留目录结构后运行：

```text
python -B work/Melodydt/280/dual-frequency-v5/integrate.py
python -B work/Melodydt/280/dual-frequency-v5/verify.py
python -B work/Melodydt/280/dual-frequency-v5/build_reports.py
```

前两步仅标准库；PDF需要ReportLab、pypdf和Deng/Dengb字体，输出目录须存在。`inputs/`优先读冻结快照，不覆盖原输入；`input-manifest.json`、`provenance.json`记录来源和散列。公开包无权重、大波形、综合网表或商业仿真器完整日志，不能仅靠包从头复跑电路。

结果：results.json、verification.json、pdf-checks.json、两PDF及evidence.zip。PDF列明每模型优化、分项和未覆盖项。P512为冷活动/曲线外推，完整序列误差未知；R定点模型精度/转换、加载/门控/实际调度未验收，物理时序、全局互连、PHY/封装/板级未补齐。特殊算子额外候选组合未混入主表，仍保留此前PR295独立结果。

整体Issue280 in_progress，本子交付待独立审查，审查人待指定、PR未合并。登记management-hub PR5 pending；Projects缺board.json及工具，unverified/同步pending，有权限维护者接续。恢复第一步：核对PR295最新commit和publication.json，再验证输入与积分；技术负责人Melodydt。无后台监测。
