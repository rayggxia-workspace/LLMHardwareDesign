# Issue110：注意力 limb 移位与位宽的受控电路比较

2026-10-25；Liangruizhi；Issue110，task/110-attention-width。基线为106 PR108@7a9fece。独立服务器目录 `issue110-attention-width-20261025`；不修改106或109工作目录，也不把候选优化写成已经整合109。

## 当前结论

三种实现保持相同整数合同、原INT32溢出检查、同16KiB/8S8/S32/SFU/link库存。完整102的79查询、真实cached输入、完整边界恢复，以及106的7混合/27恢复命令，在两种等待条件下均通过独立数学接收。全部记录、周期、实际物理事务及协议字段与STYLE0逐项完全相等；这是本次面积比较的前提，见 `paired-receipt.json`。

| 候选 | QK / PV算术 | 实际mapped逻辑面积 µm² | cells | 相对本批STYLE0 |
| --- | --- | ---: | ---: | ---: |
| STYLE0 | 原64位动态移位 | 126,029.470 | 85,361 | 基线 |
| STYLE1 | 64位显式常量选择 | 125,300.098 | 84,737 | −729.372；−0.57873% |
| STYLE2 | 已证明QK34 / PV45，常量选择 | 125,009.626 | 84,500 | −1,019.844；−0.80921% |

三者均为9,397个DFF_X1、10,752 generic寄存bit（含wrapper寄存）、131,072bit单1RW行为存储。独立库存核验实际唯一8个signed8×8、1个signed32×32、一个SFU和一个外部桥，保持两有限S32响应槽及所有观测/控制逻辑。没有通过移除计数器或多放存储获得收益。

STYLE2可作为后续整合候选，但总逻辑面积仅降低约0.81%，没有周期加速。这一改动没有解决当前共享Block的主要面积问题，也不构成STA、频率、功耗或完整PPA收益。历史106的125,966.694µm²对应旧源结构和映射；本批STYLE0经过等价表达和重新综合，得到126,029.470µm²。不得把两种baseline混用或隐去这一差异。

三变体×两等待的六路实际raw mapped gate全部通过：各INIT→完整M0→完整8头A prefix1→完整Falcon R0，与同driver RTL的全部字段、周期及协议相同，再通过独立数学接收。该子集不含cached/abort/epoch故障注入门级资格；完整cached及恢复在RTL层通过。最终总接收状态为`PASS110_PROVED_EQUIVALENT_SAME_CYCLE_RESOURCE_SELECTED_RAW_GATE`。

## 为什么允许缩窄

1. 原106→STYLE0单独比较，再比较STYLE1/2；没有拿新模型自证。Yosys对真实RTL作proc，提取原始cell/pin/参数的组合锥，保留原始JSON、命令和源SHA。
2. 输入域含任意8个S16乘积和任意S32累加器，比合法S8乘积域更宽。每一个真实QK前缀加法都对独立S64数学和证明；8项和在[−262144,262136]内，中间I32均不溢出。
3. QK合法移位0/7/14，任意S32部分和与最大移位相加可超过S33，S34足够；PV任意S16乘积经0/7/14/21/28移位再加S32，S44不足而S45足够。保留完整值后再执行原I32 guard，不是先截断到32位再判断。
4. 真正的limb/plimb/vlimb FF D锥逐版证明：reset产生0，当前三个limb均≤2时下一拍仍≤2，其他寄存和外设输入任意。STYLE2对非法内部QK limb3不等价，故不能删掉这一可达域条件。取消该条件会得到真实SAT反例，已保存。PV非法limb组合仍按原default28处理。
5. 独立接收器再次核对实际锥的全部cell/pin/输出和源范围，并重新构建性质运行SAT。两版源的控制器、溢出guard、握手和接口在允许的两段算术表达以外逐字一致。102适配只还原原来的内置8S8；106继续使用实际共享8S8。

这是二态位向量和真实next-state门锥证明，依赖正确同步reset；不证明整个top的活性、物理时序、软错误容忍或所有后续接口实现。

## 完整消费者与边界结果

原102输入来自Qwen2.5真实捕获，79查询含76真实查询及3个边界合成输入，8Q×d128完整GQA；实际cached快照单独编码，不冒充append。原输入、LUT、原捕获SHA和独立Decimal/Fraction/bigint/NumPy接收不变。106复用原M0/M5、A full1/cached129、Falcon完整head0连续STEP0/1；这是不同工作负载交替使用同一银行，不是单模型端到端图。

| 每个变体、每种套件 | 无等待总cycles | 有等待总cycles | 两种等待下的输出记录 |
| --- | ---: | ---: | ---: |
| 102完整79查询 | 102,304,592 | 120,963,906 | 各79条/632 heads |
| 102完整恢复 | 3,127,808 | 3,704,250 | 各40条成功结果，另有原失败/abort协议记录 |
| 106完整混合 | 17,103,407 | 20,314,135 | 各7条 |
| 106完整恢复 | 25,315,312 | 30,088,639 | 各27条 |

