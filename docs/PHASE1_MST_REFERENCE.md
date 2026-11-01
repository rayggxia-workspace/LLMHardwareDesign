> 2026-11-01 P2更新：用户要求同步最新PR144并开始第二步；当前14核心RTL采用707878621b2add4ed218b8c43df2e95c9a56e2ba，仅R相对643变化，七顶层接口不变。新增MST控制原型及实际验证见[第二步报告](PHASE2_MST_IMPLEMENTATION.md)。以下P1/既有研究保留原版本与证据边界，不将旧回执重标为新源通过。

# 第 1 步：M/S-loader/T 有界整数参考与显式向量

本交付为 Issue151 / PR152 七步路线中第 1 步的参考子包。研究输入固定 `343f4d4775ffab61b2ed2df13de243cc659c157a`；原生叶宏固定 `643c6012a11cbf461146ac40fbf61485223fe946`，从本轮 `integrated/project/rtl/` 逐文件读取并核对字节。没有自动纳入 PR144 最新提交。日期：2026-11-01，Asia/Shanghai；负责人 Melodydt。

本地已形成纯 Python 3.7 参考、不可由参考输出回填的 literal 预期向量、复现脚本和实际回执。**本轮没有实现系统 RTL，没有运行 RTL 仿真、SystemC、推理、综合、EDA 或服务器；Python 数值/协议检查通过不等于真实引脚握手、整模型或硬件通过。**

## 1. 文件与使用边界

| 文件 | 用途 |
|---|---|
| `phase1_mst_reference.py` | M 原子整数/有效性模型；S loader 合法描述符、读请求顺序与载荷布局模型；T 行为时钟步进模型 |
| `phase1-mst-vectors.json` | literal 整数、响应字、描述符、布局及 T 时序步骤的预期输入；包含第 2 步固定最小切片 |
| `verify_phase1_mst_reference.py` | 只读取来源与向量，执行断言、独立整数/精确有理数对照并写回执；不修改预期向量 |
| `phase1-reference-verification.json` | 实际 Python 版本、源文件/工具/向量 SHA-256、Git blob SHA-1、分类断言计数、限制与待执行 RTL case |
| `reference-local-checks.json` | 两次实际命令、回执字节一致性、管理结构/编码检查及交付文件 SHA-256 |

M 参考的调用在事务边界串行执行：`command()` 是原子操作，调用方视为已经等到该命令完成。它支持 op4 配置、op10 执行、op3/op5 读取、op6/CLEAR_ALL、op11/CLEAR_BANK 的所列语义；保留实际 A/B 元素、格式和有效性。**它没有 M pipeline、ready/valid 周期、同拍优先关系、bank 并行调度或 op12 有限 partial 槽生命周期模型。** op12 明确抛 `NOT_MODELLED`，不能把诊断 Python trace 当成 native op12 随时可读。返回对象中的 `partials_s40/fault_reasons/rounded/lanes_s32` 是 Python 诊断字段；真实 M 响应仍只有 data128、error、saturated。

loader 参考只生成真实描述符检查结果、S512 读地址顺序、A128/B512 内容及标签；**不模拟两个 A queue、一个 B slot、S 宽/窄仲裁或传输周期**。S 字典只是已初始化测试载荷，Python 读取缺失字会报 `UNINITIALIZED_FIXTURE`，这是防止测试误用未知数据，**不是 S 硬件具有未初始化检测或错误响应**。没有新增 S 地址空间或外存行为。

T 参考的 `tick()` 返回本拍边沿前输出 `before`、本拍接受事件 `fires`、边沿后状态 `after`，可明确描述首读气泡及停顿保持。这是按源码写出的行为模型，**尚未与 RTL 波形比较，不宣称周期等价或 RTL 握手通过**。初始对象相当于协调 hard reset 后的架构状态；不建模复位前未知寄存器/亚稳态/X 传播。所有端口输入用范围内的 Python 整数（含 0/1）；超出引脚宽度的输入在 Python 入口拒绝，不能据此声称真实 RTL 检测到了截断前的超宽地址。

## 2. 数值参考与原生合同

### M：段内 dot、尺度、逐行提交、读出

每个 op10 只含 1..8 行、1..8 活跃输出列、1..4 个 K tile；最后 tile 有效 K 为 1..8，总段长 `8*(tiles-1)+last_k <=32`。A/B 可独立选择 S8/S16。inactive N 和末 tile 的无效 K 不参与 dot。A/B 载荷有效/格式检查、追加所需旧行 valid 和相同 `active_n` 均按 native 条件检查。

