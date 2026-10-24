# Issue68：因果R范围与重定标候选

本工具只消费Issue66已编码的新32步与旧真实256步整数输入，不重复模型推理、捕获或校准。q/k/v/gate、初态及原scale编译的浮点桥原样继承；FP64/native参考只用于误差，不能参与范围决策。无饱和不等于模型质量通过或硬件已实现。

## 冻结协议 causal-range/1

同一原整数编码、位宽和初态比较三种策略：

- `static_sat`：完整复现原静态范围下的饱和递推，逐码核对Issue66原state/output trace和原饱和计数。
- `static_guard`：当前token未clip proposal任一单元越过范围，整个token拒绝，不发布新状态、输出、units、epoch或position。此前成功token保留。
- `guard_rescale`：同样先guard。失败时仅将越界head的当前token试算旧状态执行**逐次RNE右移1**、该head exponent加1，整token重新执行。一个重试波次全局trial epoch只加1，多head不重复加epoch。最多8个重编码波次/9次attempt；exponent不得超过I8上界127，epoch不得超U32，所有宽阶段保留受检I64/shift边界。宽边界拒绝时重试全部head，其未执行算术成本标未资格。

重试不从native/FP轨迹重新加载状态，不查看未来token，不按评价误差拟合scale。多次RNE1可能与一次右移n的结果不同，必须保留逐次轨迹。S16码域[-32768,32767]；S32码域[-2^31,32767×65536]，二者从Issue66同物理范围起点开始。V单位始终保持原值。

每attempt完整执行 decay→完整K预测→delta→outer→未clip state proposal；guard通过才计算new-state output。static_sat是唯一允许clip并发布的诊断。guard_rescale成功时将新state、output、units、epoch共同绑定到同一新version/position；重试旧state副本、units、epoch都只是私有trial，最终拒绝则原提交完全不变。软件SHA是可审计见证，不假设硬件SHA引擎。

## 数据选择与输出

默认固定28个源条件：native `evaluation`四格式(S16/S32×D15/D31)，legacy layer0/14/30×end2048/8192各四格式且必须为真实连续256步。三策略共84条件；`--suite native`为12，`--suite legacy`为72，便于独立并行。旧相邻1步窗不拼接或冒称新256步。

```text
python -B project/experiments/range_service/range.py --native <issue66/state01> --legacy <issue66/long-state01> --suite all --out <新目录> --binding <binding.json>
python -B -m unittest discover -s project/experiments/range_service -p test_range.py -v
```

binding包含 `commit`、`range_sha256`、`state_sha256`。原模块路径固定为 `project/experiments/scale_state/state.py`，两文件SHA必须实际匹配。所有源NPZ与原metrics的大小/SHA均核对，包括暂未选中的源artifact，manifest保存源manifest/metrics SHA及原source provenance。每row保留原格式、校准来源、clip、饱和、保守位宽proof和源NPZ完整描述。

每条件NPZ：`state_trace[commit+1,H,K,V]`、`state_units_trace[commit+1,H]`、`epoch_trace[commit+1]`、`output_codes[commit,H,V]`、`output_units[commit,H]`。状态实际S16/S32存储，输出I64，units I8，epoch U32。单位用于将每步码转换为物理值，不能用最终单位解释全段。

同名JSON有 `tokens`、`rescale_events`、成本与最终已提交见证。每token记录before、attempts、commit或拒绝后的after；attempt记录trial旧态SHA、units/epoch、未clip proposal I64 SHA、逐head违例计数、宽阶段max、是否实际算output及COMMIT/ABORT。rescale事件记录触发token/attempt、head、旧新units、逐次旧/新试算态SHA、RNE非精确数和扫描/读/写字节，`published:false`表示**事件当时**仍未发布，而非最终成功token的units永不发布。

`range-results.json`为逐条件数组，保存1/8/32/256（或已提交前缀）误差、拒绝位置、原失败及实际成本；`manifest.json`索引全部产物SHA。guard拒绝是协议正常执行结果，不能称完整窗口数值成功。

## 成本与结论限制

计入每attempt真实decay/prediction/beta/outer/output乘积、guard扫描、每个完整head的重编码扫描/RNE/状态读写、scale/epoch和commit元数据。Python完整旧/试算/新状态副本**不是免费硬件shadow**；真实SRAM容量、端口、读改写、shadow/backing和多周期宽乘由同资源服务实验定价。materialize/recompute是替代调度，不叠加两者成本。

范围扩张降低每LSB精度；adaptive与static不能被当作同一数值函数直接宣称placement收益。必须在**同一policy/format/实际轨迹**下配对比较物理组织，并同时报告质量与服务。max8重试/I8/I64限制可能拒绝；被拒绝条件不能删除或事后挑选样本。端到端质量、量化非线性、长期跨窗口范围保证、RTL/PPA仍未由本工具证明。
