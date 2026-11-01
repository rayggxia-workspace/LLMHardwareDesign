# W4：有界RMS-preNorm F8控制

研究父提交`0101cc7e1e6d5718455fb45b61c7428439efc09a`，原生源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。新增独立`block_w4_f8_top.sv`，保留原叶/P2/W1/W3文件。接口沿W3：16拍可变输入、input_stored/start、busy、保持到take的DONE/error/saturated和T输出。没有host opcode、shape、地址或程序装载。此实现仅固定8维RMS预归一化FFN及原x残差，不是任意模型的完整F/A、数值质量或系统物理资格。

## 固定数值与地址

x和三份8×8 n-major权重仍为S8 Fin7。原x以S16 sign-extend保存S466；N RMS8使用gamma每项1024及epsilon raw=1，src466/gamma475/dst474。N原始公式为`factor=floor(2^38/isqrt(floor(sumsq*2^16/8)+2^16))`，逐项`clipS16(RNE30(x_raw*factor*1024))`，本profile将结果绑定为Fin10。epsilon处于原始整数平方码单位，不是直接把浮点模型epsilon写成1。

N结果先存入S474并消费ACK，然后top回读474，用新组合函数`narrow_norm_rne3`实现逐S16 RNE右移3、再clipS8，得到M投影输入Fin7。仅低64紧凑装8个S8，高64硬件清零，改写S448；449..451的输入padding已经真实写零。E7残差始终读原始S466，左移3至S467，不能以normalized x替换原残差。三次M、G及最后E相加沿W3有限profile。

| S地址 | 内容与生命周期 |
|---|---|
| 448..451 | ingress原x保留容器；RUN后仅448显式改写为narrowed norm x，供gate/up loader |
| 452..463 | 三份可变S8权重，各4字，整个RUN保留 |
| 464/465 | gate/up S16 Fin10，G读取并存mid前不复用 |
| 466 | 原始x S16 Fin7，N两次raw读取及原残差E7均使用，不被N输出覆盖 |
| 467 | 原始x残差Fin10，最终E0前保留 |
| 468..471 | G mid S16 Fin10及3个真实零padding字，down loader之前全部ACK |
| 472/473 | down/final S16 Fin10，最终T只读取473 |
| 474 | N RMS输出S16 Fin10，N目的写ACK后再由top回读窄化 |
| 475 | 8个S16 gamma=1024，N整个group期间不可改 |

固定保留448..475共28字/448B；S宏仍是16KiB，T宏仍是6KiB但本程序只使用1字lease。没有扩大/缩小原生宏存储，也没有研究MEM调度。

## 顺序与计数

输入16次写ACK后才能start。start后的顺序为：保存原x至466→写gamma475→N RMS服务→读474/RNE3→写448→E7原残差→M gate→M up→G门乘→mid padding三次写→M down→E0残差相加→读473→T BEGIN1/WRITE1/COMMIT/TAKE1/RELEASE→成功DONE。

普通S owner为LOCAL0/E1/G2/N3，仍只有一个`block_p2_s_ctrl`和一个native S普通端口。N整个group从request到service response消费独占owner，不能在N统计/回放中间交给其他group。成功service response必须已消费最后目的写ACK；N失败后top在下一拍通过internal_reset协调N controller、N native、helper及其他叶子复位，然后保留error DONE。内部错误复位由顺序寄存脉冲产生，不形成response ready→error→leaf_reset的组合环。

正常帧计数为39个普通S请求/ACK：入口16W；RUN23笔=13W/10R，总29W/10R。相对W3的32笔新增7笔：gamma写1、N统计raw读1及回放raw/gamma读2与N输出写1、top读N输出1、改写M输入448一次。N单个8项group产生4个native命令/应答：BEGIN0→STATS1→FINALIZE2→NORM5；其余保持15M命令/应答、3loader、2E服务、1G服务和T单字take/独立release。

## 新增逻辑与限制

`narrow_norm_rne3`是8条并行17bit符号扩展/算术移位/低3bit舍入判定/加一/S8上下界比较与选择的真实RTL组合逻辑，返回128bit包及1bit裁剪标志。它不是金属连线或E12的别名；native E12没有所需RNE。除新N原生实例和Ncontroller的上下文/缓冲外，top还新增owner四路选择、N阶段状态以及local_tag的一位宽度；没有新增完整张量RAM。没有进行综合，不能给新增门数、面积或时序成本。

负数使用算术右移形成floor，再以正的低bit余数与保留位奇偶决定加一；例如-4→0、-12→-2为ties-to-even，1020→128后clip127并置sat，-1028→-128不置sat。`check_f8_narrow.py`已将全部65536个S16输入与独立sign/magnitude整数参考及10个literal边界比较通过，回执明确这只是整数设计检查，不证明HDL展开/8lane接线或时序行为。真实RTL由另一作者的独立oracle/TB及根任务ModelSim另行验证。

done_saturated OR所有已退休N/M/E/G响应及本地窄化clip。预归一化后S8范围仍可裁剪，这是本profile定义内的行为，不能当作真实模型量化精度已接受。abort/error只保留已观察的clip，未退休阶段不推断。busy、早start pulse不排队、held start接受一次、prestart abort无DONE、RUN abort一份error DONE、已有DONE+abort+ready恰好消费一次和硬reset沿W3语义；不回滚已接受RAM写或外部消费。

top服务观察点为`n_req_* / n_rsp_*`，native回应另名`n_native_rsp_*`，native命令`n_cmd_*`；实例`u_n_ctrl/u_n`。固定`permit_n_req/rsp`仅供TB有限背压，产品RTL恒1。原S/M/E/G许可和层级沿W3。Ncontroller poisoned错误后必须协调reset，不能以新的BEGIN绕过poison；本top按此恢复。

当前实际检查：integrated根`python -B -X utf8 scripts/check_project.py`通过；65536项整数设计检查及UTF8 LF检查通过。根任务实际ModelSim运行`runs/f8-r01`编译/仿真exit0，25个唯一CASE、16323周期，本文作者已读回源码快照/receipt/log：top SHA`54905280f8b9dbfcd7440981fd4f4244c509ea8de5e1a8912a050c457ad75a8e`与当前draft/正式文件一致；对应Ncontroller SHA`02e6e8f0538c8423481c2f30a3d0a2d392bae583551cbf7ffcc7cd947674cd01`。此为根执行、本文读回，不是自行仿真或外部PR批准。详见`w4-n-controller-review.json`的源和日志指纹。原P2/W1/W3、完整F/A、大shape映射、系统母控/M11/M12实现及PPA不由这个F8切片自动覆盖。
