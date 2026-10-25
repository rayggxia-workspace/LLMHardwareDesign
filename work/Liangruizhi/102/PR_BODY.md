Refs #102

补齐单16KiB/8S8/1S32预算的完整GQA8头注意力电路：Q8/KV16真实输入经三遍整数softmax到PV32，prefill与实际cached输入分列；修复缓存A→B→A复用漏洞，绑定单owner/单调version/scale及显式caller committed前缀。

服务器两路各79query/632head与71cmd同core恢复独立通过；原mapped gate两等待18query/144head与RTL逐字段一致并独立数学接收。实际宽算术/移位/元数据计入53,187.764µm² logic-only；严格库存8S8/1S32/唯一16KiB。58作业51完成/3失败保留/4自有失效依赖取消，完整677232014B服务器、精选365258B入仓；双包/精选/10phase149源字节验收通过。管理结构/AST/JSON/diff检查PASS。

没有online softmax、KV append/淘汰、投影/RoPE、M/A/R真实共享、整模型INT8质量、SRAM/ROM宏/时序/物理资格。门级只正常完整消费者子集，错误/abort/terminal注入仅RTL。完整报告docs/experiments/issue-102-attention-rtl.md。

规则rayggxia-project-collab1.0.0；身份Liangruizhi/182389313；登记management-hub PR5 pending；看板缺config/read:project，unverified/同步pending待管理员。未自行合并或done；审查人待指定。根会话负责push、PR、Issue及远端读回。
