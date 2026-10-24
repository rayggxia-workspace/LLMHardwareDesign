# Issue66：完整消费者链 scale 传播与 Qwen3.5 连续状态整数化

2026-10-24（Asia/Shanghai），Liangruizhi。[Issue66](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/66) / [PR67](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/67)，base PR65@ec3008c665709fa3126d55719ad084d33af44428。实际结果与源码版本见[统一索引](../../project/experiments/scale_state/results/issue-66/index.json)，辅助原始记录见[work66](../../work/Liangruizhi/66/README.md)。本报告是局部数值与资源合同证据，不是完整模型质量、目标硬件周期或PPA验收。

## 1. 研究结论和划分的变化

本轮把旧16输出down切片扩成完整hidden2560，实际接上残差、完整RMSNorm及下一投影前16/8192输出；同时对真实非零初态、完整K128/V128的共享同一K的两个V头做连续整数重放。优先冻结的是数值单位、完整归约、状态提交和资源义务，物理同宏仍须同资源验证。

- M输出保留ACT8（逐通道base exponent + 每16输出tile的row delta）及ACT16候选，禁止在不同单位下直接加部分和。提前统一K128不是默认义务：本批省128B/row但增加norm及未最终RQ的next16误差；完整norm以后重新生成A8K128，不能把前一级ACT16的多周期乘法成本机械套到其后A8矩阵。
- V逻辑闭包收敛为ALIGN→残差→完整H统计→归一化→新A8。整数RMSNorm已给出可独立逐码验算的候选，sqrt/div和宽乘都显式计费。整行I64对齐结果20,480B超过V16KiB，原mixed sum+unit25,600B也超；必须明确两遍源读或付出spill，不能把Python数组当免费SRAM。
- R逻辑闭包保持完整K投影→delta→state更新→基于Snew形成output→共同commit/发布。S32显著降低本批短程舍入误差，但同范围S16/S32在旧256步窗都可饱和193次；不能用更多位代替范围管理。必须保留owner、sequence、position、scale/epoch、范围守卫和合法失败处理。
- R32KiB内K128×V32的S32 old+shadow正好32KiB，已无辅助空间。V16 tile、S侧shadow/额外流量，或有证明的预检查原位提交，仍是互斥候选，未决定独立R制造模板。

## 2. 输入、模型及复用边界

没有下载任何新模型。只读复用本人服务器已有Qwen/Qwen3.5-4B@851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a，按原接收记录重验文件SHA；模型源码SHA b4b17fe08d8d54da34a0fce78639666279ae7fd0a9e4ec06fce6602774707ca3。框架Python3.12.7、NumPy2.2.6、Torch2.10.0+cpu、Transformers5.20.2；CPU采集，不是GPU测量。模型24个linear-attention层、8个full-attention层；本轮不解封Phi，也不重复成员Issue55/63工程。

新calibration/evaluation为不同冻结文本，各B1、prefix128+cached32，token全部保留。消费者：layer3完整down(K9216,N2560)→加layer3.post_attention_layernorm输入对应的残差→layer4.input_layernorm(eps1e-6,有效gamma=1+weight)→layer4.linear_attn.in_proj_qkv前16输出。校准16行，prefill评价8行，cached decode评价32行。原始float消费者先重建并核对，完整hidden不等于完整8192投影/GDN或端到端模型。

状态采集layer0，Vhead0/1共享Khead0，完整K/V128；保存32次连续输入及33个真实R/conv边界，初态非零。512个相关conv channel采用源码实际4槽history，而非把3槽优化冒充原实现。原始NPZ：consumer-raw48,394,079B，state-raw9,252,980B；精确SHA和token见索引/capture manifest。

另无损导出PR36@2ada6cf6a61f5acff4b6052e81e15d20070dc0f3的旧真实状态。原qwen35-states.pt.gz SHA049c1cf4e81044fdc740dd1e65701a86293f31293d4b0ee2c554daecfef4e91a；export windows.npz8,912,088B/SHAfacb5a23145501a093deee792a3b87fa1a21bafb0566645ef9209ffeae088a5f。12窗为层0/14/30×终点2048/2049/8192/8193，六段256步、六段邻接1步；head0/31不共享同K组。短诊断只取同窗前32，长诊断用原完整256，均不拼接窗口。旧窗2×初态最大值的固定范围是迁移诊断，不是独立校准的生命周期范围证明。

