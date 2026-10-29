# V355 归一化合并修正：六项数值／算术验证

Refs #121 / PR #122。源 `c654fc8412e16d49827917c8605b8901a915641a`，归档SHA `ac530a3dfb929c30edd86da38158052cfd506bdb90d879379d84d5310714c2b1`；主V RTL SHA `d0ac0dc37c3cbd114f5eba63d142c6cd3c5b2979007c658b2beff6e5601e80b3`。N_WRITE完整S128合并改用已有分组加法，未改变RNE、饱和或操作周期。

六项已实际通过：三初态各566999检查/414906拍；公共42、扩展36案例各两初态，全部measurement字段与348一致；组合/逐命令延迟各三初态；实际RTL函数提取的264bit无约束加减/RNE全值证明通过，真实单bit错误负例被拒绝。47原始文件、35稳定输出绑定、308源Git blobs及receipt输入核验，见[index.json](index.json)、[verification.json](verification.json)。此为六项完成时的快照；随后映射亦通过，七项已齐，见[映射完成证据](../v-map-355-complete/README.md)。

在现有R344/93237/node21上执行，父原生0–15保留，子任务16–95按五个16CPU槽动态补位；父192GiB、子16GiB/映射64GiB预测，1.2安全系数加16GiB guard/liveRSS保留，不新增allocation。原350继续收尾；后续占用/有限工作空间、全新物理、全部独立最终门及接口均须当前新源实际证据。
