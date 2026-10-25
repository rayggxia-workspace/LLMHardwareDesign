# Issue102：完整 GQA 整数注意力电路切片

2026-10-25，负责人 Liangruizhi；[Issue102](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/102)，分支 `task/102-attention-rtl`，base PR101@5820c223c41327e154869616339dded900609007。所有张量、RTL、映射、门级和数学接收在本人CPU服务器；本机源码、metadata和字节接收。完成有界A切片L2及选定raw gate，待主会话上传PR及独立审查；非六Block库或物理实现完成。

## 本次真正闭合的链

从真实Q8/K16/V16和冻结scale开始，由RTL完整执行一个GQA共享组：8个Q头、一个共享KV头、d128、B1；QK → score → 合法前缀max → exp/sum → P15 → PV32。主机不提供QK、概率或PV。采用64既定数值函数和三遍score的materialized路径，**不是online softmax**。Q/K投影、RoPE、V投影、KV追加/淘汰和output projection没有加入本任务。

| 阶段 | 实际整数实现 | 状态与服务 |
| --- | --- | --- |
| QK | Q8[-127,127] × K16[-32767,32767]，K三平衡radix128 limb，通过同8个S8乘法，I32受检部分和 | 每次先取完整16-key K tile，再消费；完整d128后才转换score |
| score/max | I32 × 94906266 → S64，经RNE(18−Qe−Ke)到S32Q12；非法shift/溢出拒绝 | 一个S32共享乘法服务；完整有效前缀max，未来key不读取 |
| sum/P | max差值[-16,0]，exp grid128/U32Q30；U64sum；真实128迭代U128除法、余数RNE和P15饱和32767 | 再读两遍score；两次外部LUT，无免费缓存；先验Psum界再进入PV |
| PV | 三非负P limbs × 三平衡V limbs，9次S8乘法及有费shift/add，8个受检I32特征累加 | 每个16-key V tile后在单口S读改写输出；全部8头完成/服务排空才发布 |

QK limb保守前缀界为666,886,144；maxT1056时Psum界33,297，对PV limb保守前缀界1,365,976,128，均小于INT32正界。每步仍实际检测；无浮点运行分支。原始BF16 checkpoint在61以FP32计算捕获，离线Q20桥、scale和LUT编译仍明确是软件步骤，不称独立FP32 checkpoint或全模型INT8质量验证。输出PV单位为2^(Ve−15)，未擅自改为A8。

## 输入、缓存和协议

固定Qwen/Qwen2.5-3B revision `5defd2796acd3cb2051bb4c787eddc7f8f35e113`，layer0/KVhead0；原61 capture `a96eef6175d15173496d674caee7b0078971f2f5`。原manifest SHA `165e8109f8025c8bfafc9079d5a9e40e688897162cf6e9ca48d337efd5c3b5e5`，selected-raw.npz SHA `e7b8162bae2e8e85962de5e46a32b656ff3e51095149810ea81a779820cf0d10`，34,851,938B。

预注册76真实query：prefix128 full40、真实cached32；prefix1024 full2、真实cached2；每个完整8头。64 `.full`后32行没有冒充真正cached；cached重新从61 `.cached.q`编译，使用其最终KV前缀快照，未声称逐token追加写入。静态KV校准单位Ke=-8、Ve=-14保持，评价样本未用于改scale。另3合成覆盖length1/1056、P上饱和、LUT端点/-16边界、索引RNE ties、±32767V。

最初仅记last owner/version存在A→B→A漏洞；正式硬件冻结一个owner直到协调hardreset，version必须正数单调且不回卷。更大version替换旧cache；旧版永久失效，同版K/V地址与scale不变、length不退。softabort保留registry，不能通过abort重绑旧版。length是调用者保证已提交的有效前缀，RTL只核范围、position+1、单调和访问域；**没有自主证明append完成**。

所有命令锁存参数，busy拒绝新命令；S写也等应答；配置及外部request/take显式mask reset/abort。softabort取消完成发布、epoch不回卷、旧响应只discard。最大epoch永不接新命令，必须协调fabric/core硬复位。done保持至ack，完成前服务排空。具体接口与地址合同见[PROTOCOL](../../project/experiments/attention_rtl/PROTOCOL.md)。