S16 输入按 `[v[6:0], v[13:7], signed(v[15:14])]` 三个有符号 radix-128 数位展开，位权分别为 1、128、16384。它不同于两个 unsigned byte；例如 `-1=[127,127,-1]`，`-32768=[0,0,-2]`。参考逐 tile/a-digit/b-digit 重放 S40 partial 累加和 wrap/溢出记录；另用独立的原始整数乘加检查四种 A/B 格式。合法 dot 的精确结果界至多 `32*32768*32768=2^35`，这不是 S64 尺度对齐或多段追加的免溢出证明。

段缩放是 `partial_S40 * signed_factor_S16 * 2^left_shift`，`left_shift=0..31`；此时不做 RNE。op4 的 factor 允许零和负数，且只有全局一份 factor/shift。op6/CLEAR_ALL 使输入/结果失效，**不恢复 factor/shift**。外层还必须证明不同段、层、专家的身份和共同数值单位；native 描述符不携带这些身份。本参考只操作 raw integer，没有把任何模型统一假定为 Q10/Q14。

S64 对齐或与旧结果相加溢出时，该行全部 8 列保留旧值和旧有效状态；其他成功行仍提交。即使 `clear_result=1`，失败行也不会先清成零。首次执行失败且无旧行时，读该行仍返回 error。EXEC 返回低 8 位故障行 mask、`error=(mask!=0)`、`saturated=0`；它不是整条事务回滚，也不是饱和算术。不能盲目重试一个部分行已提交的 append。

op3 每次返回两个原始 S64，低 64 位对应较低列；op5 对四个 S64 做算术右移和 RNE，再 clamp 到 S8/S16/S32，结果仍是**四个 sign-extended S32 容器**。RNE 对负数采用 floor quotient 和非负余数，tie 取偶；例如 `-7/2→-4`、`-5/2→-2`、`-1/2→0`。clip 只置 `saturated`，不置 `error`。若以后将 op5 容器送给 S16 消费者，仍需根据已授权宽度/尺度做字段抽取或转换；第 2 步最小 profile 先直接保留 op3 S64。

