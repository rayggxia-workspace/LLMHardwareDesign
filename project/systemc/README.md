# 七类 Block 的 SystemC 行为模型

任务 [#145](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/145)，依据 [#143 / PR #144](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/144) 的七宏设计和 `docs/BLOCK_V2.md`。M/N/E/G/R/S/T 均有可执行代码，并通过真实 SystemC 调度器连接。不是只含声明的架构草图。

**抽象层级：无时钟的事务级功能模型。** 一条命令对应一个操作，省去 RTL 的逐拍 FSM、流水寄存器和发射顺序；保留定点格式、舍入/饱和/拒绝、有效位、有限存储、状态提交及事务顺序。适合解释电路职责、开发上层调度和构建数值参考；不能据此预测周期、面积、带宽或宣称通过 RTL 等价验证。没有新增物理实现或改动已有 RTL。

## 从哪里看

| 文件 | 对应计算/状态 |
|---|---|
| `include/blocks/m.hpp` | M 操作数双银行、分块点积、分段缩放与行级提交 |
| `include/blocks/n.hpp` | N 长向量统计、EXP、Softmax/RMS/L2、40选8 |
| `include/blocks/e.hpp` | E 八路逐元素算术、RoPE、S8打包 |
| `include/blocks/g.hpp` | G 两路查表/插值激活及门乘 |
| `include/blocks/r.hpp` | R GDN/SSM、四抽头卷积、双银行状态与提交/撤销 |
| `include/blocks/s.hpp` | S 16KiB工作存储及分块供数事务 |
| `include/blocks/t.hpp` | T 6KiB结果交接及消费/释放 |
| `include/blocks/modules.hpp` | 七个真实 `sc_module`；每块一个 `SC_THREAD` |
| `include/blocks/common.hpp` | 带符号RNE、范围检查、整数平方根、运输类型 |
| `examples/softmax_trace.cpp` | 257元素 `S → N → T` 演示，逐批打印状态 |
| `tests/block_tests.cpp` | 数值、边界、存储/状态协议和SystemC组合测试 |

数值及操作合同冻结于本地设计提交 `9cc23ff32cf7a57c5eadbfccc8bfb37438f3643d`，其中 `82d34d0f` 已将 Softmax 更新为**非负 S16 Q1.14**。开始任务时 PR #144 的公开头仍为 `d739fc46992ecb95cfab1a0f58ba1467f172cbb0`，其旧 UQ0.16 Softmax 不是本模型合同。`source_manifest.json` 记录实际读取来源及规范化SHA-256。系数整数直接从这些设计的SV表导入，包含来源关系；它们不是独立数值真值。提交期间上游已发布 `341d6f938564af54268ab87fc41c05a002297d80`，已纳入本分支；全部RTL与冻结9cc23ff3一致，新Q1.14合同现已发布。设计继续变化时需显式审查模型合同，不能仅更新版本号。

## 编译运行

要求 Linux/WSL、GCC或Clang的C++17支持（局部宽数值检查用 `__int128`）、CMake≥3.16和真实SystemC 3.0.1。MSVC暂不支持。系统已有相同C++标准构建的SystemC时可以直接配置；没有时使用本仓库的本地依赖脚本，依赖不进入Git：

```bash
# 在仓库根目录，Linux/WSL内执行。只下载和编译项目本地依赖，无需sudo。
bash project/systemc/tools/build_systemc.sh
cmake -S project/systemc -B project/systemc/build \
  -DCMAKE_PREFIX_PATH="$PWD/.systemc-deps/install" \
  -DCMAKE_BUILD_TYPE=Debug -DBLOCK_SANITIZE=ON
cmake --build project/systemc/build -j 4
ctest --test-dir project/systemc/build --output-on-failure
project/systemc/build/softmax_trace
```

依赖使用[Accellera官方SystemC 3.0.1](https://github.com/accellera-official/systemc/tree/3.0.1)，按[官方CMake安装方法](https://github.com/accellera-official/systemc/blob/3.0.1/INSTALL.md)构建。脚本校验下载归档SHA-256，不安装全局软件。实际检查记录见 `work/YUZE-LU/145/README.md`。

## 中文源码注释的阅读顺序

每个模型头文件顶部说明数据流与抽象边界；Command旁写字段用途、合法范围和原始Q编码；成员旁写存储容量、地址计算和有效位；execute分支旁写操作前提、状态更新及错误后保留什么。M/N/R的重要运算还说明移位常数、舍入点和提交边界。

公共数值函数、SystemC线程/背压、系数表、测试、Softmax示例和构建工具均有中文注释。系数表注释由生成器维护，重新生成不会丢失。JSON清单保持合法机器格式：source_manifest记录设计源与发布版本，model-file-sha256记录当前模型文本哈希，不把说明塞进JSON造成解析失败。

## 通信和通用约定

每块有输入 `sc_fifo_in<该块Command>` 和输出 `sc_fifo_out<Reply>`。调用方明确创建队列容量；例子和测试全用深度1。可单独调用 `Engine::execute()` 验证算法，也可实例化 `blocks::M` 等模块进行并发仿真：

```cpp
blocks::M macro{"M"};
sc_core::sc_fifo<blocks::MCommand> commands{"cmd", 1};
sc_core::sc_fifo<blocks::Reply> responses{"rsp", 1};
macro.commands(commands); macro.responses(responses);
// 在SC_THREAD内 commands.write(cmd); auto rsp = responses.read();
```

每个模块保留至多一个正在等待写出的响应。响应FIFO满时阻塞工作线程，输入FIFO再满则上游阻塞，恢复后保持顺序。命令的 `tag` 原样回传。**Reset是顺序事务**：不能异步取消已经排队的响应；系统级复位须由调用方协调排空队列。没有额外的异步复位端口。

`Reply.error` 表示事务被拒绝/计算失败，`saturated` 表示合同允许的数值夹取；两者不能互换。`lane` 是最多8个主机S64结果容器，`bits` 是最多512位运输容器，低字节/低lane在低位。它们便于解释不同宽度端口，**不是对物理端口或响应寄存器位数的重新定义**。无效操作返回错误；原RTL中未ready的握手尝试在此通常立即拒绝，而非永久等待。

## M：分块计算引擎

```text
LoadA/LoadB → A/B各1KiB双银行
           → Execute(1..8行, 1..4个K8块, 1..8列)
           → 每行局部点积 → 两行×8个S40部分和
           → 有符号S16系数×2^left_shift → S64行候选
           → 本行全8列通过检查才写64份S64结果
           → ReadFull / ReadFinal(RNE与饱和)
```

A/B独立装载。A一次8个S8/S16，B一次64个S8或32个S16（后者先half0再half1），S16元素在主机中按有符号整数解释。`Execute.clear=false` 把新段缩放后加到原S64结果，不追加到旧S40部分和；K256由8个K32事务实现。S8/S16的RTL数位分解在本层用精确整数乘法代替，数值目标一致；不模拟64个乘法器的发射拍数。

M的失败为**行原子性**：`failed_rows` 是8位失败掩码，失败行保留旧结果，其他成功行可提交。`ReadPartial` 仅允许最后仍驻留的两行。`ReadFull` 返回一对S64；`ReadFinal` 一次4个结果，可选8/16/32位、右移0..63、RNE后饱和。`InvalidateBank` 保留结果，`InvalidateAll` 同时使结果失效。

## N：统计状态与外部回放

```text
Begin → Stats(每次1..8个S16) → Finalize
 Softmax: Exp(回放原始x) → FinishExp → SoftReplay(回放EXP)
 RMS/L2:                            → NormReplay(原始x,gamma)
```

只有一个长度≤65535的统计上下文：S32 sum、U48 sumsq、S16 max/min、统计/EXP/回放计数、U32 EXP和及U32因子。**N不存整条向量，也没有旧V的256元素缓存。** 一条命令内部两lane多周期处理的时序在这里被折叠。最大值只会随着已接受的Stats数据更新。

Softmax输入Q5.10；局部 `EXP(x-max)` 使用[-16,0]、1/64网格的UQ1.15系数及RNE插值。EXP值必须保存到S或调用方存储再回放。`FinishExp` 算 `factor=floor(2^44/exp_sum)`，输出 `RNE(exp_raw*factor/2^30)`，夹在0..16384，对应非负S16 Q1.14。最大值扫描完成前不能开始EXP；EXP总数达标前不能求最终因子。

RMS先取 `floor((sumsq*2^16)/count)`，L2不除count；再加 `epsilon*2^16`，取floor整数根；`factor=floor(2^38/root)`。epsilon是原输入整数平方单位的正整数，gamma为Q5.10，输出 `RNE(x_raw*factor*gamma_raw/2^30)` 并S16饱和。

`ReadStats.lane[0..7]` 顺序为count、max、min、sum、sumsq、exp_count、exp_sum、replayed；后3项是调试便利字段，原RTL响应不全部打包输出。`ReadFactor` 在lane0返回因子。`TopBegin/TopLoad/TopSelect` 使用独立40项(score:S16, ID:U16)状态；每次装≤4项，选1..8项，分数降序、ID升序；输出ID，不进行专家数据搬运。

## E 与 G

E输入三个8×S16数组；支持ADD/SUB/MUL/FMA/MAX/MIN/SELECT/左移/算术右移/RoPE/RNE右移/ABS/S8打包。MUL/FMA/RoPE在完整中间值上右移RNE一次，再S16饱和。FMA的C处于乘积单位。RoPE相邻配对，B偶数为cos、奇数为sin；不含任意重排。Pack8把结果紧凑放入 `bits[0]`，并在lane中返回带符号结果。

G每事务两路Q5.10输入，SiLU/GELU_tanh/Softplus输出Q5.10，Sigmoid输出Q1.14。插值表与RTL共享相同整数系数；可选门值Q5.10，门乘后输出Q5.10。域外规则和RNE保留。未模拟其四级流水/II=1，也不把两lane当成8lane。

## R：状态反馈与显式提交

```text
Open(tags,length) → 装active状态、K/Q或B/C、当前输入及参数
 → Execute(GDN/SSM): shadow衰减 → 预测/注入 → 更新 → 读出
 → ReadOutput，active仍不变 → Commit(tags,next_position) / Revoke
```

两份2048×S32状态银行，各8KiB，最多256×8状态矩阵；K/Q各256×S16，历史3×8×S32，4×8×S16卷积权重。没有第三份完整SSM因子存储：`DecayRow` 写入shadow，执行时读因子后覆盖为候选状态，每次SSM必须重新装载因子。`StateRow/DecayRow/History` 将原128位半行端口合并成8lane事务，`Key/Query` 按元素装载；这改变事务包装，不改变运算格式。

GDN：`Sd=RNE31(S*alpha)`；`p=RNE14(sum(Sd*K))`；`e=RNE31((X-p)*beta)`；`Snew=Sd+RNE14(K*e)`；`Y=RNE14(sum(Snew*Q))`。SSM：`Sd=RNE31(S*decay_element)`；`Snew=Sd+RNE14(B*inject)`；`Y=RNE14(sum(Snew*C))+RNE16(X*skip)`。K/Q/B/C为Q1.14，alpha/beta/逐元素decay为UQ1.31且≤1；skip为S32 Q16.16；inject由外部事先计算。各S32边界溢出则失败，不自动饱和，active不改变。

卷积固定四抽头、当前值加过去三个值，权重可加载；结果RNE14，历史候选也需Commit。它不是任意长度通用卷积。成功的卷积历史可以与随后状态计算一起提交；后者失败不隐式丢弃已有历史候选。Commit核验owner/epoch/position，交换状态银行、提交历史并epoch+1；epoch最大值拒绝提交。外部投影、归一化和激活仍由M/N/E/G承担。

## S 与 T

S固定1024×128bit=16KiB、四bank交错映射，窄地址低2位选bank；`ReadWide.address` 是0..255的宽行号，一次读取连续4个窄字。写响应回显数据。未初始化读取有显式软件诊断，真实RTL对这些字节没有初始化值保证；Reset不清空存储。

`LoadBegin` 冻结bank、行数、K块数、A/B格式、对齐基址和B复用标志；`LoadNext` 依次返回B512半块或A128行块，最后一拍 `last=true`。`lane[0..4]` 为A/B类型(0/1)、bank、A行号/B半号、tile、宽格式。A按每tile的4行宽组布局，B按S8一宽行、S16两宽行布局。例子见测试的S→M连接。为保持接口简单，模型在供数期间拒绝普通存取，并逐拍请求下一条运输事务；**不模拟RTL两项A队列/一项B槽的重叠读、同时A/B发射和仲裁优先级**，不能用本模型给供数吞吐结论。

T固定384×128bit=6KiB，状态为Empty→Fill→Sealed→Reading→Release→Empty。Begin指定words/owner/generation，顺序Write填满后自动Sealed，Commit后可Peek/Take；Peek不前进，Take消费一个字，末字后必须Release。只允许填充/封口阶段Revoke。owner/generation是记录标签，不能宣称T已有跨主体认证。错误长度和非顺序Write置sticky协议错误，可通过Status检查，Reset清除错误/控制并隐藏旧数据。同步读等待状态在本层折叠，保留一个held字的语义。

## 已测范围与局限

测试含：四种M格式和尾K、K256分段、行级溢出与保留；E全部13操作独立整数参考；G全S16域与函数误差界；N最大65535元素、257元素最后才到达新最大值、精确倒数/整数根、RMS/L2和TopK；R两种更新、卷积、tags、提交/撤销、失败保持；S容量/布局/供数和T完整384字批次；真实SystemC的七模块组合及有限FIFO背压。另有257元素S/N/T逐批轨迹。

**尚未进行RTL协同仿真或逐事务形式等价证明。** 测试通过说明这些模型在所列测试下自洽，不替代PR #144原有的RTL、物理和模型精度验收。模型无时序标定、功耗模型、M11/M12互联、任意多上下文调度或完整LLM运行时。外部测试使用的大向量属于调用方，不代表片上S能容纳超过16KiB的数据。
