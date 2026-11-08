# 可综合PM与统一装载启动入口

Issue179 / PR180，负责人Melodydt。`control_boot_top`在当前双P控制顶层外接入三个DUT内PM和一个统一管理入口。母控/局控的64 bit执行ISA保持不变；下面的4 bit命令是主机管理接口，不是新增的执行指令。

## 硬件与接口

PM各16 KiB、128 bit访问、16 B对齐、1笔在途。默认`PM_USE_SRAM=1`实例化每端4个既有OpenRAM bank，共12个PM bank；`0`选择可综合同步RAM。两颗P的数据S仍分别属于原P组，未与PM共用。PM复位清协议状态，不清存储数组；复位后必须重装、读回验证和部署。

主机请求使用`cmd_valid_i/cmd_ready_o`，携带4 bit操作、2 bit目标、14 bit字节地址和256 bit数据。响应使用`reply_valid_o/reply_ready_i`，携带16 bit状态与512 bit数据。每次一条命令，响应保持到接收。目标0/1/2为MC/P0局控/P1局控；全局命令目标3。S读写目标1/2分别是P0/P1数据S。

| 编码 | 命令 | 请求数据与行为 |
| --- | --- | --- |
| 0 | RELEASE | bits31:0释放序号，63:32世代；要求整个复位组都可释放。 |
| 1 | BEGIN | generation[31:0]、总字节[47:32]、image[79:48]、topology[111:80]、ABI[143:112]、capacity[175:144]。 |
| 2 | WRITE16 | 对齐字节地址、data[127:0]，从地址0顺序写完整镜像。第一字检查版本2及MC/LC角色。 |
| 3 | READ16 | 写完整后从地址0顺序读回，响应低128 bit为实际PM读值。 |
| 4 | VERIFY | 要求全部写完与读回，比较硬件CRC，再提交核心头部/格式验证。返回写/读CRC于[31:0]/[63:32]。 |
| 5 | PREPARE | 只允许验证通过的镜像准备部署。 |
| 6 | ABORT | 撤销当前候选；后续需要新的generation或组复位重装。 |
| 7 | DEPLOY | data[31:0]为generation，三端必须同generation且都准备完成；等待三端实际image_valid再应答。 |
| 8 | START | job[31:0]、epoch[63:32]、sequence[95:64]、generation[127:96]，保留位为0。 |
| 9 | STATUS | 查询部署、候选、运行、结果和故障状态。 |
| 10 | RESULT | 获取并消费实际MC结果；只有主机接收响应时才消费MC结果。 |
| 11/12 | S_READ/S_WRITE | 对齐字节地址；写数据低128 bit；运行、链路未闭合或结果未消费时拒绝。 |

无数据命令及未声明字段必须为0。装载中的WRITE/READ由管理器维护严格地址顺序，不允许跳过读回后直接PREPARE。CRC32使用IEEE反射多项式0xEDB88320、初值/末异或0xFFFFFFFF，按镜像小端字节流处理；每个128 bit存储字用128个时钟更新，避免单周期长CRC组合链。CRC用于读回一致性检查，不能代替镜像权限认证。

所有底层cfg、release、deploy、START及PM端口封装在新顶层内部。主机未提供可绕过CRC的proof端口。三个镜像先各自准备，再共同部署；被拒绝的BEGIN保留现有已部署组，接受新BEGIN则撤销旧组部署并要求完整的新组准备。运行中禁止修改镜像和S，状态查询及结果读取保持可用。

## 状态与结果

0为成功；核心原有状态1..12原样传播。管理接口状态0x101未知操作、0x102目标非法、0x103字段非法、0x104读回CRC不一致、0x105未就绪、0x106任务/数据/结果义务未闭合、0x107顺序或世代非法。CRC不一致会向核心发送ABORT并撤销候选，不能继续PREPARE。

STATUS的[2:0]是image_valid，[5:3]为poison，[8:6]为prepared，[11:9]为verified，[14:12]为begun；bit15部署许可、16运行、17链路未闭合、18结果有效；[31:20]为三端life，[63:32]部署generation，[95:64]释放epoch，[127:96]最后START sequence。

RESULT的[31:0]job、[63:32]epoch、[95:64]sequence、[111:96]任务状态、[143:112]错误PC、[151:144]来源、[183:152]子错误PC、[215:184]失败任务序号、[247:216]确认读字节、[279:248]确认写字节、bit280溢出、bit281饱和。其余响应字段为0。

## 复现

按`control_frontend_v1/stage.py`及输入锁准备native-p、既有OpenRAM bank模型和工具。全部仿真在获授权服务器执行。

```bash
python3 -B project/control_presynth_v1/check.py
python3 -B project/control_boot_v1/test_pm.py --stage "$NATIVE_STAGE" --bank "$SRAM_BANK" --verilator "$VERILATOR" --yosys "$YOSYS" --jobs 4 --out results/pm
bash project/control_boot_v1/run.sh results/boot
python3 -B project/control_boot_v1/check.py --stage "$NATIVE_STAGE" --bank "$SRAM_BANK" --verilator "$VERILATOR" --yosys "$YOSYS" --out results/structure
```

`images.py`输出三端镜像、加载参数及Python zlib独立CRC参考。新测试台只驱动上述外部端口，DUT不包含`network_pm`或测试台供数路径。验证正常、连续任务、装载CRC期间复位、读回破坏后恢复、混合/旧世代拒绝以及显式ABORT恢复；每个后端运行三种初态。

当前RTL候选仍为单时钟、两个目标和固定P0到P1路线。核心继承旧格式兼容；新管理入口只接受版本2。组复位后新的epoch由可信主机提供，不声称非易失跨复位抗回放。两后端功能与综合结构分别验收；新增组合映射、时序、面积、功耗、宏视图和完整物理仍待后续步骤，不沿用旧局控组合的物理资格。