源码证据：[M L29](../project/rtl/block_v2/block_v2_m.sv#L29) 的数位展开、L48–62 的描述符、L90–104 与 L163–193 的缩放/逐行提交、L198–223 与 L240–248 的命令/读出。完整文件 SHA 见下表和 JSON 回执。

### S loader：字地址、整容器、n-major、half

base 是 S 的 **128bit 字地址**（每字 16B），A/B base 都须四字对齐。rows=1..8、tiles=1..4；A 范围为 `a_base+tiles*(rows>4?8:4)<=1024`；非 reuse 的 B 范围为 `b_base+tiles*(b_wide?8:4)<=1024`。恰好等于 1024 合法，超过非法。`reuse_b=1` 跳过 B 范围/数据读取，**仍要求 b_base 对齐**；它不检查旧权重版本、模型层或专家身份。

每 tile 的 A 预留 4 字或 8 字，每个真实行占完整 128bit 容器；S8 仅使用低 64bit，并不是把两行紧凑放一字。B S8 每 tile 占四字，单 B512 beat；B S16 占八字，half0/half1 各一个 B512 beat。B 元素按 `8*n+k` 排列，因此 S16 half0 是 n0..3 各自八个 K，half1 是 n4..7。宽读拼接 `{S[word+3],...,S[word]}`，按每 tile 先 B 后 A 的请求顺序；A/B 实际退休可并行，参考不规定其相对握手周期。

描述符原生检查不禁止 A/B 范围重叠，不禁止 reuse 错权重。向量保留“重叠仍 native 合法”和“reuse 跳过越界 B 读取”例子，防止参考凭空增加硬件合法性检查；系统编译/分配器仍须证明数据身份与存活性。非法 native 描述符返回 done_error；超宽 Python 地址 1024 不存在于 10bit 引脚域，单独标注 `PORT_DOMAIN`。

源码证据：[loader L31](../project/rtl/block_feed_v1/block_feed_loader.sv#L31)、L47–59、L72–108；[S L11](../project/rtl/block_feed_v1/block_feed_s16k.sv#L11)、L24–37；[S macro L20](../project/rtl/block_feed_v1/block_feed_s_macro.sv#L20) 的真实 loader/storage 接线。

### T：批次生命周期与停顿

BEGIN 只在 EMPTY、words1..384 接受；WRITE 必须从 index0 逐字顺序，最后一字进入 SEALED；COMMIT 握手后进入 READ_REQ，下一边沿同步取首字，再进入 READ_HOLD；连续 TAKE 可每拍前进一个字，末字 TAKE 后进入 RELEASE，必须再 RELEASE 才能 BEGIN。owner/generation 只登记，不认证请求者；release 不清这两个标签或 word_count。

行为模型保留实际错误边界：EMPTY 时非法 BEGIN 长度、FILL 时无 revoke 的错误 WRITE index 会置 sticky `protocol_error`；reset 才清错误。未 release 时 BEGIN、提前 COMMIT/RELEASE、提交后的 REVOKE 不握手，native 不自动为这些事件新增错误。FILL/SEALED 的 REVOKE 优先于 WRITE/COMMIT；提交后不能撤销。stall 时有效 read_data/index/last 保持。payload 不因 reset/release/revoke 清零，未完成新批次不会发布旧内容。

源码证据：[T L27](../project/rtl/block_v1/transaction6k.sv#L27)、L41–69。

## 3. 第 2 步直接复用的最小 MST profile

固定 `S8×S8, rows=1, tiles=1, K=8, N=8, bank=0, factor=1, left_shift=0`；路径为 S 内 loader→M EXEC→op3 四个原始包→S 四字→T 四字。没有 E/G/N、S16 紧凑打包、溢出重试、并发上下文或外存搬运。系统有外存，本轮没有对外存接口/调度建模，不据此施加产品永久禁外存。

| S 字地址 | 内容 | 128bit 字编码 |
|---|---|---|
| 448 | A=`[1,-2,3,-4,5,-6,7,-8]` | `0000000000000000f807fa05fc03fe01` |
| 449..451 | A 组 padding | 全零 |
| 452 | B n0 的八个1、n1 的八个2 | `02020202020202020101010101010101` |
| 453 | B n2 的八个3、n3 的八个4 | `04040404040404040303030303030303` |
| 454 | B n4 的八个5、n5 的八个6 | `06060606060606060505050505050505` |
| 455 | B n6 的八个7、n7 的八个8 | `08080808080808080707070707070707` |
| 456 | 结果列0/1 = −4/−8 | `fffffffffffffff8fffffffffffffffc` |
| 457 | 结果列2/3 = −12/−16 | `fffffffffffffff0fffffffffffffff4` |
| 458 | 结果列4/5 = −20/−24 | `ffffffffffffffe8ffffffffffffffec` |
| 459 | 结果列6/7 = −28/−32 | `ffffffffffffffe0ffffffffffffffe4` |

A 的和为 −4，B 第 n 列的每个系数为 n+1，所以八结果手算为 `-4*(n+1)`。每个结果字低 64bit 是较低列，高 64bit 是下一列。12 个 S 字是实际固定保留 **192B**；T 另保留4字64B，新增控制/响应保持寄存器另计，不能算进这192B就假定已有。

原生命令和控制次序如下（同样写入 JSON，供 P2 testbench 读取）：

1. 初始化 S448..455；每个普通写请求必须消费写 ACK，ACK 载荷是写入 din，不能当成新张量。
2. M `op6/index0/data0` 检查成功 ACK；显式 `op4/index0/data1` 配 factor1/left0，检查 ACK。
3. loader=`bank0,rows1,tiles1,a_wide0,b_wide0,reuse_b0,a_base448,b_base452`。请求宽地址113（B）然后112（A）；等待完成 done_error0 并消费 done 后才启动 M。M clear/config 与 loader 的最小实现应按已冻结控制序列串行，不能边 CLEAR_ALL 边盲发载荷。
4. M `op10/index0/data0x9884`；等待 ACK，要求 error0/faultmask0。此响应是完成状态，不写成结果字。
5. `op3/index0..3/data0` 逐包读取四个原始 S64 对。第 i 包写 S456+i，保留 M 响应直到真实 S 请求接受，并排空写 ACK；所有错误归属由新增顶层控制实现。
6. T BEGIN `owner0,generation1,words4`，随后读 S456..459，按 index0..3 顺序写 T，最后写后等待 SEALED；COMMIT，等待首字 read_valid，接收四个 word，末字 TAKE 后 RELEASE。

JSON 的 `minimal_mst_profile` 是该切片的单一 literal 输入契约。Python 组合检查只证明所列数值和行为意图互相吻合；上述真实接口间保持/信用/ACK 控制尚未实现和验收。

## 4. 实际检查与独立性

执行环境为 CPython **3.7.0**、Windows 10 build 26100，仅标准库。验证脚本严格核对五份原生源 SHA；固定向量不由参考输出重新生成。实际通过 **527124 条 Python 断言**，计数是循环内比较次数，不是 RTL case 数、opcode 全覆盖率或系统通过率。

| 检查组 | 实际范围 |
|---|---|
| literal M 数值例 | 九种 EXEC 场景：S8 尾 K10/2行/N3/负 factor、S16 极值、两种混合精度、多段合并、单行溢出而另行成功、clear 对齐溢出保旧行、末列溢出保全行、负缩放到 S64_MIN 后再溢出 |
| literal 读出 | 负 tie、S8/S16/S32 clamp、最大 right_shift63；四 S32 容器及原始双 S64 的完整128bit字编码 |
| 独立精确 oracle | `Fraction.__round__` 对照 −32768..32767 在 shift0..6 的458752例，另1608例 S64 边界；不使用 float |
| 独立 dot oracle | 四种 S8/S16 组合×四种形状（含8×8×32）共16 job，与直接 raw 整数乘加对照；固定 seed151，仅用于可重复有界测试 |
| 全 S16 数位 | 65536 个 raw signed 值的 radix-128 重构；另有七个手填数位预期 |
| M 合法性 | reserved 位、rows/tiles/K/N 范围、append 无旧结果/宽度不符、未加载/格式不符、错误读字段、op4 非零 index/保留位、B half1 顺序、clear 不清尺度、首次溢出不创建 valid 行 |
| loader | 十四个描述符例（含一个引脚域外输入）、末地址1024、复用、重叠、S8 A 容器和5行 S16 A、B 两 half 的 n-major literal 布局 |
| T | 三个显式步骤序列，共30拍；BEGIN/顺序WRITE/COMMIT/首读/停顿/未 release 重入/revoke优先/sticky错误，以及384字容量端点的顺序填充/读取 |

RNE 使用标准库精确有理数 round、dot 使用原始整数乘法、布局使用独立 byte 编码；它们不读取 M 数位展开或参考的 pack 函数来生成预期。literal JSON 内的响应字、整数和每步 T 状态都是固定期望。Python 模型与测试仍可能共享对源码的理解偏差，因此第 2 步必须把同一向量驱动真实 RTL 并对响应/状态逐项比较。

复现本地子包：

```powershell
python -B -X utf8 work/Melodydt/151/verify_phase1_mst_reference.py --source-root . --output <独立回执.json>
```

整合进正式 checkout 后，脚本及向量保持同目录，使用 `--source-root .`；`--output` 可指向独立临时目录，避免重算覆盖正式回执。脚本不依赖本机绝对路径，不扫描 ref-project、不访问网络、不自动下载工具。`-B` 避免产生 pycache。

## 5. 冻结来源与交付限制

所有来源 ref 均为 `643c6012a11cbf461146ac40fbf61485223fe946`；字节 SHA、Git blob SHA-1、原始长度、行号和固定链接已由验证脚本实际重算写入 `phase1-reference-verification.json`。

| 路径 | bytes | SHA-256 |
|---|---:|---|
| `project/rtl/block_v2/block_v2_m.sv` | 12996 | `5825adcd3364d4315afd1aa4addae85379fb36df2802ca8ab60026e0b0f44d1e` |
| `project/rtl/block_feed_v1/block_feed_loader.sv` | 5019 | `3b8d4643519141232a7297afcf966899cfae3de67be0eba069d54116e66de356` |
| `project/rtl/block_feed_v1/block_feed_s16k.sv` | 1737 | `262b193ae007d9a26f310087a6e37e0921f9468cd9884530d8f527d7190f3603` |
| `project/rtl/block_feed_v1/block_feed_s_macro.sv` | 2141 | `3d105bf4605076e5f806b45c545cb5fdd5658a23d82f0ea4b58c0cd8d2ce18c8` |
| `project/rtl/block_v1/transaction6k.sv` | 3397 | `0b07833dffc28169ba70beafabad3d7503a31989f46fcbdcf03b15ba9026b3ef` |

本参考原在独立目录准备，本次正式交付不改叶宏源码、真实八模型形状或量化。管理结构检查 `python -X utf8 scripts/check_project.py` 通过，仅反映管理文件结构。正式整合命令、上传和PR/Issue/看板状态由phase1-checks及PR152回执记录，不将独立准备阶段的本地回执误写为在线状态。

第 2 步待完成：新增最小 MST 顶层/测试夹具，把 ACK 归属、响应保持、S 写入与 T 租约做成真实控制；在实际引脚独立施加背压，比较本向量；再验证非法描述符、partial-row fault 恢复和协调 reset。M 输入 bank 锁定、M 响应冻结、S 宽窄仲裁、loader queue 活性、T 实际 hold/II、RTL/整数参考等价仍全部**未执行**。外存接口、整模型编译、量化质量和物理资格仍未验收，合法的缺实现能力没有因本轮小切片而被排除。

正式当前回执为work/Melodydt/151/phase1-reference-verification.json与phase1-checks.json；reference-local-checks仅保留于独立准备目录，记录准备阶段的两次运行，不作为远端验收。