本表每一个数字在三个变体完全相同；逐字段比较包含状态、scale元数据、S读写、S32/SFU grant、外部事务/5×128bit packet、导出长度、全状态和恢复协议，不仅是最终输出。

原错误条件、同owner/version、跨lease保留、abort后已接受事务排空、旧tag丢弃和epoch耗尽边界仍由原driver实测。原qualification中的显式Q注入只属于RTL资格，不放进mapped gate声称。

34项负例包括：102真实输出/协议文件16项、106真实输出/状态/metadata文件8项、变体标识与精确adapter绑定3项、真实锥/FF输出/前缀绑定4项、移除limb可达域后的实际SAT反例1项、真实库存2项。文件变更后重新计算SHA再通过完整接收；不能用SHA不匹配冒充语义拒绝。

## 面积与物理边界

本次数值合同不变：Q8/KV16、QK/PV检查I32、scoreS32Q12、expU32Q30、U64 sum、P15；无新增浮点回退。增加或缩窄的选择/符号扩展/比较路径进入真实综合。面积是Nangate45典型库逻辑cell之和，包含三套控制器、宽算术、队列、观测和仲裁；不是面积模型，也不按cell类型把组合锥猜成模块面积。

16KiB行为SRAM没有宏面积，外部128KiB LUT、M/A backing、Falcon1MiB及fabric两个128bit+32bit响应槽仍在环境边界；至少320bit+控制和32bit epoch sideband不在core逻辑面积。M/A下游最大6KiB provisional暂存仍未实现为核心硬件。三种方案对这些条件相同。

未做STA/布局布线/RC/CTS/PVT/宏映射，也不继承98对其他网表的资格。STYLE2仍明显高于98旧网表79,600.5µm²预算；本任务没有提高预算。制造前固定/产品后定制、通用ISA/GEMM、online/KV append、下游提交缓冲及完整六Block库仍未完成。109新增GDN属于独立实现，需在其实际网表重新整合、验证和计价。

## 运行、失败与交付

实际RTL在 `fe9ee178` 冻结；构建和原输入复用 `f066925`，接收/对照/负例 `f144277`、`f8d1d56`，最终验收/归档 `3b974e1`。更晚的文档commit不替代这些运行源码SHA。五阶段源/源ZIP保留，交付时核原Git blob、完整包和精选包字节。

一次旧Slurm job依赖过期导致提交拒绝，未产生计算作业；恢复时两次基线门级未等待build manifest便被接收入口拒绝，作业91536/91538实际0秒失败。修正调度后使用g00b/g01b新目录，不覆盖失败档，不更改数值预期或RTL。所有实际命令、日志、作业和失败均归档；执行前的自动审批超时不算服务器实验。

完整成果与SHA见 `project/experiments/attention_width/results/issue-110/index.json`，完整包留授权服务器；精选只供查验，不替代完整输入/网表/数学重放。管理结构检查与累计diff检查是另项，不代替实验。

下一步只建议将STYLE2有界表达整合到后续真实共享top，重核库存和功能；不在本任务改109，也不凭0.81%有限逻辑收益改整个Block物理划分。主会话统一上传PR/同步Issue；当前不自行push、合并或done。登记PR5 pending，看板缺配置/read:project，unverified/同步pending。

## 最终证据与读回入口

- [逐周期/协议/实际事务配对回执](../../project/experiments/attention_width/results/issue-110/paired-receipt.json)是比较门槛；[报告汇总](../../project/experiments/attention_width/results/issue-110/summary.json)只在全部必需回执通过后生成。
- [实际锥与独立SAT回执](../../project/experiments/attention_width/results/issue-110/proof-receipt.json)、[六路真实raw门级回执](../../project/experiments/attention_width/results/issue-110/gate-receipt.json)、[完整索引](../../project/experiments/attention_width/results/issue-110/index.json)保留源commit/文件SHA与运行链。
- 全部106个本人Slurm作业已终态：104个COMPLETED，2个因调度缺build manifest而0秒FAILED且原样保留。完整执行与终态见[execution](../../work/Liangruizhi/110/execution.json)。没有仍运行、取消或依赖未满足的本任务作业。
- 完整包87,834,705B / 1,616成员，服务器`delivery01/full-results.zip`，SHA-256 `e3be4dadd6018b5f9dd49a6d2c25d90add4f010bdd8641216bbb28863d96eccc`。
- 精选包1,299,697B / 540成员，SHA-256 `ea3f7b9560389c264e15036c9ff1d525aa8e777ee13ddc8810fe7a72b8f42206`，随仓库保存。服务器双包、PC精选与5阶段320个原Git源条目字节接收均PASS。

本地科学交付已整理；root统一发布PR和同步Issue，未自行上传/合并/done。当前报告中的“通过”仅限上述实际功能、证明、库存和门级范围。
