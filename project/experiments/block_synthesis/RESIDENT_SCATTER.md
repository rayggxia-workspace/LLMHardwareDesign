# 原生逐行结果地址的搜索

这是现有M最终化指令的地址选择，不是S内复制器。每个ROW_M_FINAL仍选择实际累加行、格式、移位和目的S字，逐行等待写ACK。
输入布局、计算次序和数值范围保持；同一M累加上下文直到全部行输出后才可覆盖。
仅启用已经资格化的active-prefix合同，不据此授予新接口、宽数据重排或跨S通道。

`resident_batch.plan(..., final_layout='contiguous')`是原候选族；`scatter`令各行写入独立8字单元首字；
`choice`在相同前沿比较两族，每写一行都更新S记录、脏后备、实际STORE/ACK和成本。
原连续写回保留；有界前沿可能剪掉较好的历史，因此组合结果仍保留旧计划和最强贪心，不保证增加候选就单调改善有界搜索。
`width=None`只在小例用于穷举；严格贪心与DP使用同一硬件动作，不把固定策略的弱基线当作算法收益。

```text
python project/experiments/block_synthesis/resident_scatter_survey.py MASKED_PROGRAMS IR FRESH_OUTPUT --width 8
python -m unittest discover -s project/experiments/block_synthesis -p 'test_*.py'
```

调查保留全部输入计划，另比较choice/强制scatter的贪心和DP；成本从每个前沿的S内容重新计算。
独立有限S回放检查所有原操作、行号、源地址、S64累加、最终舍入、外部后备及边界提交。
完整程序RTL通过`resident_batch_probe.prepare`冻结真实M/E/feeder/S；主机只搬整字，不做任何重排或数值运算。
观测读访问及主动背压使探针周期不同于系统执行时间，不能据此计算token/s或能耗。

这是地址布局的一种动作族，尚未统一任意结果向量表示、列打包、任意字对齐或跨S直传。
新真实权重/共同图覆盖注册/完整模型/SystemC/DRAM/能耗/token/s均须另验。
