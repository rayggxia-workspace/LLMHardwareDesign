# Issue99 单head连续R RTL冻结合同 v1

状态：实现前合同；实际结果必须另行验收。负责人Liangruizhi；task/99-r-state；只本人服务器issue99-r-state-20261025/lrz-i99-*。基线93 f660e3。读取Issue72 full-S32 guard_rescale既有整数coeff、calibration unit与输出；不读取模型权重内容、不生成新模型/其它机器任务。conv/LUT/其它31head/4096norm均切口外；consumer accept/reject只是Block接口。

## 1. 数学范围与选择

D128、N256，S32状态，共32768码/128KiB；固定72连续步，主head0。若原72事件元数据显示head0无重标，按head编号选择最小发生过range重标的head作第二完整72步，选择发生在看任何新误差之前；不挑有利样本。真实host只喂x/B/C I32Q12、dt/skip I32Q20、alpha UQ31及原calibration unit，不能提供decay/injection/proposal/new state/readout。

每head公式严格保留两次舍入：dtB=RNE12(dt*B)并I32 guard；decay=RNE31(old*alpha)；injection=RNE(32+unit)(x*dtB)；proposal=checked-I64 decay+injection。alpha范围[0,2^31]，端点2^31明确old恒等旁路（比较/mux/控制均映射）；其它alpha由实际signed32乘法器执行，不能把2^31解释成负数。

先完成全32768码proposal与全head conservative-I64 guard、S32范围检查。失败按原最多8次retry：私有trial完整head统一RNE1、unit+1、local_numeric_epoch+1，再完整重算。不得只重标一个tile。dtB溢出/左移或I64 guard也保留有界wide-failure重试语义；非法输入格式alpha>2^31直接descriptor error，不夹断。unit只允许[-127,127]，需要retry而unit/epoch到界必须拒绝，published不变。

RNE使用绝对值、商/余数、ties-to-even后恢复符号；I64_MIN在abs/shift前拒绝；负shift是有guard的左移，不免费截断。已知64bit product、I64 add、abs/max及移位都实际实现计价。全N256 readout先S32*C32精确signed64乘；与72相同保守max(abs(product))*256<=I64_MAX guard，再逐D完整和、RNE(-unit)对齐Q12、RNE20(skip*x)与最终I32检查。readout失败不重标，整事务拒绝；一般全码域需72signed bits，此候选只在该I64 guard内执行。

单位轨迹与该head原72数值比较；本地numeric_epoch只统计这个head的重标，不与32head共同epoch逐数相等。transport_generation独立：隔离命令/IO，与量化单位无关，不得混用。

## 2. 单16KiB128bit1RW布局（Dtile=1）

选择tile1为最小可验证控制，不称最优吞吐。所有S请求/回复串行，单有效回复，列byte半开区间：

|对象|位置|容量|
|---|---|---:|
|头/标量|[0,32)|32|
|X128|[32,544)|512|
|B256|[544,1568)|1024|
|C256|[1568,2592)|1024|
|dtB256|[2592,3616)|1024|
|trial单D行|[3616,4640)|1024|
|proposal单D行I64|[4640,6688)|2048|
|shadow单D行S32|[6688,7712)|1024|
|候选Y128|[7712,8224)|512|
|保留scratch（不执行V）|[8224,8736)|512|
|未用/canary|[8736,16384)|7648|

统计/单位/索引/校验寄存器、line staging、one-inflight桥和乘法响应另列映射，不暗加SRAM。coeff完整装入162行；dtB仅计算一次/attempt，不能重新调用host。trial先从published bank完整clone；proposal完整存外部，只有全head guard后才转换shadow；完整readout完成后才offer。每次S/external写都等ACK；无双buffer/多bank暗加带宽。

## 3. 有限外部库存与输入格式

当前任务独占1MiB窗口[0x04000000,0x04100000)，对齐16B。所有地址为控制器固定范围/索引，不接受任意未检查base：

- state bank0 [0x04000000,0x04020000)，bank1 [0x04020000,0x04040000)：各128KiB，指针轮换，当前published bank永不被私有写覆盖。
- trial [0x04040000,0x04060000)：128KiB；proposal [0x04060000,0x040A0000)：256KiB。
- Y bank0 [0x040A0000,0x040A0200)，Y bank1 [0x040A0200,0x040A0400)：各512B，跟state bank轮换，拒绝不破坏上一published Y。
- published descriptor [0x040A0400,0x040A0410)：一个128bit字。
- coeff [0x040B0000,0x040DD900)：72×2592B=186624B；其余gap计库存但无数据。

