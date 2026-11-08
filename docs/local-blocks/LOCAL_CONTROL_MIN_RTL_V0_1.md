# 最小功能局控 RTL 研究 v0.1

2026-11-04，Asia/Shanghai。Issue179／Draft PR180；负责人Melodydt；PR180基线41777f1d，PR176复查仍08f2ea20、正文与讨论无变化。

本轮将[第6步接口候选](LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)推进到第一份功能局控DUT。[实现、能力范围与复现](../../project/control_rtl_min_v0_1/README.md)和[实际运行报告](../../project/control_rtl_min_v0_1/run_report.json)为主入口。
本分支继续只研究母控／局控，完整Block实现为外部依赖。

同一份DUT由两个已有完整镜像改变行为：208B空任务只取指／返回，368B M clear程序读取执行描述符、发服务命令、等待真实peer响应后返回。程序由统一装载器经配置口写入外部PM；母控运行时只送CALL包及信用。
固定局控与PM／适配器／母控的逻辑连接不随程序改变，宏间M11/M12数据拓扑不在本切片中实现。M clear实际宏行为尚未验证，只验证控制器与服务行为模型的控制协议。

## 本轮解决的控制问题

1. 配置、取指和描述符共用一个128bit程序口，计数依据实际响应，运行时不接受配置写。
2. 头部、任务与完整执行记录先收齐再使用，PC先做宽范围检查再取14bit地址；没有预取或免费多端口。
3. EXEC接受时建立单个在途令牌和身份快照，WAIT使用前拍完成事实；native失败传递为ERROR，不伪装DONE。
4. 终态包在整包接受前保持稳定，连续任务不复位仍需新任务序号和终态信用。
5. PREPARE与全cohort deploy分开；装载候选出错失效，错误BEGIN保留旧提交，空闲撤销许可回INVALID。

## 验证边界与研究发现

实际Verilator编译／仿真和未修改的边界检查器分别保留证据，不把testbench通过等同于完整协议证明。
首轮位宽警告、第二轮peer在背压时改变信用、第三轮execution ABI偏移错误均保留失败作业记录；修正未改变ISA和旧镜像，未禁用位宽警告或削弱旧检查器。

原第6步688B是覆盖更大profile的payload下界；本子集未实现对象／GPR／PROGRESS holding，不能将其寄存器结构或Verilator执行时间用于全控制器面积／频率／功耗估计。
reset/release仍依赖外部协调器真实履行provider静默／复位条件；没有实现整个cohort的硬件。CANCEL、RX/TX、RAW16与超时仍是后续工作，不把本轮标为R3整体完成。

后续先补局控取消／异常排空和真实服务适配器边界，再扩有限S与收发服务；随后进入母控与多局控任务／事件协同。每次研究前及上传前继续核PR176，并把进展补入[总方案](TWO_LEVEL_CONTROL_PLAN.md)。
