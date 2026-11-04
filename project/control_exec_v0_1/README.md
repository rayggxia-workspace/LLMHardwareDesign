# 二进制母控／局控执行模型 v0.1

Issue179 / Draft PR180第4步，正式说明见[CONTROL_EXECUTION_MODEL_V0_1.md](../../docs/local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)。这是Python有界控制解释器及协议peer，没有控制RTL或完整Block。

- machine.py：从已装载的完整镜像按PC读取16B机器字，执行母控／局控、有限服务、holding与S字节存储；运行端不读取cases.json／golden_traces.json或选择预写程序脚本。
- compare.py：把观察中的操作／路线ID映射到人工参考，执行既有属性oracle，并比较接受事件／payload集合及退休PC；不补造事件或在属性检查前改排序。job／任务序号来自独立主机预期。
- scenarios.json：外部数据包模板、延迟、背压、随机种子和M错误注入；无PC脚本或内部RAM初始化。
- run_campaign.py：加载7份既有镜像，运行9次实验并在运行结束后对照参考。
- run_reports.json：9次真实解释执行的事件与退休指令，合计100次退休、193观察；不是人工轨迹或RTL结果。
- test_machine.py：26组执行检查，包含8种随机种子×3案例、改变机器码、连续任务、背压和失败实验。

在仓库根执行，仅Python标准库及同仓库已有参考模块：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B project/control_exec_v0_1/run_campaign.py --output binary-runs-check.json
python -X utf8 -B -m unittest discover -s project/control_exec_v0_1 -p test_machine.py -v
```

binary-runs-check.json应与run_reports.json逐字相同，临时文件不上传。所有既有四套单测命令在[ARCHITECTURE](../../docs/ARCHITECTURE.md)，本轮共107组。

运行入口Machine(admitted_loader, environment).run(job, epoch)，loader须经BEGIN／WRITE16／VERIFY／COMMIT到READY。程序快照绑定manifest及实际字节；重装后需新建Machine。正常／已排空M错误终态后loader回READY；连续job不重装、不复位S，任务序号递增。改变字节会改变实际执行，独立参考可报告差异。

上限为1母控＋2局控、每局控1任务／1对象／1在途服务、16KiB S、8个holding通道、2个链路槽、2个外部数据包、2048观察、每实验最多1024调度tick。控制传输以整包握手建模；tick不是硬件周期。仅支持现有直线profile的14类指令和M op6／RAW16传输；循环／分支、其他服务、实际S bank仲裁、运行取消／provider协同复位与迟到响应仍待扩展。ModelBound只表示实验界限耗尽，不是架构错误终态或死锁证明。

M错误为显式非正常peer注入；存储是实际有限Python bytearray，不是S RTL。报告instructions_executed=true只说明解释器执行机器码，rtl_tested始终false。现有loader.START自身仍只准入，不执行PC。未启动服务器作业／自动监测，不计为模型数值、Block、物理或性能通过。