## 3. 完整消费者：四种出口合同

所有profile固定同一down动态A8K128/W8K128、组INT32及受检完整I64对齐归约。静态ACT8和同物理范围ACT16具有相同上下端点（ACT16为[-32768,32512]）；另外为逐通道base+tile16 row-delta ACT8，以及该出口额外转K128统一单位。残差先FP32编译S32Q20，随后用checked I64对齐/相加。第一组实验RMSNorm为明确FP32桥；其后重新生成A8K128，再使用同一W8下一投影。

下表均相对本次native局部参考，相对RMSE以%表示；不能与旧16输出切片或其他模型百分比直接横排。

| 出口 | prefill down / next | decode down / next | outlet饱和 prefill / decode |
| --- | ---: | ---: | ---: |
| 静态ACT8 | 3.380 / 3.513 | 2.805 / 3.150 | 36 / 1 |
| 同范围ACT16 | 3.010 / 3.285 | 1.847 / 3.101 | 36 / 1 |
| base+tileδ ACT8 | 2.256 / 3.261 | 2.202 / 3.086 | 0 / 0 |
| δ后再转K128 | 2.256 / 3.285 | 2.202 / 3.244 | 0 / 0 |

范围不变时加位不能消除37次饱和；不事后扩评价范围掩盖失败。δ→K128使norm误差prefill约1.033%→1.408%、decode0.841%→0.994%。声明协议下整row包静态8/K128为2752B，tileδ2880B，ACT16为5376B（base驻留、64B包头/物理padding/FIFO分段按脚本）；提前转K128只省128B/row。这个数字是具体协议账本，不是必然链路收益或通用包格式。

独立receiver不用producer函数，验完整下一矩阵的K2560点积、部分和/对齐/最终RQ、全部8profile消费者和成本；原down采用独立选定数学见证，不能称全down每个MAC都由第三内核重算。真实NPZ改码并重写SHA后仍被数值检查拒绝。两轮全部科学文件字节一致。decode下一投影最终再RQ后，四profile误差依次3.4123%/3.4575%/3.4444%/3.5623%；不能从上游某项较优推断整个链单调更优。

## 4. 新整数RMSNorm闭包

norm01/02是首版账本；发现整行缓冲超限后，保持源码/数据不变留档，另冻结norm03/04，补齐两遍源读取、可选spill及fresh A8/Ae读写。所有NPZ在两版本间逐字节相同；新版成本不能追写为旧运行已计费。

候选把mixed sum对齐为checked I64，动态整行重编码X16；Z=sum(X16²)用U64。离线epsilon→U64Q40、sqrt(H)→U32Q20、有效gamma→S32Q20。Den=(Z<<16)+RNE(epsQ40*H,40+2eRow−16)，checked U64；运行32轮restoring isqrt与64轮restoring divide/RNE，求inv_U32Q30，再做S16×U32、gamma S32×S32及S32Q20输出。fresh A8K128直接从整数norm生成，不经FP32。零行捷径；超出Den/移位/格式域则拒绝并记录，不暗调参数。离线常量编译与上游FP32→整数边界仍明确。

8条件共160行、完整2560通道。相同X16输入下，整数norm对FP32 norm最坏相对RMSE约0.000050%；含X16重编码后，相对原FP桥norm最坏约0.05862%。下一投影对旧FP桥链的差别最大约0.4975%，说明小norm变化可能改变A8码；不能只报sqrt精度。整数norm链的next/native误差（prefill/decode）：静态ACT8 3.5158%/3.1621%，同范围ACT16 3.2538%/3.0920%，tileδ 3.3088%/3.0860%，δ→K128 3.3161%/3.2055%。prefill的相对排名改变，不选择单一精度赢家。

