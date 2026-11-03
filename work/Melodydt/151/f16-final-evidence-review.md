# F16服务器结果独立证据复核

结论：r02/job95209在声明的H8/I8整数profile和30个有限场景内有真实服务器Verilator通过证据。本代理仅只读核对下载文本、源码manifest/原提交包、独立contract与golden，并进行证据算术核验；没有启动RTL仿真、服务器任务或修改正式包。这不是外部PR批准、lint清零、完整F/模型质量或物理验收。

## 实际尝试与检查缺口

- r01/job95206，source `63ce0f3ddb9cc7bac67380dc20f7b5eb8d0f135c`，build exit1，未执行simulation。新top第125行`5'd16?10'd475`缺少分隔，被Verilator词法器合并为非法decimal token，日志有2个error。**此前我的数学/CASE静态检查和快速源码审查漏掉该SV词法问题；Python PASS不能证明可编译。** 不能将r01写为就绪/通过，失败回执及日志原样保留。
- r02/job95209，source `b77d6b7bae17e265bf20509e9ea53c1cdc5c4c9d`，node1/c64、8CPU，Slurm自然COMPLETED/0:0，用时00:00:56。Verilator5.042、G++11.4.0，在SHA `c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df`的容器内`--binary --timing`构建，compile/sim均0。
- 原r01/r02提交包及manifest比较显示，提供的SV/SVH中只有新F16 top变化；读回两包该文件后去除空白完全相同，修复是该行三目表达式的词法分隔，没有改数学profile、golden或CASE集合。

## 源、场景与数值证据

独立核对154项读回条件：23个下载证据文件SHA、各命令日志fingerprint、r02输入manifest/实际提交commit及本地formal文件、完整有序30CASE集合、唯一精确`PASS_W4_F16 cases=30`、无失败文本，以及warning和计数。与前W5-IF包比较的34份继承SV/SVH全部字节不变；这不将本次结果转移成旧宏/路径的新资格。

| 绑定对象 | SHA256 |
|---|---|
| r02 run-receipt | 3821237141e001a1d4bd457cd1ea39a024d019e357f3bedc8eb89e874f8e8477 |
| r02 simulation log | 0bc670264a019f726a4132c6405ed1a6a7698051820015bc0360d68af9400411 |
| r02 build log | e6da2cfe2ff69f73fbb7e3073ba8f99cdcdc617d97f75e508de263a00d7d20a9 |
| 修复后F16 top | ea0d040d6e67ed847e21c22cfef5605e484ab14afd2fc9851fbf9e3c3169ed27 |
| 冻结TB | 9ce2664937ab092e817fad56cbe14bd85785b06fdc06ee516655b3859e8f1de9 |
| 冻结10组golden | d170f0ef732418f999f64d31a2d4209a8ea3130fb0f20429c2d4df37ca3568d3 |
| 独立30CASE合同 | 8d15e922ab7777e5e4ecbda970d5e7930169927fa463a63b613654eeb1d4aa1b |

10组数据检查了完整S16 X、非8倍低位、可变gamma（非unity、零、负值）、固定随机与正负边界饱和。zero-gamma两组输出逐位等于原X，残差未被S8窄化；N RMS8/epsilon_code1、三个wide A投影RNE7、G SiLU门乘RNE10及原X相加均按独立整数参考逐阶段检查。没有从DUT输出生成expected。

30CASE还保留输入/padding/末字ACK启动门、held start、重复、输出/完成反压、prestart/running abort/reset、已有DONE+abort+ready唯一消费，以及S/M/N/E/G受控故障恢复。S故障是在helper响应error边界注入，不等于原生S有错误检测器。全部CASE名称与原独立合同逐项一致，无删除故障用例。

正常成功帧逐次验证39个S请求/ACK=29写10读，M15/15、loader3、N4/4、E2、G4pair接受/退休、T1字及release。实际suite为19250周期，`input701/Sreq1439/Sack1436/M488/488/N150/150/Ttake30`。独立按29个正常成功帧，加一次已消费T前缀后abort及其余14项取消/故障事务重算，所有数值完全相同。S差3分别是入口写ACK、RUN原X466写ACK、N474目的写ACK在协调abort时取消；S helper错误是在真实S ACK后注入，未造成额外ACK差额。M/N响应无全局差额。Ttake30包含那一次已消费前缀，不能据此声称30个正常成功帧或回滚。

## 告警与接收边界

r02保留24条编译warning：TIMESCALEMOD14、WIDTHTRUNC3、WIDTHEXPAND7。实际仅有`-Wno-fatal`，没有按类别屏蔽warning；build exit0不等于lint clean。r01词法error没有靠该选项绕过，必须修复并重新真实编译。

本次只接收明确的H8/I8、X/gamma S16Fin10及权重S8Fin7小核profile与所列场景；不覆盖所有整数/故障组合、连续数学近似误差、真实模型精度/shape、完整F/L4、MEM/跨岛、完整产品ROM/M11M12或PPA。根任务负责正式整合、远端交付与所需外部审查；此复核不改Issue验收状态。
