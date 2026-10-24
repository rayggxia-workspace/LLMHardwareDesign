# Issue70 独立接收合同

`receive.py` 不导入 Granite/Falcon producer 的算术。它接收冻结的结果目录，先核验 manifest 索引的**全部**文件大小与 SHA-256，再执行下面的独立检查。模型权重本体不重新下载、不重放全模型；权重来源由采集清单及服务器下载回执约束。

```text
python -B receive.py --model granite --result NUMERIC --capture CAPTURE --producer-source FROZEN/granite.py --binding RECEIVE_BINDING.json --out NEW_AUDIT
python -B receive.py --model falcon --result FALCON --producer-source FROZEN/falcon.py --binding RECEIVE_BINDING.json --out NEW_AUDIT
python -B receive.py --model transport --result TRANSPORT01 --repeat TRANSPORT02 --producer-source FROZEN/transport.py --binding RECEIVE_BINDING.json --out NEW_AUDIT
```

`RECEIVE_BINDING.json` 至少含真实 `commit` 和本文件 `receive_sha256`。`--producer-source` 对照实际冻结 producer 文件；省略时回执明确记为未执行，只核 manifest 中 SHA 格式。输出目录必须不存在。默认创建实际改写文件并重算 manifest SHA 的负例；`--skip-negatives` 只能产生 `PARTIAL`。

## Granite 决策见证

- 32 个实际完整 K 的 W8A8 点积使用 Python 任意精度整数复算，核对声明的对称格式和 INT32 条件范围证明；不是全部专家所有点积重放。
- 32 个真实重新量化见证，独立检查 I64 乘积、signed ties-even、饱和；shift **已经包含 Q31**，不再重复加 31。
- 对两种激活 scale 方案分别从完整 40 路 FP/quant logits 独立重排 top8，平局按专家下标升序；量化路由必须重新选取。FP softmax 及 gate Q15 对照真实选择，不接受任意八个 gate 冒充路由。
- 四种激活/路由组合各检查一个完整 `8 × H1536` 见证：每个专家完整输出重新量化到共同 power-of-two S32 单位，然后计算八路 Q15 权重乘积与完整 S64 和，最后一次 RNE15/S32 饱和。共同单位与最终 hidden 归约均核对。
- `route_fixed_diagnostic` 保留为对照，不据其结果声称动态 MoE 已通过。
- 实际负例：改写完整 dot 的保存累加值、改写量化路由选择；重新生成 NPZ 和 manifest SHA 后仍须由数学/语义检查拒绝。原始文件保持不变。

softmax、SiLU、scale 选择、除法和 Q31 系数生成仍有浮点桥；这些不获得整数 SFU、宽乘硬件或端到端质量资格。

原始 reference 失败时默认拒收。仅在显式 `--diagnostic-failed-chunk` 下，允许原门限不变、cal/eval cached 与完整 MoE replay 都过、cal chunk 过且**唯一 evaluation.chunk16 失败**的有限局部诊断。接收独立核原 manifest 与 qualification 链；数学见证通过仍输出 `PARTIAL_DIAGNOSTIC`，不会把原始 FAIL 改成整模型参考 PASS。transport 同样需要此开关并完整透传失败链。

## Falcon 决策见证

- 明确采用并行 Attention + **Mamba2**，不是 Qwen3.5 的 GDN。由真实投影及完整因果 conv 权重独立构造 FP64 conv/SiLU/softplus/exp 系数。
- 对完整 head0 的 `D128 × N256` 校准/评价序列独立重放：
  `state = a*old_state + x[:,None]*(dt*b[None,:])`；
  `y = state @ c + D*x`。浮点运算顺序固定；完整输出之外增加边缘行的 Python `math.fsum` 见证。