每行X16 5120B，gamma和norm32各10240B；gamma+norm不同时驻16KiB。两遍sum+unit源读51,200B/row，或另一条源读25,600B+aligned spill写读40,960B，不能两条都加。X16平方融合或再读也互斥。声明128bit/1RW动作下界融合平方6084beats/row，未融合6404；不是已调度周期，未含SFU依赖和全部争用。fresh A8 2560B/Ae20B，分包2752B。只有S8乘法时，S16平方/S16×U32/S32×S32分别以9/15/25基础积上界加shift/add/RNE计候选；不声称已经执行S8硬件内核或宽乘免费。独立receiver实际PASS 8条件，另核全部norm码、开方floor证书、Fraction除法/fresh A8、下一投影全部选定输出、账本与真实重写SHA负例。

## 5. 连续conv与R状态

### 格式与次序

conv校准每通道dyadic H8或H16/W8，4tap的完整INT32点积、真实history移位/追加；SiLU仍FP64桥。R输入q/k为S16Q15，V按cal每head S16 dyadic，beta U16Q15；decay比较D15/U16与D31/U32（都保留精确1）。S16/S32保持同一物理范围，S32指数比S16低16，不偷扩大范围。

顺序严格为：decay后RNE→完整K projection→V−prediction→beta后RNE→outer更新RNE→state SAT/guard→从新state形成output→状态/输出同版本共同commit发布。中间checked I64，完整K不能partial提前RQ/写state；8/16 chunk边界逐码相等，position/owner/epoch错误拒绝。commit SHA仅是软件接收见证，不要求硬件SHA单元。q/k共享不允许两个Vhead别名同一state。

### 真实新32步

| profile | 输出相对RMSE | final state相对RMSE | 输入/初态/state clip |
| --- | ---: | ---: | ---: |
| S16 D15 | 0.64384% | 0.49519% | 0 / 0 / 0 |
| S16 D31 | 0.64217% | 0.49579% | 0 / 0 / 0 |
| S32 D15 | 0.05666% | 0.02774% | 0 / 0 / 0 |
| S32 D31 | 0.05667% | 0.02767% | 0 / 0 / 0 |

D31/S32观察到62bit中间乘积，S16/D31可到46bit，宽乘/shift读写不得隐藏。S16/S32每head状态32/64KiB，两个头64/128KiB；全模型24×32heads的S32 backing为48MiB候选，不在S256KiB里免费放下。

### 长窗范围失败与decay分辨率

完整长诊断每轮48条件是24个256步+24个1步，不是48个全256。layer14/end8192中S16/D15 final state误差约0.509%（32步）→2.220%（256步）；S32/D31在256步state0.13687%、output0.12911%，本窗无sat。

但layer0/end2048四个格式都184次sat，end8192都193次；后者S32/D31 output误差只有0.04821%也仍是范围失败。短输出误差不能代替state range验收。当前没有自动rescale/epoch协议，不能宣布S32普遍可用。

layer14/end8192的最大decay约0.99999793649，D15把106/512编码成精确1（前32步3/64），D31没有；S32 output仅0.130894%→0.129105%，S16则1.77479%→1.77516%。这证明风险可观测，尚不证明D31普遍必需。需要明确误差预算、状态生命周期和wide成本后再选，保留两个profile。

### conv与R耦合

H8/H16在相同校准覆盖下都clip输入102、initial history14；W无clip。SiLU后RMSE约0.7078%/0.6525%，不是加位就扩大范围。将conv8/16真实量化输出送入R(S32/D31)，32步output约0.9629%/0.8598%、final state约0.7632%/0.5530%；同一conv后FP64参考与整数R的新增输出误差约0.0583%/0.0628%。第一步state误差约11.73%/11.67%，不能只报较好的final。q/k L2归一化、SiLU、a/b→g/beta编译/门控以及R内部GatedRMSNorm仍有FP桥，不能称整条全整数GDN。

## 6. 实际服务器执行、独立接收与失败

