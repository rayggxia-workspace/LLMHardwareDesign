# 原生联合闭环：补充进展（2026-11-11）

任务保持 [Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250) in_progress / [PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251) draft。没有达到旧条件9.215647 token/s，也没有完成整系统300MHz。

## 已测证据与费用

- RF：乘法、RNE、末级实际读前态三段。16×8 S32持久数据仍512B；2×465bit有限算术owner加单响应，head同context可II1。18RF与18独立scale测试通过；ready独立旁路另18+18通过。提交和CSV在 rf-ii1/run-01、run-02。
- M：实际产品18run102228、generic102229通过；额外4×37bit响应身份FIFO18.5B，防止后发head组覆盖先发结果身份。普通与head INPUT11、CONTINUE16、FINAL18，仍保留head八次RNE。实际单active guard连续core间隔21，不能套理想17。
- 物理：原单级真实placed/CTS失败、常量one_/zero_错误PG分类失败均保留。改用实际LOGIC1/0 tie单元计面积；新RF source继续原Lib/TT300MHz P&R，尚无最终合格M。最终outline和core利用率均须不低于main；不得用mapped面积或placement报告代替验收。
- MC：实际942scope检测出1+26×36+5重复，131静态指令/1184B，3596实际取指、1304 CALL逐项等价；630控制测试通过。描述符166912B在DDR，实际取参、CRC和仲裁有成本。
- MC→LC：102226真实MC bank PM、四128flit、1KiB LC PM实际bootCRC/取指、128B DDR scope和124拍CRC、typed decoder/六票range、四flit返回18PASS。record完成仍由peer提供；不代表M数值通过。
- typed范围：102241六seed×三初态18PASS。service1为LOCAL_CONTIG_RANGE，输入A16整像从K0开始，占full_k/8个S128字，检查完整跨度及输出/快照不重叠。service2是候选streamed outer，service3 wholeFFN保留，均拒绝。
- COPYscale：102253有限发送/接收协议18PASS，包含逐端点帧数、错误producer/全key/metadata字段、未知错误ACK不夺owner、halt不撤回已offer、延后消费和两类真实drain门控。尚未与真实S数据复制/A/M联接，不能把协议单测当成数据路径验收。

## 当前性能结论

固定decode512 trace、51.2GB/s、同字节/权重记录与有限资源审计下，102238采用已测RF费用和guard gap5，条件结果8.136179 token/s。关闭G重叠8.017249、四票8.091893、关闭A预取7.945371。gap3的8.507534和gap1的8.605452仅候选。硬件RF变化、控制实现费用、纯排程变化分列；不能把改费用或硬件收益称为DP20%。

E/N与动态S32 QK/AV仍未原生资格；当前decode trace没有全部数值payload。动态Dot必须恢复原full-K exact sum后仅末尾一次RNE/saturation合同，不得改成每K128舍入。3×signed16 radix2^15、5×signed8 radix2^7与有界80B临时merge正在实现，不扩大持久S32/SRAM。

## COPY元数据合同

两个128bit头帧复用现有数据链路，DATA位宽不变。tag高16位generation；低16位0x8000为完整key，0x8001为header。既有S数据tag的[15:11]为0，接收端必须拆出头帧，不能把头写入S。

header从高位到低位为：ABI16=0x0251、tile bytes16=256、K元素偏移16、shift6、reserved10=0、session32、ticket32。偏移必须128对齐；A/M接口的K128索引须显式右移7，不能同名直连。

source只能在16个A16目标字真正写ACK后启动（written_mask=ffff且无producer error）。接收端注册完整expected lease身份和一个6bit pending shift；第二帧ACK只证明shift已真实捕获。它允许先COPY、稍后A load消费metadata；释放还需实际数据/消费者排空。头帧成功不等于A消费完成，也不等于S复制完成。generation耗尽必须真实排空重臂，不能静默绕回。

## 接续工作

实际P executor连接M短命令、真实S/A、RF/guard写ACK和LC完成；globalDMA实现有限32beat/32descriptor每channel、partial CLOSE、实际FENCE与代际重臂；COPYscale→真实S/A及scatter、streamed outer继续补齐。五类仍为独立叶宏和局控/适配逻辑的控制分组，禁止回到五个大硬框。不扩私有SRAM；所有寄存器、FIFO、PM和端点成本单列。

所有失败、负性能与取消记录保留。大物理原包保存在授权服务器并逐SHA索引。本地盘满用可恢复稀疏checkout和迁移自有缓存处理，未删除实验历史。未经完整联合/物理/数值验收不宣称完成。
