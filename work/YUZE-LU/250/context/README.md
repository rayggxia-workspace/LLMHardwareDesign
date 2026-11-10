# 有限S32投影上下文单元

2026-11-11，Issue250/PR251，持续实施中。16×8×S32=512B数据及实际owner/K游标元数据，group128和head group16，每组独立FP16/RNE；CREATE/RESTORE/STEP/SPILL/DROP。连续同ctx旁路、16槽占满拒绝别名、第17对象、86个Down输出组经spill/restore、不合法身份/K序、部分/最终溢出不改原状态、复位取消和背压保持均进入独立状态机/Fraction预期检查。

102098首轮数值fault返回nextK未归零，独立检查拒绝；未修改检查来通过。RTL统一故障nextK=0，保存原失败日志。102099六seed严格Wall通过，持续接收每拍一个命令的旁路覆盖和随机背压均过。完整源/工具/回执SHA在index及不可变归档，归档不是执行提交。

输出SPILL/FINAL被真实有限持有槽接收后才释放RF；S快照仅在外部真写ACK后可用于restore。本单元不提供S/MC传输、不验证上游ACK真实性，也不是完整M或物理/整模型证明。单元一个scale输出级的32B存储、512B RF及metadata都应计入组合M面积。

下一步将W记录前端、raw M、RF/scale及真实2结果槽和局控联合，接head真实scale、四FFN新profile和最终物理。未达总目标不停止、不标done。

102106六seed严格通过：SPILL/DROP新增实际RF的fullK/group/n返回，故意不同的LC描述符元数据不能改变快照身份。该修复避免在完整M增加重复shadow表。执行源5aa1ef242，组合同步该接口。
