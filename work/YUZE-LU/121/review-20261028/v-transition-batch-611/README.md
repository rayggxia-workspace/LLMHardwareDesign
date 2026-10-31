# 82处组合转接失败及实际归因

Refs #121 / PR #122。610/93816/node17自然FAILED。完整原生检查172→188：消除82、新增98；新增为84 Short、10 Cut Spacing、4 Metal Spacing（M2共88、via2共10）。原始数据库不变、557412普通NETS及精确路径/RECT/其余网token核对通过，不能抵消DRC失败。611收取14原始文件、5稳定输出绑定、320归档源Git与远端SHA；大ODB/DEF留获授权服务器并索引。verification.passed仅表示封存完整性，diagnostic_result=false。

从实际新marker双方网络关联82处修改，46个被改网络参与新增违例，无无法关联项。failure-analysis.json为原报告差分，不是另一次实验。排除全部46网后仅36处候选（22mixed/14stack），必须从原598副本重做全片检查，不能按单例相加或声称已无新增。当前588、端点连接/RCX/STA/完整GDS/最终功能/严格LEC/交付均无资格转移。