state/trial/proposal/Y/descriptor有效容量656400B，再加coeff186624B=843024B；外部实验RAM固定1MiB，不能称片内16KiB已容下状态。完整old clone、retry reencode、proposal写读、shadow写、readout重读、Y/meta、setup INIT/RESTORE全部计实际事务。无多余旧态备份clone：published bank本身就是不可变old；这是明确生命周期选择，不假称原软件两次copy免费。

每token coeff162个128bit行：首行uint32(magic=0x52393943, position, head_id, reserved=0)，第二行(int32 dt,uint32 alpha,int32 skip,uint32 reserved=0)，随后128×I32 X、256×I32 B、256×I32 C。位置/owner/header/alpha范围校验先于状态运算；head允许0..31但实际owner冻结layer0，本轮只执行选定head。

桥按既有memory_link真实协议：read/write均5个128bit beat（四header、一data）=80B，payload16B，另32bittransport_generation sideband不在5beat内。header中32bit地址并不意味着beat宽32。每次最多一个外部请求在途；write ACK必须保证该128bit写已生效且不会以后再次生效。这是明确fabric义务，不是已验证目标宏/NoC。

## 4. 发布描述符逐bit合同与命令

一个128bit字：bits31:0 magic0x52393901；63:32 position32；95:64 local_numeric_epoch32；111:96 unit signed16；112 bank；117:113 head_id5；118 valid；122:119 profile4（固定1=S32guard-rescale）；127:123 owner5（固定0=layer0 R）。version明确alias position，无第二独立version字段。模型/形状/精度合同由magic+固定profile界定；不是任意模型身份或安全认证。

INIT、STEP、RESTORE三类显式cmd_ready/cmd_accept命令，所有参数锁存，busy与配置pending禁止命令丢弃。INIT只用于调用者明确授权的新context，RTL实际清零bank0与Y0并最终写初始descriptor，初unit来自既有cal。真实主测host不初始化计算state。STEP校验caller expected_position与published position，读取对应coeff，产生private状态和Y。RESTORE仅在协调fabric屏障后读取真实descriptor并校验magic/owner/head/profile/valid/unit；不能用host猜测old/new。状态完整性SHA只在观察者接收，不冒充片上SHA引擎。

consumer_offer保持候选unit/localepoch/position/bank与Y稳定；accept/reject同时出现以reject优先。任何numeric error/reject在descriptor提交前保持published字及旧state/Y全部不变。只有所有S/mul/外部write响应排空后才offer。

consumer_accept之后发布单128bit descriptor写。该写被外部接受后进入**不可撤销commit-drain**：abort_ready=0，不得先回“取消成功”；ACK后更新内部published镜像，响应committed。之后再响应新的abort。128bit外部写原子是接口要求，未证明宏物理原子性；若fabric不支持，需另议shadow descriptor+最终指针并全计成本。

此前soft_abort只有abort_ready/abort_accept成立才被接收，停止新IO但保留已接受IO的credit，等实际write ACK/read响应消费后才完成abort并恢复cmd_ready。仅改epoch不能撤销已发写。transport generation不wrap，耗尽必须协调fabric/reset；local_numeric_epoch只有range retry推进，publish拒绝不改变旧数字epoch。

硬reset屏蔽所有请求/假握手。若发生在private或descriptor写未ACK阶段，fabric必须协调排空所有已接受操作并清回复，再允许RESTORE；真实descriptor可能已新提交，也可能仍旧，恢复读取实际字。实验要覆盖write已生效但ACK尚未到达时的reset/restore，不能只测迟到read，也不能靠host猜测结果。无独立CDC/掉电持久性/跨32head原子资格。

## 5. 验收与证据

同核72连续、chunk8/16停顿+实际RESTORE、quiet/背压及有限响应；逐步完整32768state码、128readout、unit/localepoch/retry匹配独立bigint与72切片。需观察所有published old/descriptor保护、非工作S/externalcanary。

合成边界：alpha0/2^31、正负ties/INT_MIN、dtB溢出、合法负shift/左移溢出、全head重标/重试耗尽/unit/epoch耗尽、完整N readout guard/I32输出guard；错误owner/profile/position/descriptor、late write ACK、consumer reject/双响应、多阶段abort恢复、hardreset未ACK后实际restore。合成初始checkpoint可显式提供测试码域，但不能用于替代真实72由RTL递推产生的状态。

真实修改state/unit/protocol文件并重SHA，调用冻结完整receiver拒绝；独立source/input/results SHA与all artifacts，保留失败。映射真实新增FSM/宽shift/add/metadata/接口，单S32乘法服务候选单列，不声称已接97或继承98STA。root最终发布PR、不自合并/done；登记PR5 pending、看板权限缺项保留。
