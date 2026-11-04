# 五类控制profile与状态：R5有界研究

Issue179／Draft PR180。这里是研究用软件控制模型与候选适配ABI，不是新增原生宏、完整Block或U/C/F/J控制RTL资格。ISA v0.1的128bit指令、操作码和九种记录布局保持不变；新镜像使用未分配给硬件的研究标签`native_abi_id=capacity_profile_id=0x17950001`、`topology_id=0x17950002`，`deployable=false`。现有P RTL只接受ABI65537，不接受这些镜像。

| 类型 | 宏与资源mask | 候选控制顺序 |
| --- | --- | --- |
| P | M/G/S，41 | M→私有S→可选G；有限循环 |
| U | N/E/S，38 | N→私有S→可选E；状态消费者时先实际读取next |
| C | R/G/E/S，60 | R读old／写next→可选G→E；独立发布任务 |
| F | G/E/S，44 | G→私有S→可选E；状态消费者时先实际读取next |
| J | E/S/T，100 | T→私有S→可选E，外部参数决定已声明路径 |

表中路线是candidate适配合同，不能证明M11/M12可达或原生服务已经接通。N/E/G/T/R的数学、Q格式、舍入与饱和来自外部数值服务合同；本模型只用16B版本标记追踪依赖。每端一个16B scratch，地址上限16KiB；不是分配了16KiB物理SRAM。有限性：最多3局控、2个全局活动任务、每局控1个服务／token、1个PM请求、1个返回槽、最多8个holding channel、16个外部状态handle；8192是实验model-tick上限，不是硬件周期预算。

## 程序与编码

`images.py`使用旧codec打包真实二进制，`model.py`从经WRITE16／实际READ16回对的镜像按PC读取，每次PM响应16B；任务／对象／128B执行描述符逐拍读完后才使用。G_PARAM等实际参数响应接受后退休，G_CALL锁存全部GPR；每任务清GPR并由L_ARG读取CALL锁存值。L_ADDI解释有符号imm32并拒绝溢出；LOOP必须回跳且计数>0，BRANCH必须向前。`check.py`独立重建取指／PC／寄存器、信用、实际存储／参数读取、字节前缀和发布义务。输入payload是opaque版本标记，不验证R或其他宏数学结果。

候选逻辑服务沿用`execution`记录：resource取旧ISA表，compute的`service=0,native_op=0xF100+resource,completion=LOCAL_STORED,count=1,stride=16`；`src0=255`表示已声明的外部版本输入／old／next，`src0=0`表示私有scratch，`dst=0`。`native0`动作0为普通scratch服务、1为C更新、2为消费者receipt、4为读取next；动作2／4的`native1`为receipt位1或2，其余为0。这些数值是**候选adapter操作号，不是任何现有宏的真实cmd_op**。

发布使用R逻辑适配器的`service=5,native_op=0xF1FF,native0=3,completion=NATIVE_DONE`；它不是新增ISA操作码。状态动作声明`parameter_ref=4096,parameter_bytes=32`，实际参数响应与CALL的前五个状态字匹配后执行。外部控制参数字0..7依次是old_handle、next_handle、expected_generation、required_consumer_mask、transaction_id、local_iterations、local_optional_path、mother_iterations；各字uint32小端。前五字为状态事务身份，后三字用于编译控制流；GPR可变，immutable参数区不变。当前C合同要求两个消费者，示例mask3；旧／新handle是外部状态存储标识，不宣称等于R原生context编号。

状态程序为：母控G_PARAM取参→CALL C更新／WAIT→CALL U及F／WAIT全部→CALL C发布任务描述符1／WAIT→G_END。局控执行OPEN／ARG／MOVI／EXEC／WAIT／BRANCH／ADDI／LOOP／DROP／END；更新和发布是两个明确任务入口。R实际读取非零old标记后写next，U/F实际读取next并完成scratch写／ACK及成功终态，发布才允许发生；不把G_WAIT或“发完计算”直接当作状态提交。

## 发布、取消与恢复

发布的线性化点在provider原子改写root。之前的错误保留old；已经offered的发布不能撤回，因此取消后仍可能提交。发布ACK丢失或发布后错误时，调用方按UNKNOWN处理，通过持久transaction journal查询；不能仅凭ERROR／POISONED声称old仍有效。幂等重试检查事务号及old／next／generation，禁止二次改写。old只能在确认发布、消费者全部结束且无旧响应后释放。连续正常job和错误后的job不reset，保留任务序号、私有存储内容与已提交状态；未确认发布结果时禁止直接装入下一job参数。

`cohort.py`另提出64B管理帧，独立于ISA指令和现有RTL端口：version@0/u16，kind@2/u8，participant@3/u8，reset_sequence@4/u32，epoch@8/u32，generation@12/u32，cohort_bitmap@16/u64，transaction@24/u32，status@28/u16，flags@30/u16，value0..3@32..44/u32，48..63保留0，全小端。kind128/129/130/131/132分别RESET_REQ／ACK／RELEASE／QUERY／REPLY；ACK flags.bit0=applied，QUERY_REPLY status2=committed、3=not-found，value0/1为当前root/generation、value2/3为事务old/new。每种消息未用字段为0。`examples.json`含字段表和可复核字节例子；尚无真实传输serializer／MMIO绑定。

完整cohort包括母控、各局控、adapter、五类实际列出的provider、feeder、transport、ingress、外部MEM／持久journal接口，按inventory分配参与者位。模型要求实际应用复位／清空未来旧响应后才允许匹配ACK，拒绝未知／重复／旧序号与错误epoch；所有ACK、额外quiet step、全部镜像重装／实际读回、新generation／epoch和未知提交查询完成后才RELEASE。provider没有job tag时必须依靠可信flush／reset合同，观察器的来源标记不用于路由；quiet model tick不等于真实CDC／复位时序证明。提交状态／journal不被reset清零。

## 实际验证与复现

所有执行仿真均在服务器：

```bash
python3 -B project/control_profiles_v0_1/run_profiles.py --out /work/results/profiles
```

最终97246／node27／debug／1核COMPLETED0:0，34模型执行、30镜像拒绝、6组114复位／查询检查、4错误轨迹拒绝；见`profiles_report.json`／`cohort_report.json`和[验证索引](../../work/Melodydt/179/control-profiles-validation.json)。97244因遗漏CANCEL观察事件失败；97245早期模型通过，97246进一步要求显式OLD_READ／NEXT_READ及读值依赖，不能混淆版本。原始轨迹仅服务器保存，报告逐份SHA。

`examples.json`是静态编码导出，逐镜像SHA与最终服务器用例相同；不是本机模型执行。可使用：

```bash
python project/control_profiles_v0_1/export_examples.py --server-report <server-copy>/profiles_report.json --output project/control_profiles_v0_1/examples.json
```

R5有界控制研究产物已具备；新指令／参数／候选服务的RTL实现、真实native ABI与适配、provider复位／CDC、数值转换、完整Block和物理仍未验收。R6控制IR生成与R7成本／真实接入是后续阶段，本次不自动开展。