主数值实验及全量独立接收走c96/node13的lrz-i66-* Slurm；除采集24CPU外每job2CPU，OMP/MKL/OpenBLAS=1，独立不可覆盖目录。原模型只读，未中断其他成员89448。时间是作业墙钟，带转存/观察者，不能作推理benchmark。

| job | 执行内容 | 条件/时间 |
| --- | --- | --- |
| 90059 / 90060 | 原状态无损导出 / 新真实采集 | 22s / 90s |
| 90061 / 90062 | conv两轮 | 每轮4条件，1s |
| 90063 / 90064 | 完整消费者两轮 | 每轮8条件，15s |
| 90065 / 90066 | 新连续R两轮 | 每轮8条件，8s |
| 90067 / 90068 | 旧同窗32/1步诊断两轮 | 每轮48条件，19s |
| 90069 / 90070 | conv→R耦合两轮 | 每轮2条件，2s |
| 90072 / 90073 | 旧完整256/1步诊断两轮 | 每轮48条件，126s |
| 90077 / 90078 | 整数norm首版两轮 | 每轮8条件，5s / 4s |
| 90079 / 90080 | 整数norm新版账本两轮 | 每轮8条件，5s / 5s |
| 90071 / 90074 / 90075 / 90076 | 独立conv / R / 消费者 / 扩展接收 | 0 / 41 / 7 / 122s |
| 90081 / 90082 | 独立新版norm / 归档 | 7s / 21s，COMPLETED0:0 |

上表90059–90082全部COMPLETED0:0；Slurm账本已读回，提交和完成分开留档。准备阶段Windows CRLF/SSH建连超时失败原记录保留，未启动数值作业；改UTF8 bytes、新phase、只重试确定未连接的超时。日志、命令、各phase源码commit/SHA、输入及产物SHA完整留档。

独立conv核65,536个4tap点积；主R核8条件、8,388,608 decay RNE和同数outer RNE及各65,536个完整projection/delta Pythonint RNE、65,536个output Fraction RNE值；扩展核2个耦合全32步+接收前固定3个256步见证（含193次sat失败），不是48个长条件全量由第二内核重算。消费者/norm均完整8profile接收，二轮文件SHA核对，所有receiver不导入producer。实际重写SHA的坏acc、坏state/commit/输入、坏consumer和坏norm保留并被拒绝；SHA通过不等于数学通过。

## 7. 交付、复现与剩余最小分叉

小精选包含两个完整32步R编码轨迹、两个decode全hidden消费者路径、来源/源码/全量指标/独立接收JSON；已在本机独立重放这2R+2consumer并通过，也可在另一台电脑校验重放，但不代替原始模型采集、完整down/compiler或整数norm验算。全量capture、所有条件NPZ和两轮日志在本次本人服务器目录及完整ZIP，仓库不收模型权重或大中间张量。准确位置/大小/SHA见统一索引。实际执行的管理结构检查、原164项业务测试及新增59项边界测试均通过，日志与命令在work66；[模块README](../../project/experiments/scale_state/README.md)说明源码/输入绑定和接收边界。

后续只保留会改变制造边界的实验，不扩模型品牌/长度矩阵：

1. 固定当前整数profile和同一库存，比较V归一化两遍读/流式gamma、R V16 vs V32+S-shadow/合法原位提交的有限端口调度；加入相同FFN/attention竞争，核全链buffer/credit/失败原子性。当前字节下界不是完成周期。
2. 冻结R范围/重定标epoch或合法回退合同，用独立校准生命周期验证；保留真实饱和失败。整数SiLU/QK norm/gate候选需明确LUT/乘除/端口后才能去掉FP桥。
3. 用适用RTL/物理资产校准wide SFU、布局、连接端点和布线，与成员Issue55/63协作接收。M+A同宏、R独立、近M RQ及端到端收益均未定；Phi继续封存到策略/阈值冻结之后。

交付PR待指定审查人及合并，Issue非done。登记management-hub PR5 pending；无board.json及可用Projects字段能力，看板事实unverified、同步pending待管理员。不得将本地/服务器执行、远端上传、审查合并和物理验收混为一项完成。
