# W3 验证与交叉审阅补充

关联 Issue151 / PR152。W3 输入研究提交为 `99d6df2e094febe4ea8fc9896301adbbfdc803ed`，原生叶源为 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本补充由 E/G adapter 作者只读核对另一作者 FFN 顶层与 root 的真实运行证据形成；审阅者没有启动这些仿真，也没有代替外部审查人批准 PR。

## 实际运行与结果

| 保留运行目录 | 实际日志标记 | 退出码及检查范围 |
| --- | --- | --- |
| `runs/ffn-r02` | `PASS_W3_FFN8 cases=21 cycles=7524` | compile/simulation均0；21条 CASE_PASS 与receipt逐项一致；固定FFN8的数值、阶段、32笔普通S事务、恢复及错误门 |
| `runs/adapters-r01` | `PASS_W3_ADAPTERS cases=46 cycles=2231` | compile/simulation均0；46条 CASE_PASS 与receipt逐项一致；E/G一字service及协议定向测试 |
| `runs/regression-r01` | `PASS_P2_S_CTRL`、`PASS_P2_MST`、`PASS_W1_MST cases=28 cycles=4422` | compile及三次simulation均0；helper6+P2 MST13+W1 MST28共47条 CASE_PASS 与receipt逐项一致 |

工具为本地 ModelSim SE-64 2020.4，Python3.7.0，Windows主机；没有服务器/SSH作业或物理流程。本次已读回各run的版本、vlib、compile和simulation log，SHA-256全部与相应 `run-receipt.json` 相符；仿真日志末尾Errors0/Warnings0。完整实际 `argv`、cwd、工具路径/版本/SHA、起止时刻、原始stdout与规范化log SHA、输入版本均在每份receipt中。JSON配套审阅索引再次锁定这些receipt/log的字节SHA。

21、46、47是三个不同suite的有限检查标记数，不是完整模型任务数、连接矩阵覆盖百分比或形式证明；恢复测试会额外运行正常帧。旧FFN-r01的19标记/6609周期是保留历史尝试，本次最终FFN证据用r02，不能将两次重复累计成独立覆盖。

## 实际命令记录与复跑入口

root运行时的命令以对应receipt的 `runs[].argv` 和 `runs[].cwd` 为准。共同实际步骤为 `vlog.exe -version`、`vsim.exe -version`、`vlib.exe work`，然后：

```text
D:/EDA/modeltech64_2020.4/win64/vlog.exe
  -modelsimini modelsim.ini -sv -work work
  +incdir+<该次run的绝对source目录>
  <该次receipt.runs[label=compile].argv记录的全部源文件>

D:/EDA/modeltech64_2020.4/win64/vsim.exe
  -modelsimini modelsim.ini -c -voptargs=+acc -onfinish stop
  work.block_w3_ffn8_tb
  -do "onbreak {quit -code 2}; onerror {quit -code 3}; run -all; quit -code 0"
```

上面compile使用具名占位仅为省略长源清单，逐参数真实命令在receipt，不能将省略形式声称已单独执行。adapter运行将顶层改为 `work.block_w3_adapters_tb`；回归实际依次运行 `work.phase2_s_ctrl_tb`、`work.phase2_mst_tb`、`work.block_w1_mst_tb`，其余vsim参数相同。

交付后的复跑入口为 `run_w3_ffn.py --root <项目根> --suite ffn|adapters|all --output <新的空目录>` 和继承的 `run_w1_mst.py --root <项目根> --suite all --output <新的空目录>`；可显式加 `--tool-dir D:/EDA/modeltech64_2020.4/win64`。这是复跑方式说明，不是审阅者新增运行。必须使用新目录保留旧尝试；不要在已保留的run目录覆盖编译库、日志或快照。

## 源码与历史 metadata 的正确解释

运行时新增W3实现尚未提交，真实源码版本由输入文件SHA绑定，最终交付commit应另行记录；707只表示冻结原生叶源，不能把新增wrapper/adapter/TB写成在707提交中。当前 top/E/G 两adapter与FFN-r02实际快照逐字节一致，E/G两adapter也与adapters-r01快照一致；FFN-r01→r02的18个RTL/include全部未改。r02只追加TB错误门，FFN TB SHA为 `61e5427bc13f4ae24afbfd59645d4cfcfecd4ba3b628082ea691404e27ff2582`；standalone TB为 `7eabf9949d4d056e79efaff35f840dabdc94e31412c9d0b1bd748f674496e0f6`。

