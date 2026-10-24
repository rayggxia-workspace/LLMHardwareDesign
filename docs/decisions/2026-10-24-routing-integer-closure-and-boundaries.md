# Issue72：保留精度/代际接口，不冻结独立R物理宏

状态：待审查的研究候选决策，2026-10-24 UTC+08；负责人Liangruizhi。[Issue72/PR73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73)，依据[实际报告](../experiments/issue-72-numeric-closure.md)和[统一SHA索引](../../project/experiments/closure/results/issue-72/index.json)。原Issue70 FAIL/FP桥、Qwen/Llama既有条件均保留。

## 取舍及证据

1. 六个逻辑模板M/V/A/R/S/D保留。固定完整K mixed-unit归约/RQ顺序、完整norm共享group、状态owner/unit/epoch/version、私有试算与guard/retry接口；这些是软件功能和协议义务，不等于必须同宏制造。
2. 不将Granite router固定成廉价纯W8或静态expert连接。评价动态W8 top8变720/6912，W16变6/6912；保守选择性证书全部13,824行回退，不能称低概率宽路由。允许宽重算/guard/可编程topk及gate/LUT接口候选，但未获得应用质量预算前不把集合差直接判定模型不可用。
3. Falcon因果重标/完整整数R消费者在当前72步软件资格通过；S16/S32各51head事件/25epoch且零发布sat，后继局部L2均约3.03%。保留完整conv历史和状态/单位代际，失败代不发布。当前候选协议末端nextnorm后统一提交；未来可带额外队列/信用/回滚证明的解耦方案，不把该同步点宣称数学唯一实现。
4. M/V接口保留group scale和宽ALIGN_REDUCE。固定输入下K512/K256降低nextnorm L2至1.87%/1.67%，但最大误差非全面改善，partial wire增8/16倍。保留元数据因式分解、完整K一次RQ；未有同数值group服务不能据此选择近M或共享V。
5. 不据本批条件服务选择独立R宏或V/R合宏。20配置已独立接收，10对标签日历完全零差，实际D8/R、D2/V、D16/Sspill差小于0.02%。D16spill轻微更快反例保留；VR字节操作服务成本factor2/4（含宽算术、复制/重排、guard和控制，M/SFU/port不缩放）的变化远大于placement差异，不单独归因于宽乘。只继续候选端点/预连线和bank映射，不把此结果包装E2E/PPA收益。

## 制造前与产品后

制造前候选固定局部MAC累加、有限寄存器/端口仲裁、范围guard与版本提交控制、同一算术循环及完整归约协议。必须实际提供带单位/epoch/owner端点、背压、宽部分和、双代缓冲或合法backing；不能期待产品确定后补有源存储/SFU。

产品后在既有实例和合法定制互连内选择M↔V/R↔S等配对、银行/分页、共享SFU、广播/权重复用及调度。独立R与合宏仅是两种候选物理组织。当前不为省跨block字节把RNE/guard/宽对齐或scale元数据删掉，也不统一把FP32字节除四。

## 下一优先级与拒绝的扩展

优先用相同整数函数校准真实S8宽lowering/多周期SFU/ROM与grouped-RQ微实现，随后联合合法prefill批处理、权重复用和state分页比较端口。Granite下一门是完整gate→expert down/merge数值与质量预算，不是再盲加模型。S16窄乘可作另一静态证明的lowering候选，不能由观察小值免费缩位。

不新增模型下载、GPU/其他机器任务，不解封Phi，不接管成员55/63物理工程。未有真实时序/工艺/库或整模型质量证据，保持物理边界和端到端收益待验证；以同Issue/PR交付记录供审查，不自行合并。
