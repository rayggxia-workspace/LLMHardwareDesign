# 当前候选接续队列准备

Refs #121 / PR #122。十五个固定队列的远端manifest/queue与本地文件、归档Git dispatcher/dependency及archive SHA已核验；config.json只授权这十五队列。controller替换尚未执行，此提交仅封存准备结果。既有555继续看护R404及旧553。

新576使用dea3c22b、归档5e45946f，576/577/578从此归档执行；579/580使用helper39f32da4、归档c18d8882，51份RTL/C++与576逐字节一致。576已实际提交93775/node16，七项行为/逐拍/算术PASS，mapping仍运行；577测量、578六阶段、579全部最终门/交付/完整几何、580逐端口与有限RC均stage，未宣称通过。573/93776/node20是旧523副本上一个M3 via-pair替换试验，使用同一已封存576源码归档，仅诊断，不改变当前V。

本Issue≤8 allocations，含旧/PENDING/UNKNOWN；c96六个16CPU独立任务槽即完即补。暂时减少活跃槽仅因真实依赖；单个PNR不可伪造独立副本填空。R与现有EDA不因慢或安静取消/重启，不触碰其他成员任务。所有最终门仍必需，M/S/T不重复。