## 实际通过的验收

- 两路完整运行（quiet/确定等待），每路79query/632head；全部119,904个QK、同量score/exp/P、每行sum及80,896个PV逐位独立核验。真实full与64所有有效prefix一致；未来masked QK不在执行域，不能拿它要求本次额外读未来。
- 每路71条同core资格命令：40个完整成功输出/320head，21预期错误，8个真实状态阶段abort、一个持有在途外部响应abort、一个DONE取消。独立接收3,624个QK和40,960个PV，非每case硬复位。
- 21错误含长度/位置/window/倍率/地址/alias/version、owner/旧版/same-version scale/base/length、A→B→A、Q=-128/K或V=-32768、score溢出、LUT零值与Psum失真。14类首轮descriptor/context错误及A→B→A均0外部事务，数值错误后同core恢复成功。
- 实测8个stage为3/10/12/22/25/27/38/41；reset前13次softabort、2个stale response，外部FIFO峰2。配置请求/待应答与abort、DONE与abort优先均实际核验；64B canary保持。
- 最大epoch仅RTL后门边界注入：idle/drained设0xfffffffe后过真实边沿，执行最后ffffffff命令、同tag迟到排空/拒新命令/no-wrap，再协调硬复位。没有把输出端赋值伪装为门级FF注入或普遍形式证明。
- 完整数值每路12份真实文件修改后重SHA负例、资格每路16份均拒绝；不仅检查SHA，还核数组、精确键/类型、实际计数、命令/恢复序列。receiver独立读实际simulation-command，绑定真实binary/build及RTL/driver SHA。
- 原map02精确Nangate45逻辑门级，选9个query×2等待，共18query/144完整head。每一数值、cycle、端口计数和协议字段与对应实际RTL相同，并再次独立整数接收；4份门级文件重SHA变异均拒绝。该driver无Q注入；错误/abort/terminal资格仅RTL，门级是零延迟函数+原行为store82，不是全等价/真实宏/STA签核。

Oracle不import producer：独立原capture编码、I64点积、Fraction/RNE、Decimal50 exp表、精确有理除法和PV；原64参考来源与SHA同时核。正式RTL源 `a6961b7`/phase5；最终执行driver `3b5743f`/phase7；严格接收/汇总 `b84f0b2`/phase8；归档 `06b7b4f`/phase10。硬件不因后续文档变更被重新命名为新执行。

## 实测周期、端口与库存

| 输入组 | query数 | 有效长度范围 | quiet active cycles | 有等待 active cycles |
| --- | ---: | --- | --- | --- |
| real/128/full | 40 | [1, 160] | [7776, 1099412] | [9380, 1298520] |
| real/128/cached | 32 | [129, 160] | [891698, 1099412] | [1053476, 1298520] |
| real/1024/full | 2 | [1024, 1056] | [7037552, 7114972] | [8313212, 8426704] |
| real/1024/cached | 2 | [1025, 1056] | [6986866, 7114972] | [8262820, 8426704] |
| synthetic/None/one | 1 | [1, 1] | [7776, 7776] | [9380, 9380] |
| synthetic/None/capacity | 1 | [1056, 1056] | [7296472, 7296472] | [8613044, 8613044] |
| synthetic/None/lut-ties | 1 | [6, 6] | [40584, 40584] | [48141, 48141] |

周期来自真实RTL计数，driver另以实际step数核active cycles+4等于命令边界；不含host Q配置、debug输出读回或held-DONE等待。两等待条件除cycles外所有数值及端口计数相同。没有把这些周期换算为频率、模型延迟或目标工艺PPA。

对完整8头、有效长度N，实际S8产品数=12288N；K和V各128N次128bit事务，意味着每头重读共享KV。LUT读=2E、SFU除法=E，E为全部8头中差值在exp域内的元素数。总外部事务=256N+2E，每事务5×128bit桥即80B；line payload16B单列。S读=384N+16ceil(N/4)+128ceil(N/8)+256(ceil(N/16)−1)，S写=256N+8ceil(N/4)+8ceil(N/8)+256ceil(N/16)。每query全部逐项独立核验，原始结构化明细见summary.json。