- S16/S32 是**整数状态存储、FP64 系数与更新**候选。单位由独立 calibration16 的 FP64 状态最大值冻结；评价不调 scale。核全部 code/state/output/saturation；每步极值及边界 cell 用 Python integer 对已冻结 IEEE FP64 proposal 独立做精确 ties-even/sat。
- 全部 KV/conv/SSM 初末值的实际 shape、owner、位置、版本和每个 chunk 边界的 epoch 描述保持一致。KV 有序增长，conv/SSM 不能每窗清零。描述是分析元数据，不声称框架原生强制 epoch。
- 原生 full/cached/chunk 的误差由保存数据独立重算，按执行前冻结的门限记录逐项 `passed`。数值失败保留在 `native_acceptance`，不会因数学接收成功而改成原生一致性通过。
- 重放完整 4096 维 gated RMSNorm，保留所有 32 head 的归约依赖；不能把它改成每个 head 独立 norm。
- 投影的 16 个分层抽取输出检查完整 K2560：W8/A8 编码与 scale 来源、全部 Python integer dot、INT32 条件界及 FP dequant 分列。
- 实际负例：改写 S32 code，以及改写 chunk epoch 描述；更新对应文件 SHA 后仍须拒绝。epoch 负例证明接收合同的一致性检查，不证明原生模型的事务/认证协议。

原生门限（不根据结果放宽）：full/cached 末 logits、layer0 chunks 输出/完整 cache 的 relL2 ≤ `2e-4` 且 maxabs ≤ `1e-2`；并行汇合 ≤ `2e-6` / `1e-3`；FP64 head state/y 相对原生 ≤ `2e-4` / `1e-3`。

投影的浮点编码桥有明确求值 dtype：原始 norm×MuP 输入为 FP32，保存时无损转成 FP64；dynamic max/127 与输入除法仍在 FP32，static Python-float scale 和输入除法为 FP64。接收按这些实际规则重建，严格等值检查 scale、codes 与 dots，不能把文件保存 dtype 当作另一种量化器。旧接收将 dynamic scale 按 FP64 重建所致的失败应保留，修接收后仅重跑审计。

接收另外记录实际 scale NPZ 的 dtype/元素数/nbytes，避免将 producer 旧报告中硬编码的 `size*8` 当作每种方案真实存储。动态 FP32 scale 和静态 FP64 scale 分开；若目标接口另选 FP64，须显式记录转换与传输格式，不能静默改写原始 SHA 绑定报告。

## COPY/PORT-IO 独立接收

transport 接收不导入 producer 或 producer 调用的 checker。它重新核所有实际来源 manifest/artifacts、完整日历 gzip、每个分包的 header/padding、连续对象与银行地址、每次访问的 128-bit 拍数，以及依赖和资源容量事件扫描。不同地址不能免费拼接：例如 offset=15 的 3-byte 元数据须两拍。每个已声明 suite/tile 都有相同两种 staging layout 与两种策略预算，配置数从实际清单推导。

完整消费者义务另外检查：Granite top8 的所有返回/RQ 参数两跳路径；Falcon 先 gate 后 norm 的首遍 raw+gate、完整4096归约屏障和第二遍 raw/gate/gamma；residual+A+R 三输入与一输出；完整 head state 所有 proposal 写入先于 published-state 读取。FP32 搬运和 S16 存储候选分列，不能将 FP32 图改称 S32/INT8 递推性能。

实际负例改写 wire 字段和消费者字节账，并更新 gzip/JSON 及 manifest SHA；必须由独立公式或消费者检查拒绝。此接收只证明 COPY/PORT-IO 下界合同，没有添加算术、宽乘、非线性、原子 guard 的零成本假设，也没有把该下界称整图服务或物理周期。

## 执行状态与边界

2026-10-24 在本机运行 `python scripts/check_project.py` 通过，随后在任务专用 D 盘 TEMP 下运行 `python -B -m unittest discover -s project/experiments/architecture_extensions -p test_receive.py -v`，28 个小合成边界检查通过。包含完整 8×1536 合成 merge、实际重写 SHA 的 dot/route/wire/ledger 负例、小 Mamba2 状态与 epoch 描述拒绝、FP32 编码桥差异及显式 PARTIAL 失败链约束。

这不是服务器真实模型接收回执。真实接收必须由服务器对实际输出执行以上 CLI，保存 `audit.json`、源码 commit/文件 SHA、运行命令和 Slurm 作业证据后才能记录。接收通过仅表示此有界数据/数学合同通过；没有全模型 W8A8 质量、真实 INT8 性能、无浮点硬件、RTL/PPA 或最终物理边界验收。