`regression-r01` 使用未改的继承 `run_w1_mst.py`，其中 `research_parent=bfe62ad...`、`new_W1_RTL/new_independent_W1_TB`、`execution_source` 中的W1字样，是原runner的历史硬编码label。本轮是在W3包中真实重跑旧P2/W1；不能据这些label把W3当前输入parent改成bfe62ad，也不能声称旧W1实现是本轮新写。保留原receipt不改写，以其实际origin、snapshot和逐文件SHA证明执行输入，再由本说明纠正语义；这不影响其真实工具退出码和日志结果。

14个锁定native源在runner编译前按原锁核验；但编译纳入不等于功能验收。FFN与standalone实际使用M/E/G/S/T或E/G/S的所列路径；N/R及legacy在本轮仅语法编译，没有功能、数值、延迟或物理资格转移。

## 有限功能与协议覆盖

FFN-r02使用6个独立冻结整数参考输入，逐阶段核对S464..473与最终一字。参考按Fin7→M RNE4→G SiLU门乘Fin10→A16/B8 down RNE7→E残差Fin10计算，正常帧检查15次M命令/应答、3个loader、32普通S请求/ACK（26写6读）、两E服务、一G服务及T TAKE/RELEASE。新增真实native E op14与单G fn4错误门分别检查无residual/mid目标写和无T发布，G检查4输入pair全部退休再结束；各自随后恢复新帧。done在stall中保持，abort+done_ready同边沿只消费一次。

standalone共36个数值/guard例与10个协议例。E有22例：op0..13各定向输入，FMA/SELECT真实第三操作数，E12 compact8且shift忽略，E13 S32输入与compact16/RNE/clip，tail防止虚假sat；invalid14/15走真实native error；count0/9、E13 count5、RoPE奇数count3走本地guard。有效count分布为3/4/5/8等指定值，不覆盖所有op×count×shift交叉积。

G有14例：fn0..3各gated0/1、count8，另有gated odd5、ungated单lane Softplus、native invalid fn4/count8及fn7/count1、invalid count0/9。没有明确逐例测试fn5/6，也不等于所有S16输入穷举。10个协议例涵盖E/G native输入捕获与保持、native输出背压、真实destination写ACK门、S请求/响应保持，以及E保留response和G多在途状态的协调reset/新service恢复。G输出stall实际检查至少2个pair同时在途。

正常service检查目标703写一次且在真实ACK消费后才response；错误例检查目标仍为poison。S read/localvalidation/native error发生在结果写之前时禁止目标写。若请求已被S接受，随后人为注入write ACK error，不能保证回滚；当前真实S helper本就没有普通原生error、rsp_error固定0，本轮不赋予额外存储故障检测资格。全suite Gissued65/retired61含协调reset取消4项，不是无条件不变量失败；同理FFN累计Sreq823/Sack821含被取消事务，不冒称全局req=ACK。

## 仍然未证明的内容

本核不使用N，没有preNorm/postNorm，也没有样本模型完整H/I、任意多字张量分配/回放、MEM/NUM、通用跨岛事务或完整F。后续加入preNorm必须分别保存原始残差X和归一化投影输入，不能仅插入N后把两者混同。仓库系统具有外存，当前profile没有实现或评价外存路径。

Fin位数和clip是本次明确选择的bounded数值合同；有限参考一致不等于真实模型质量、全部数值参数准入或全输入证明。abort/error的done_saturated只汇总已退休/已观察到的标志，不能推断取消流水内部未退休clip；已经接受的RAM写和已消费输出前缀不能回滚。没有CDC、综合/P&R、面积、功耗、时序或M11/M12产品永久绑定验收。

交叉审阅未发现阻断性问题，但作者互查和root有限测试不能替代项目要求的外部设计/PR审查。文件上传、审查批准、合并、看板同步和任务验收仍应分别报告。

交付归档位置：以上`runs/<name>`原运行目录的文本证据保存于`work/Melodydt/151/w3-rtl-evidence/<name>/`。统一索引为`work/Melodydt/151/w3-execution-index.json`；旧ffn-r01 TB保存在该轮previous-inputs。二进制编译库/全套原生副本不上传。数值参考重建/冻结TB再生成一致性检查及管理结构检查的实际命令和结果由w3-checks.json留存；w3-verification.json只复核证据，不重新执行仿真。
