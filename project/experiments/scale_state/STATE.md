# Issue66：连续递推状态候选

本模块只实现 Qwen3.5 Gated Delta Rule 的整数状态闭包。真实 FP32 capture、conv/SiLU、L2norm/rsqrt/head scaling、sigmoid/softplus/exp、初态和 scale 编译均是明确的浮点桥；不能称完整整数模型或目标硬件能力。

先完整 FP64 逐步 replay，核对原生 output/最终 state；首批旧 256 步窗以同一真实初态运行整数前 32 步、报告 1/8/32 步；后续独立长诊断使用 --steps 256 跑原完整256步（邻接原1步窗仍1步），不将其前32终态接到原end256的相邻窗。新 capture 的33个真实 state boundary可额外直接对比。所有整数步骤使用前一步整数状态，不从原生轨迹重置。

## 冻结格式

- Q/K：源 L2norm 后 S16Q15；Q 已除 sqrt(K)。对称 code[-32767,32767]，RNE/sat 及裁剪数单列。
- V：新 capture 仅由独立 calibration 编译逐 head、2×max dyadic scale；旧诊断缺独立 V 校准，固定 S16Q10，不据评价调整。
- beta：U16Q15，[0,32768]，包含确切1。
- decay：U16Q15 与 U32Q31，[0,2^f]；exp(g) 是离线桥，D15 可把接近1的真实衰减舍入为1，D31隔离此精度风险。
- State：S16 与同物理范围 S32。新数据只用 calibration 的真实初/末状态编译逐 head e16；旧数据由该窗可见初态2×max编码，属于迁移 profile，不能声称生命周期静态范围。e16 最细限制 -26；e32=e16−16。码域 S16[-32768,32767]，S32[-32768×65536,32767×65536]，物理端点完全相同。
- 所有格式、scale 和版本在窗口内固定。初始扫描、重编码和新 epoch 有成本，未来越界会保留为饱和，不通过重拟合掩盖。

步骤：`dec=RNE(S*decay,f)`；`pred=RNE(sum_K(dec*K16),15)`；V 对齐到 state 单位；`delta=RNE((V-pred)*beta,15)`；`upd=RNE(K16 outer delta,15)`；`Snew=Sat_state(dec+upd)`；`out=RNE(sum_K(Snew*Q16),15)`。pred/residual/correction/outer/output 使用受检 I64；只有最终 state 饱和。不把完整 K 拆开提前 RQ，不先写部分 K 后重算 delta，不读取旧 state 作为新输出。

32×16预测累加的保守格式界可需54位；D31 state乘积可需64位容器。每阶段观察位宽、格式上界、溢出拒绝和最终饱和都记录。S8基数分解仅为候选成本：S16为3 digit、S32为5、I64为10；U16 gate为3、U32 gate为5，移位/宽合并/控制/端口另计，没有真实 S8宽乘执行速度证据。

## 数据及执行

```text
python -B project/experiments/scale_state/state.py --root <capture目录> --binding <冻结JSON> --out <新的结果目录>
python -B project/experiments/scale_state/state.py --root <capture目录> --conv <整数conv结果目录> --only-coupled --binding <冻结JSON> --out <新的耦合结果目录>
python -B project/experiments/scale_state/state.py --root <旧真实256步窗目录> --steps 256 --binding <冻结JSON> --out <新的旧窗256步诊断目录>
python -B -m unittest discover -s project/experiments/scale_state -p test_state*.py -v
```

binding 格式为 `{"commit":"实际commit","state_sha256":"state.py实际SHA"}`。输入支持旧 `windows.npz` 与 manifest.windows 字典，及新 `state-raw.npz`/manifest.state.checks 的 calibration/evaluation；严格核状态 NPZ SHA/bytes。新 capture 的 consumer 大包不由本分支重算/核验。

每条件输出 `窗口.S16.D15.npz` 等，保存 compact Q/K/V、unsigned beta/decay、初态、全部整数 state 边界、I64输出、scale、原生输出和 FP64状态参考。state-results.json 给逐长度误差、初态/operand裁剪、饱和、near-one decay、保守/观察位宽、commit记录及成本；manifest.json索引 SHA 和源版本。calibration 条件只作编译/诊断，evaluation不能称完整模型质量接受。

可选 `--conv` 严格接收 `conv-output.npz`、其manifest SHA/bytes及 `capture_manifest_sha256`。`conv8/conv16.evaluation.query/key/value` 分别由 H8/W8、H16/W8 整数conv及明示SiLU桥产生。只在 evaluation S32/D31追加两项，使用原生独立cal编译的同一eS/eV，隔离conv输入变化；g/beta和真实初态保持原源。另保存同coupled输入FP64状态/输出参考，将conv输入/浮点桥误差与R整数误差分开。`--only-coupled` 仅执行这两项，不重复已完成native八项；不带该参数共十项（校准四、评价六）。conv自身的实现/成本由其单独结果索引负责，本模块不冒充全整数conv到norm/门控链。

`--steps` 默认32，可选256，只消费原窗已有真实步数（例如原1步窗仍只执行1步）。不会复制token、拼接窗口或在中间重编码state。长窗报告1/8/32/256及原native最终态对比，记录requested/actual原始长度；它扩展旧诊断跨度，不是新的独立质量样本。完整整数state trace及FP64参考留在服务器，较大文件按项目共享存储/SHA规则交付。

chunk8/16 与整段严格保持相同初态码和 scale/epoch，逐输出、state、commit完全一致。StateLease 用 sequence/scale/epoch/position/version/旧新state和输出哈希拒绝过期、异序列、改码和重复commit；哈希是软件证据，并非假设硬件已有 SHA 引擎。

单个128×128 S16 head已占32KiB，S32为64KiB，metadata/临时量/事务shadow都另计。可按 V列切片保留完整 K，但 gated norm仍须跨原始完整V归约。物化 decay 与重算 decay 是替代成本，不能相加或假设旧/新事务缓冲免费。成本字段仅为明确假设的字节/基础积账本，尚无公平服务/RTL/端到端/PPA结论。
