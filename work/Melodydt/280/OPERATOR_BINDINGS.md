# 算术缺项 2–4：真实输入与 RTL 绑定边界

用途：Issue #280 / PR #281 的新增算术标定；负责人 Melodydt。沿用 512-bit SRAM、三路 FFN、代表性历史位置和冻结两步 decode/短 prefill。只添加观察点，未修改原冻结模型数值或模拟事件。2026-11-17，Asia/Shanghai。

## 已确定的绑定关系

| 项目 | 冻结 TLM | 当前候选 RTL | 本轮推进与尚缺项 |
| --- | --- | --- | --- |
| RMS 因子与 gamma 乘法 | 两次独立 RNE，S32；每个 PRODUCT 叶节点 9 周期 | `e_s32_native` + `e_s32_ap64`，四个 S32 元素，64-bit 输入口 | Llama/Qwen3/Granite 共 14,208 个真实乘法包逐项一致；连续输入/输出无阻塞时 18 周期/包。尚未校准调度/访存/等待周期 |
| RMS scan/apply | 动态 S16 范围扫描、分开归一化和 gamma | `s32_rms_range_scan` / `s32_rms_apply_s128` | 映射完成；需要包装逻辑真实活动、共享实例/驻留积分。跨 bank gamma、超过单 bank 容量的部署须单独绑定 |
| Softmax | S32 score、整数 LUT 参考，长度随 KV 窗口变化 | `n_s32_softmax_s128` | 已有候选映射；本轮捕获实际 score、exponent、probability 和按窗口/形状的调用计数，待逐项 RTL 验证及功耗 |
| RoPE | 原生 128 维分段及 64/部分/256 维路径，Q14 系数和分步 RNE | `rope_e32_ap64` + E32 | 包装逻辑映射完成；原生路径记录所有 shift/符号，其他路径记录整个旋转向量。待验证各变体的饱和、周期及活动 |
| 缩放/专家加权和 | S32 Q16 乘法，独立 RNE 后加法 | E32 PRODUCT/ADD2 | 捕获实际输入、gain/probability 与输出；需要编排及功耗，不用乘法 cell 数直接替代能耗 |
| Gemma GELU | FP64 tanh 近似后舍入，再与 up 相乘；40 周期/四元素 | 当前 G32 提供 SiLU；S16 表函数 G 不等同 S32 GELU | 捕获真实 gate/up；审计 S16 Q10 输入范围。须明确近似/格式、验证模型误差及对应 RTL，不能沿用 SiLU 能耗直接验收 |
| Granite top-k/router | 40 个 S32 score；精确排序取 8，浮点 EXP/归一化后 Q16 | 既有 N top-k 使用 S16 | 捕获排序和路由概率；审计最小共同右移后的 top-8 顺序，尚缺 RTL tie 行为与 routing softmax；这里只是有界样本可行性 |
| Qwen3.5 GDN | float32 状态计算、每块写回 Q16；32 路时间模型 | `block_v1_r` 八路 S32 状态、S16 Q14 key/query、UQ1.31 decay/beta、分阶段 RNE | 捕获 16×128 块；审计候选逐阶段定点计算、溢出和输出误差。实际 RTL 指令加载/执行/提交、数值验收、周期与功耗未完成 |
| Falcon Mamba2 | float32、16×256 块、32 路时间模型 | 同一八路 R；SSM decay 使用 shadow bank、另传 inject/skip | 捕获块和因子；候选入口采用 Q16 delta×Q16 value 后 RNE。该入口尚未成为已验收实现；不得将整体时间直接乘四 |
| Conv4 / recurrent factors / norm-gate | float32 四 tap 卷积、Softplus、EXP、Sigmoid/SiLU、归一化 | R 卷积需要 S16 Q14 taps；其他服务尚未完成匹配 | 检查系数范围及时间顺序（TLM 旧到新，R 新到旧）；Softplus/EXP/归一化需补实际实现及误差/活动标定 |

## 样本和证据口径

`operator_observation.py` 记录全部调用计数，每个窗口/算子/site/形状仅保存前两个输入/输出；RMS 保留既有完整服务样本。样本极值不是置信区间，也不代表所有层的活动分布。浮点服务必须保存原始数值，不能先换成量化值再声称是原 TLM 输入。

`verify_operator_capture.py` 复算捕获的 TLM 结果；冻结运行器另行核对模型输出和时序。`audit_operator_bindings.py` 只给出格式可行性和候选定点误差，明确区分缺少匹配 RTL、系数越界、溢出与尚未 RTL 验证，不能把候选 Python 定点计算算作 RTL 验收。

E32 检查器使用真实 RMS 两阶段乘法；测试不含 SRAM 和完整 scan/apply。18 周期是第一个输入握手到最后输出握手的连续无阻塞口径，不能据此直接改写完整模型速度。E32 64-bit 指令数据入口不意味着 SRAM 从 512-bit 改成 64-bit。

功耗使用 Nangate45 typical、综合后标准单元与 RTL 边界 VCD 活动传播，不加载布线寄生、不执行内部门级活动回放、不宣称 300 MHz 时序闭合。E32 波形周期 3334 ps，与冻结 TLM 一致（名义 300 MHz）。完整 RMS 还需 N、scan/apply、相关 SRAM 操作及共享资源驻留，不能把每个算子的 idle 全部相加。

大型向量、网表、波形留在获授权服务器目录；Git 仅保存脚本、输入/输出 SHA、简小回执和交接。运行命令及成果入口见 `docs/handoffs/2026-11-17-issue-280-operator-expansion.md`。
