# Issue59：Llama down_proj 的校准、scale 粒度与归约边界

2026-10-23（UTC+08:00），Liangruizhi；[Issue59](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/59)、
[PR60](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/60)，base PR57。全部计算在本机执行，未下载新模型。

**本轮结论：校准覆盖不能替代合适的 scale 粒度；K 分组改善误差，却把 scale 对齐、归约、格式元数据和端口一起带入 Block 决策。**
24 个候选均未通过预先冻结的 5% 局部误差探索门；这不是完整模型质量失败，也不是 EDA 给定语义等价的前置否决。
当前不能宣布最终量化合同或制造划分完成。服务数字只表示特定有界调度模型，不是实测硬件加速。

## 实际范围和可复现来源

- 既有 Llama-3.2-1B-Instruct BF16 checkpoint，ModelScope revision `d3e551343d4d81508a0d226656b826c217e463cd`，对应官方元数据 `9213176726f574b556790deb65791e0c5aa438b6`。
  9 文件重新核 SHA；权重 SHA256 `1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f`，权重不提交。
- B1、layer0 down_proj，完整 K8192，**仅前16输出通道**。不代表全 N2048、全部层、应用质量或长上下文。
- 原校准32 tokens；新增科学、代码、对话各32，合成 expanded128。所有 scale 选择只读校准。
  systems/arithmetic 已在 Issue56 观察，属于诊断；预先冻结新的园艺 heldout，prefill32+teacher-forced cached decode8。
- torch2.10.0+cpu、transformers4.57.6、NumPy2.5.4，原 BF16 权重转 FP32 计算，非独立原始 FP32 模型。
  实际 Llama 实现 SHA `31bf660a663259134324bc65da4e155951dc89c5ca46471d2325a9938e859e26`。
- capture01 源码 `1ef11971bcda0ea35484e2d7857cbeb3c91e2df7`；capture02 `f025806f9f5faae5df775149ace3a67430c9aac9`。
  两次捕获 NPZ 与 inputs JSON 相同；heldout full/cached A 最大差 `2.98e-7`，Y `6.15e-8`，均过 atol/rtol1e-4。
- **正式 numeric04/05、service04/05 源码** `6d2d6603fde7e2372bd399c1cee511e33e6c2781`；
  权重相关边界分析、最终编码重放/打包工具 `e5bca383e79ad076aceac76c235b830fdebc5b14`。
  初版数值/服务与失败保留，不用旧服务数字替代加上范围守卫后的正式数字。
- 完整输入/工具/源码/output SHA 在各 manifest、包内 `records/`、`local-data-index.json`；
  capture02 SHA `0504e25ec36aa88d96ae4c3365ce22533ff3946d92c961f7e80bee0eb3daf749`。
  所有临时文件/缓存位于 `D:/Projects/Codex/llama-downscale-20261023/`。

## 冻结比较与数值合同

静态 A：original32 / expanded128 × max / 输入重建 MSE × 全 K / K512；动态 A：逐行全 K / 逐行 K128 / K512 / K2048。
每种再配 W 每输出全 K 或每输出 K128，共24候选；三文本×prefill/decode，共144条件。
MSE 只在预先冻结的7个 dyadic 指数中搜索，不拟合评价数据或输出误差；相同 MSE 取更细步长。
Y 指数固定来自原校准 Y 的2倍 headroom，所有候选一致。

| 对象 | 明确合同 | 硬件边界 |
| --- | --- | --- |
| 原 A | FP32 非线性结果，离线 RNE 转 S32、exponent=-20 | 非线性仍浮点；bridge 最大绝对差 `4.768e-7`，非全整数模型 |
| A8/W8 | symmetric [-127,127]；scale=2^e，e 为 i8 | 静态/W/Y 编译用 FP64；动态 A 从 S32 整数 max、移位比较求指数 |
| 动态零组 | e=-20，codes=0 | 不使用 log/div/sqrt/LUT；不借用未实现 INT16/宽乘法 |
| 组部分和 | INT8×INT8→INT32，最坏界 `group*127^2` | 全 K8192 界132128768；K128界2064512 |
| 对齐与归约 | units=eA+eW；e0=min(units)，精确左移后 checked INT64 归约 | 无中间舍入；eA+eW/e0为i16；spread>35拒绝；`8192*127^2<<35 < 2^63` |
| 输出 | 对 complete value 仅一次 signed RNE、sat8 [-128,127] | 右移 +/-63范围显式；饱和左移先查阈值，硬件不需产生超宽结果 |

