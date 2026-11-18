# 200MHz估算方法和证据边界

以PR292的300MHz论文表为冻结对照，不吸收父会话#280正在新增的算术覆盖。3334ps变为5000ps，DDR保持630ps。模型专用runner分别来自已验收的六模型能耗回放；Qwen3沿用共享冻结runner。

每阶段在300/200MHz执行0、中间、末尾代表完整层，Gemma加5层，混合模型加3层。两位置间保留被抽样层的KV和递推写回；跳过层使用原冻结上一层残差恢复U SRAM，不把恢复操作计入模拟时间。层输出、Decode完整词表logits必须逐字节相同。Gemma沿用s32/Q12残差，不更改其数值格式。

时间估算对每个原始完整层时间乘以同页结构类别中最近代表层的T200/T300；入口、PM启动、残差读和输出头分别修正。三路FFN并行、控制和DDR重叠都保留在整层回放里，不加和各P忙时。300MHz截取层相对原对应层的时间差只作为截取上下文偏差，不能替代全模型200MHz误差。512token沿用旧端点线性公式：P1+511L+130305*(H-L)/512+最后一次head，仍未整序列验证。

片上驻留分项使用原参考对应端点的漏电份额，固定V/T下P200=(P300-Pleak)*2/3+Pleak，乘以重建整窗时长。M增量以观测忙时和2/3动态系数修正；其他已标定事件能量固定，验证抽样的SRAM计数、服务次数和逻辑读写完成数相同。DDR命令数可随请求合并、行状态变化，不强求命令计数一致；分别按样本在原整层时间中的权重计算访问命令能量比、后台/刷新能量比，然后作用于原全窗DDR分项。

低高区间来自原功耗标定样本端点，不是误差置信区间；功耗覆盖缺项沿用原版。短Prefill能耗是2token窗口，512Prefill只给吞吐预测，不能与短窗口J/token相乘求长窗口功率。物理时序未签核；无新综合或布局布线。

执行记录：38832271整体FAILED但Llama/Phi/Granite12个子项成功；38832316 Qwen3四项完成且作业0:0。38832294、38837918无完整成功结果；后续38837935补Gemma/Qwen3.5/Falcon。失败记录保留，不混入测量表。

早期抽查进程运行时共享驱动文本随后更新，samples.json结尾采集的驱动文件SHA不一定是该进程加载的源码版本；按每个作业开始复制的source-commit.txt与GitHub提交恢复实际驱动。38837935起将驱动和sbatch复制进独立run目录，避免此问题。模型runner、DDR库和冻结资产只读。

复算：解压results/accepted-results.zip到results，然后执行 python -B work/Melodydt/293/integrate_frequency.py 和 python -B work/Melodydt/293/verify_results.py。报告生成使用包含reportlab、lxml和python-docx的已解析Codex依赖Python。正式工件在output/pdf与output/docx，仓库发布至docs/experiments。
