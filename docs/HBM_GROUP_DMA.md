# 分组仲裁与多 S 描述符 DMA 的 RTL 合同

任务 [#181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)，更新同一 [PR182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182)。本阶段把原C++架构夹具中的多S搬运、信用/事务槽、组间/组内轮询及完成处理改为实际RTL；原架构实验保留为历史参考。

## 实际结构

```text
主机/程序：每S提交一个描述符
  → hbm_group_dma（300MHz）
       描述符与游标、每S有限事务槽、S端口状态、两级轮询、完成保持
  → 每通道185bit请求异步FIFO
  → 外存用户接口模型（默认500MHz）
  → 每通道146bit响应异步FIFO
  → RTL tag/状态/通道路由检查
  → 各S真实普通口写入/读出及ACK
```

实现：`project/rtl/hbm_feed/hbm_group_dma.sv`。原S/feeder/M与原异步FIFO源码保持身份。验证组合`hbm_dma_system.sv`实际实例化4组×4S、4个通道CDC对和一个共享M数值验证器；每例选择部分或全部S。M共享选择网络属于测试组合，不能作最终物理拓扑或扇出优化证据。

## 描述符与有限资源

每S有独立valid/ready描述符入口，字段是：方向（0=LOAD，1=STORE）、40bit外存字节地址、10bit S字地址、11bit字数、16bit任务tag。数据字为128bit；S容量1024字=16KiB。每S最多一个活动描述符及一项保持的完成；完成未消费时，不接收下一描述符。

默认每S8个事务槽，可选配置信用1..8。槽保存状态、16bit内存ID、9bit代次、10bit本地地址、40bit外存地址和128bit有效载荷。信用统计包括等待通道请求寄存器/FIFO、等待内存响应、待S访问和S确认的槽。主机不能以软件轮询替代这些硬件状态。

描述符检查：长度非零、本地范围不超过1024字、外存16byte对齐、40bit地址范围不溢出、信用及通道配置合法。最后一个可访问外存字`2^40-16`允许长度1；起点相同长度2拒绝。非法描述符返回status2，不分配槽、不发内存/S请求。

通道配置允许1/2/4；组g映射至`g % channel_count`。**channel_count在复位至所有请求/完成排空期间保持不变**，不支持活动传输途中重映射；credit_limit在描述符接受时锁存。原型面向GROUPS≤4、S_PER_GROUP≤4、NS≤16和SLOTS≤8。

## 组间与组内轮询

每通道先按group_rr扫描组，再按该组local_rr扫描S。每次授权恰好一个128bit字；指针在RTL实际分配请求寄存器时推进，通道请求被背压时保持全部payload。没有无限长授权。

LOAD有未分配字、空槽及信用时参与；STORE有真实S读回payload时参与。某S的槽被背压占满，会退出新LOAD资格；同通道其他具备资格的S仍可被选中。每个组只映射一个通道，避免同周期两个通道修改同组指针。

每通道只有一条128bit/core-cycle请求入口，300MHz理论请求有效字节上限4.8GB/s，4通道合计19.2GB/s；S访问状态机、bank时序和背压会进一步限制。不能直接沿用上一版C++模型每用户周期多字的带宽数字。轮询机会公平与外存最终服务公平是不同层次；模型/平台若永久不返回响应，RTL不能保证描述符完成。

## LOAD、STORE及完成

- LOAD：分配槽及外存读请求 → 按ID接收响应 → 槽持有数据 → 驱动对应S写口 → 请求接受后等待实际S写ACK → 释放槽并增加成功字数。
- STORE：先为当前S分配槽 → 真实S读请求及返回 → 槽保存payload → 参加两级仲裁并发出外存写请求 → 收到成功写响应后释放槽及增加成功字数。
- 完成必须等全部字分配完且全部槽排空；失败任务等已分配槽排空。status0成功，status2描述符/配置错误，status3外存响应错误。complete_tag/status/words在背压期间保持。
- 读/写响应报错后，该S停止分配新字，**已经分配的字继续排空**；不是原子回滚，目标区间视为不完整。其他S正常继续。已准备但未发出的STORE也属于已分配工作，可能在错误被发现后发出并排空。

## 内存事务与响应归属

外存请求185bit：`write1 | id16 | byte_address40 | data128`。响应146bit：`status2 | id16 | data128`。不是真正AXI或JEDEC接口；后续需要独立的AXI/位宽/所选HBM控制器适配。

ID布局`generation9 | S4 | slot3`，响应必须匹配活动S、槽当前ID、预期等待状态及通道。槽代次减少紧邻复用引起的旧响应混淆，不是无限期旧响应保护。不同ID允许乱序返回；未知/重复/错状态响应置sticky protocol_error并停止新分配，不能把其认作成功。

protocol_error属于破坏传输合同的错误，需要平台协调reset/flush。reset同时覆盖DMA、两侧FIFO和外存模型队列；不能只复位DMA而保留旧响应。正常reset不清除S payload，后续使用区域通过描述符重新写入。

## 验证与边界

新的C++夹具只接受RTL发出的内存请求、提供有限HBM式时序响应、提交描述符和核对oracle；不访问S内部数组，不控制RTL轮询、事务ID、游标或槽退休。原版S供数给原版M检查完整8×32×8矩阵；STORE独立核对真实S读出的全部字节。完整模型/并行计算及M结果适配器不在本续作目标内。

执行入口：`python -X utf8 -B project/experiments/hbm_feed/launch.py --rtl --attempt <新名称> --package-dir <新目录>`，经Slurm使用新服务器目录；原作业/证据不覆盖。运行器执行Verilator lint、Werror构建、多配置/背压/错误/复位测试、坏payload负控制，以及4S与16S完整DMA核心的Yosys通用门级综合与check-assert。

综合通过不代表300/500MHz物理时序、工艺面积、功耗、扇出、HBM协议或PHY/封装通过；这些后续单独验收。最终运行结果与源/输出绑定见后续结果报告。
