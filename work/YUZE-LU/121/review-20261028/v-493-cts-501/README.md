# 新493 CTS阶段证据

Refs #121 / PR122。实际493/93618/node25完成CTS并进入GRT，15原始文件、311源Git blobs及远端SHA完整绑定；内部LEC53478输入/53467输出、diff0/1均0、UNSAT/IDENTICAL，5187时钟网均为none。

CTS setup WS−0.0383897ns/TNS−0.111982ns、5违例；hold WS−0.23009ns/TNS−2.83478ns、40违例；maxcap/maxslew均0。这是布线前阶段结果，不能当作最终300MHz验收。配置实际DIE_AREA=1250×1250µm、CTS标准单元面积706956µm²；与旧476的1260²外框分别记录。

实际源4399685bceca5f4364a9f601c5f23a6ecebe912a、归档089a274e39ad11a44c7f8461e4ad2deb186709b18cb6a157d5ce8c1527f68c50，与485/486/492前置保持同一计算RTL。不得继承旧476/477的功能、LEC或物理资格；本次493最终RCX/时序/电气/DRC/网表门/文件/几何/接口仍须完成。

原始路径、SHA、配置与实际metrics见[index.json](index.json)。不改在跑任务、源归档或已封存数据库。
