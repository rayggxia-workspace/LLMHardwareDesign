# W4 N 控制器接口与状态说明

研究输入 `0101cc7e1e6d5718455fb45b61c7428439efc09a`，原生N固定 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。实现 `block_w4_n_ctrl.sv`，端口逐项遵循包根 `W4_ABI.md`。本模块外接真实N与唯一S helper，不实例化或修改native/P2/W1/W3。此稿是实际RTL候选，尚无本agent执行的compile/simulation或PPA证据。

## 服务与准入

一次只接受一个请求，req在 `req_valid && req_ready` 的上升沿快照。mode0为Softmax，1为RMS，2为L2；count为1..257 S16，S字数W=ceil(count/8)，尾字native_count=min(8,remaining)。全部实际used地址范围须落在S word0..1023。Norm的src/gamma/dst两两不重叠；Softmax的src/exp/dst两两不重叠。Norm epsilon必须非零；Softmax忽略epsilon与gamma，Norm忽略exp地址。

地址检查使用17-bit扩展加法，先检查word range，避免10-bit wrap绕过准入。地址相邻且不重叠允许；in-place/overlap是本次控制器profile尚不支持，并非永久算法非法。caller须保证源和gamma整个服务不可变，且持有独占N group上下文和单S helper owner到服务rsp被消费，不得插入其它N group或TopK。

req_ready仅在IDLE且未poison时为1。busy覆盖工作、保留rsp，以及运行失败后的reset-required锁。rsp_valid/error/saturated在RESPONSE保持到rsp_ready；无运行时role标签或通用产品程序加载。请求地址/op等为本地控制接口，是否暴露给host由外部固定调用者约束。

## 固定原生顺序

| 阶段 | 真实动作 |
| --- | --- |
| BEGIN | N.op0，param=mode，data低32为epsilon，其余/aux/count归零；消费ACK |
| STATS | 每字真实S读src，捕获并take响应、mask尾部，再发N.op1/count，逐次消费ACK；先完成全部W字 |
| FINAL_STATS | N.op2，消费ACK/错误；Norm因子在native内部产生，Softmax此时只完成全组统计 |
| Norm replay | 每字重新读src并捕获，再读gamma并捕获；N.op5(data=原x，aux=gamma)，只将有效S16结果写dst，等待真实写ACK |
| Softmax EXP | 每字重新读原score，N.op3产生U16 EXP；exact bits写exp并逐字等待ACK，保留32768编码，不作signed转换 |
| FINAL_EXP | 仅在全部EXP已写ACK后发N.op4，消费因子完成ACK |
| Softmax replay | 每字真实S读exact EXP，N.op6；有效Q14概率写dst，等待真实写ACK |
| completion | 最后一字dst写ACK被消费后才rsp；payload不被误当作BEGIN/STATS/finalize ACK |

每次S响应先被捕获/消费才允许后续请求；native命令和响应也单在途。请求和写载荷由锁存器保持，无固定延迟假设。原生response按锁存 `cmd_op_hold` 分类；op3/5/6返回数据，其余所用op只是ACK。所有raw/gamma/EXP命令输入的inactive lane归零，输出尾部归零后写S。

正常Norm每组N命令数2+2W，S事务4W（3W读+W写）；Softmax N命令3+3W，S事务5W（3W读+2W写）。例如count257，W=33，native尾字count1；Norm68条N命令/132笔S事务，Softmax102条N命令/165笔S事务。这些是无中断成功路径的固定调度计数，尚待独立TB检查，不是已执行结果。

## 数值边界

数值运算仍由固定native N执行，本控制器不重新近似sqrt/divide/EXP。RMS factor为 floor(2^38 / isqrt(floor(sumsq*2^16/count)+epsilon*2^16))，L2不做count除法；结果为clipS16(RNE30(x*factor*gamma))。gamma=1024表达数学1、输出Fin10；epsilon按输入编码的平方单位理解，不默认适配其它宏单位。

Softmax输入S16 score Fin10；STATS取得全组max后，op3按全组max输出U16 code0..32768。op4 factor=floor(2^44/sumEXP)；op6输出clip[0,16384](RNE30(EXP*factor)) Q14。EXP临时区是原样lineage保留，不是概率，不能用原score替代op6输入。257项最后一项成为新max时，也必须先完成全部STATS再统一EXP，此RTL顺序满足该条件。

## 错误、部分可见性与协调复位

本地准入错误发生在BEGIN之前：不访问S/N、返回error；不poison既有成功上下文，rsp消费后可接受新请求。成功完成后下一服务用新的BEGIN清理Norm/Softmax上下文；不宣称BEGIN清理TopK或支持上下文互抢。

一旦准入成功进入服务，任何native rsp_error或mem_rsp_error均消费当前响应、丢弃尚未提交结果、置 `poisoned=1` 并返回held error。响应消费后仍 `req_ready=0`、`busy=1`；必须由外层协调reset本控制器、N和S helper后才能复用。不会在失败后悄悄尝试新的BEGIN。rsp_saturated保留已观察的native标志OR，独立于error。

错误发生在第一笔dst写之前时dst未写；但Softmax可能已有EXP scratch写。若先前dst写已完成，后续失败留下部分结果，不能承诺整组事务回滚。若WRITE_RSP报错，其写请求已经被下层接受，更不能撤销；当前真实S helper普通rsp_error固定0，故错误支不构成新存储故障检测能力。读/写及数值失败均由caller把目标整体视为不可提交。

reset为高有效同步；请求valid/ready也由reset门控。外部abort必须映射为N/controller/helper及owner的协调reset。没有独立无reset cancel、排空后回滚或自动清RAM承诺。RAM内容和已经被外部使用的数据不因reset回滚。

## 状态与独立验证观察点

state：IDLE0、N_REQ1、N_RSP2、MEM_REQ3、MEM_RSP4、RESPONSE5。flow：BEGIN0、STATS1、FINAL_STATS2、EXP3、FINAL_EXP4、REPLAY5。access_kind：READ_SRC0、READ_GAMMA1、READ_EXP2、WRITE_EXP3、WRITE_DST4。`word_index/words_hold`为6bit，`chunk_count`为4bit；`cmd_op_hold`用于response分类，`poisoned`用于失败锁。

独立TB须连接真实N/S/helper，核对RMS/L2/Softmax含257尾部、全局max和EXP原样回放、全部write ACK门、请求/应答背压、格式/tail、region/参数拒绝、runtime错误poison和协调reset恢复、成功与本地拒绝后新BEGIN。native/mem门控若用于TB须两端对称，不能因单端force制造虚假接受。根runner提供真实工具/命令、源/输入SHA、日志与退出码后才能增加通过结论。本稿未运行仿真。