CPU 实际整数参考不等于目标硬件 INT8 速度。新增 CLZ、32bit RNE/sat、64bit shift/carry/add 是**候选能力**。
64bit 路径按4个32bit limb slots/8lane更新计成本，每 slot 1/2/4周期敏感性；不假设免费宽乘法。
只支持声明的可整除 K 组；尾组未实现并拒绝，不声称尾块验证通过。

## 误差与机制

以下为六个局部条件的最坏输出相对 RMSE；百分比非端到端质量指标。

| A 方案 | W 方案 | 最坏误差 | heldout prefill / decode |
| --- | --- | ---: | ---: |
| 静态全K，原/扩展校准，max/MSE | 每输出 | 91.83% | 85.66% / 91.83% |
| 静态K512，原校准max | 每输出 | 32.09% | 完整指标见包 |
| 静态K512，原校准MSE | 每输出 | 30.97% | 完整指标见包 |
| 静态K512，扩展校准MSE | 每输出 | 31.98% | 完整指标见包 |
| 动态逐行全K | 每输出 | 16.88% | 14.30% / 8.53% |
| 动态逐行K2048 | 每输出 | 11.34% | 11.04% / 完整指标见包 |
| 动态逐行K512 | 每输出 | 8.85% | 8.85% / 完整指标见包 |
| 动态逐行K128 | 每输出 | 7.36% | 7.21% / 3.55% |
| 动态逐行K128 | 每输出K128 | **5.39%** | **5.39% / 3.41%** |

四段校准最大绝对值19.66–30.41，中位绝对值约0.00357–0.00419；全 K max/MSE 均选 e=-2，扩样本不改变这一指数。
少数大值和大量小值共用 scale 的问题仍在；MSE 在组内会改变部分指数，却没有解决跨文本误差。
不把本次输入 MSE 搜索的失败推广为所有校准、平滑或非 dyadic 方案无效。

最佳候选 heldout prefill 在最终 RQ 前误差4.81%，RQ 后5.39%；decode2.33%→3.41%。
这使**输出格式/scale**成为下一项有区分度的小实验，但不能事后用它调整本轮的5%门，或称 heldout 已通过。
所有条件输出饱和为0；MSE静态候选有少量 A clipping，最多18值；动态A无裁剪。
提前每组 RQ 再求和共改变25847输出，不是相同函数的划分，不能参与“等精度收益”排名。

### 必须区别粗位宽界、实际权重界和观察值

K128/W128 的当前 scale 矩阵按任意满幅 INT8 W/A 的粗界需35 signed bits，最大10950171648；
**这不是观察到 INT32 溢出，也不能直接得出必须增加 INT64。**
固定真实 W8 后，单输出的可实现最坏界为：

`B(row,j)=Σg 127 * Σk∈g |W8[j,k]| * 2^(eA[row,g]+eW[j,g]-e0[row,j])`。

三文本 prefill 最大分别1628977057、1616862273、1623441762，均可放 INT32；
用 A8=127*sign(W8) 实际构造达到边界的整数输入，S32源格式有效且重新生成动态指数相同。
编码重放工具另行核对这三个界。实际捕获最大对齐值仅约80万、99万、105万。

这个更紧结论只覆盖**16输出、当前所见指数组合、固定W**，不覆盖全层/其他权重/未来动态 scale。
32bit候选若依赖权重相关范围守卫，应计入系数/检查成本：例如16×64个u32组L1系数就需4096B，
尚未纳入当前 portable64 的 metadata预算；不能免费用离线 Python 证明替代在线硬件。
因此32bit加可证明范围检查和通用宽归约都保留，位宽尚不冻结。

## 同资源容量、元数据、端口与服务

1152配置 = 24候选×1/4行×near/shared×1/2/4 limb周期×1/4组batch×fifo/critical。
每候选/行数/limb下两侧各自优化 batch/调度，共144对包络，不固定共享侧为最差策略。

资源固定：S8×32KiB、每bank1RW/128bit；S0..3放128KiB W8，S4单行32KiB源ring，S5最多4行A8，S6 metadata，S7结果。
M总32KiB含2KiB PE、8KiB MA、16KiB MW、6KiB MC；V16KiB。一个相同8lane归约引擎仅改变位置，near 不复制额外引擎。
单128bit总线、64B包头/64B payload对齐、<=1984B payload、2KiB TX/RX credit；片段、bank读写、暂存均显式。
完整行动态量化因源32KiB>V16KiB而读S两遍；K<=2048组在V保留<=8KiB并本地重读。
所有候选包括外部source32 DMA、max/CLZ、量化与A8发布、元数据编译/守卫、部分和、宽累加、最终RQ和S7输出。
初始 W8/static metadata 驻留和预打包在计时前；不含完整层外存权重、上游非线性、全图流水或外部系统。