单16384B128bit1RW：Q1024、metadata保留256、score4224、P2112、共用K/Vtile4096、全8头PV4096、scratch保留512、canary64。附加六个128bit lineholder、八个I32累加、宽RNE/shift/compare、metadata/FSM/观察与控制计数均进入实际综合。

实际库存严格为8×signedS8与1×signedS32，唯一131072bit存储、1R/1W，无隐藏native div/mod/pow。Nangate45 typical逻辑映射 **53,187.764µm²、37,927cells、3,478DFF_X1**；generic含wrapper寄存4,213bit。unused SFU sqrt可能被剪枝；本A-only面积不能与97不同功能直接因果相减，不能说同一完整服务已共享。

SRAM/ROM宏、clock/CTS/RC/STA、电气/物理均未验。外部FIFO最低2×(128+32)=320bit加control另计；epoch sideband没有序列化进5beats。C0保留128KiB，新增exp对象8196逻辑B/8208物理B、SHA `659e0c81ddb592f49e27443dcfe89b9cf88439512cfba613dcd161950e5b6f80`，全部lookup都付费，无默认片内ROM。

## 对划分与电路设计的含义

已确认：Q8矩阵与KV16/P15状态不能统一按8bit记账；宽格式可用8S8有界分解，但要付3/9倍产品及宽shift/add、缓存和有限端口成本。完整合法前缀max/sum后才发布概率，Psum约束和scale/version属于真实消费者合同。当前单16KiB可容完整8头切片，epoch/版本状态必须随访问和发布跨越Block边界，不能只交付裸数组。

没有证明最优：逐头重读KV、三遍score、每概率128迭代除法和外部LUT都是明确成本。下一项应把M/A/R消费者接入**同一个**S/8S8/S32/SFU/link银行，核串行owner lease、状态/缓冲生命周期及精度，不能同时保留三个副本后声称同资源。在线softmax若新增，是有独立数值合同的第二候选，不能拿本P15真值替代其O重定标证明。append/淘汰、投影与整模型质量，以及真实宏/时序/制造后定制依赖仍单列。

## 失败、归档与交接

首轮C++的exp2标识符与数学库冲突造成build01失败，其两项自有依赖取消；改名后新目录重建。cost01严格库存拒绝动态vacc索引推导的额外256bitmemory；正式版改为八个显式固定寄存下标，未放松检查。早期仅last-context控制和旧合成version顺序保留，正式a6961b7重新跑全量；初次collector把server_models源码路径误判为模型权重而拒绝；修为精确目录段+权重后缀保护后新包归档，两个自有失效接收依赖取消。全部失败/日志/旧结果保留，未覆盖。

58个本人Slurm作业全部终态：51 COMPLETED、3 FAILED（构建/库存/首轮归档各1）、4仅自有失效依赖取消。

完整包677,232,014B/1743成员留授权服务器 `issue102-attention-rtl-20261025/delivery02/full-results.zip`，SHA `7a1e38f9c8fa2905aee499c5e8f99953385bc4d8694f14c0a2e55c05d1dcd53d`。精选365,258B/209成员入仓，SHA `5dd1661a55fc44ed8141fb5dc5935864b78ae26763588822ffbb6959558eb9d1`；双包服务器逐成员、精选PC逐成员、10phase/149原Git源字节核验PASS。原61完整capture/64参考只留来源SHA，未重复上传模型权重。

[结果索引](../../project/experiments/attention_rtl/results/issue-102/index.json)、[实际执行](../../work/Liangruizhi/102/execution.json)、[交接](../handoffs/2026-10-25-issue-102-attention-rtl.md)。指定账号/仓库/成员进度和权限复核；本地已整理、root负责推送/PR与Issue状态，不自行合并或标done。登记PR5 pending；board配置/read:project缺项仍unverified/待管理员，不把本地交付描述为远端已完成。