代表最佳 K128/W128、limb=2：

| 项目 | decode tile1行 | prefill tile4行 |
| --- | ---: | ---: |
| near周期（模型值） | 58545 | 130566 |
| shared周期（模型值） | 59367 | 133686 |
| near减少 | 1.385% | 2.334% |
| near / shared物理wire bytes | 237312 / 242304 | 523584 / 540864 |
| A指数 / W指数 / Y指数 / e0元数据B | 64 / 1024 / 16 / 32 | 256 / 1024 / 16 / 128 |
| INT64 accumulator B | 128 | 512 |
| 最大4组partial暂存B | 256 | 1024 |

同一方案4行时量化前source逻辑131072B、A8为32768B；wire是完整流程523584B，不能用131072/4当物理收益。
对照全K动态4行：metadata164B、wide updates64；K128/W128为1424B、updates4096，宽引擎/MC压力显著增加。
三种limb假设下该方案 near 降幅约1.36%–2.37%；全部24候选为0.0105%–2.8394%，**无一通过本轮局部数值screen**。
这些是给定语义下的条件服务差异，不是可接受应用的加速排名，更非目标芯片端到端/PPA收益。
4组部分和合包比逐组发送节省包头；decode单组64B与最终16B都占128B包，不能用逻辑4:1当物理4:1。

## 本轮对 Block 的具体调整

1. M内固定的是**同单位的组内INT32累加**；tile完成不再隐含“完整Linear已到同一INT32单位”。
2. M出口必须携带 group/row/output坐标、scale版本与完成语义。显式 `ALIGN_REDUCE` 算子位于组部分和与最终RQ之间。
   已知相同单位可旁路；不同单位未经对齐不可跨组直接相加。
3. 保留 M附近可选择的归约/最终RQ路径及共享V路径。若最终选择K128，短链有消除部分和包的潜力；
   但低百分比服务差和新增范围/位宽不确定性不支持此时冻结不可绕过连接。
4. A8与metadata必须一起发布；D管理源ring、组scale冻结、partial batch与消费者事件。
   V↔S扫描/量化连接和MC/VC1RW压力，与M↔V归约位置一起记账。
5. 不增加“每模型专用Block”；先比较 portable64 与经证明范围守卫的32bit对齐、输出INT8/INT16格式，再做RTL/物理资格。

## 检查、失败和交付边界

- `python scripts/check_project.py`通过，仅管理结构；7合同测试含负数ties/零/极值、混合单位、早RQ、溢出、容量和packet负例。
- 全量独立核23592960 A编码、262144 Fraction W编码、136校准scale、1768320 INT64 partial、46080 Fraction归约/最终RQ；
  不导入生产数值函数。21个桥接Fraction极值/端点样本；其他S32桥接为向量重算，非逐元素独立Fraction。
- 13个科学文件两轮相同，含两次capture、numeric和service。producer所有1152配置资源/credit审计；
  独立4 witness共15259节点及144策略包络重算通过，不声称所有轨迹第二次保存/重算。
- 原型服务首次 Windows spawn 导入错模块导致失败，修复 path 后重跑；初测两个测试夹具的 NumPy标量提取/零时刻负例选择错误已修正。
  复核新增范围守卫后重新冻结源码/两轮服务，原始失败日志保留，不把它当测量失败或成功。
- 实际 rehashed 对象输出码篡改仍被 `near/shared RQ changed outputs` 拒绝；依赖篡改、packet丢失/乱序/截断/损坏均拒绝。
- 本机完整包594成员，7794102B，SHA256 `26283a1101e900fc8bf45b45666a00139b7a00b9e3e502ff87cfac3aa617f96b`，
  全144条件整数/metadata packet重放46080输出、13536包通过。
- Git交付**精选192成员**、2628498B，SHA256 `77c9ab60b61337b788498248f6b262ec1d50b8f76facf4430b72ed6a80c8c4fa`：
  四代表方案24条件可离线重放7680输出/249600partials/2016包，另含全部144数值摘要、1152服务摘要、4 witness和各原记录。
  **小包不能重算未包含条件的全部编码，也不能重算原始浮点校准**；完整9.15MB捕获/13.8MB整数NPZ留本机，按local-data-index索引，共享pending。

运行入口见[README](../../project/experiments/down_scale/README.md)。恢复：先核最新Issue/PR及SHA，
运行 `work/Liangruizhi/59/verify.py <results/index.json> --extract <新D目录> --output <新JSON>`。
本任务待审查合并，非done。用户随后授权服务器承接兄方批次，独立[Issue61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61)接续；不改变本轮实际本机执行事实。
