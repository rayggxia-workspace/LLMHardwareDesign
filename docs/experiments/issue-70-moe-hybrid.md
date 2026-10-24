# Issue70：小MoE与并行Attention/SSM最小实验

2026-10-24 UTC+08；Liangruizhi；Issue70，承接PR69@ab2edaa。先冻结下表，再运行真实模型；当前未执行不写成功。用户仅授权新增Granite与Falcon两模型，Phi封存，成员Issue55/63不接管。

| 决策 | 真实差异/候选 | 最小实验与观测 | 分叉标准 |
| --- | --- | --- | --- |
| G1 路由/专家是否固定连线 | Granite40专家top8，非dense | B1 pre64/decode8，一层完整MoE；W8A8 router重新top8与FP固定路由诊断分列 | 路由会变则保留动态索引/dispatch，固定连接不能只覆盖所见专家 |
| G2 RQ/合并归属 | 8expert down输出单位不同 | 完整K整数dot、两激活scale、共同S32+Q31重标/Q15权重/S64合并 | 不同unit禁止直接INT32相加；宽乘/归约及metadata是资源义务，位置待同资源校准 |
| G3 S/分发缓存 | 稀疏专家集/访问偏斜 | actual routes/shape；独有权重下界与无复用访问量分列；48KiB S32 return与S64acc容量 | V16KiB整物化不可行则tile/stream/显式S，不能赠缓存或以unique bytes冒充带宽 |
| F1 R模板泛化 | Falcon Mamba2与GDN更新不同 | 一个完整hybrid层真实连续输入；FP64 recurrence，S16/S32状态存储诊断 | 不把FP桥候选称整数R；R控制微序列/共享B-C组需显式，完整head超32KiB则分页 |
| F2 跨head消费者 | gate后4096共同RMSNorm | raw scan/gate/gamma与完整归约，存储/重读下界 | 不能各head单独norm后拼接；V16KiB无法整48KiB免费驻留 |
| F3 A/R并行归属 | 同输入分叉、两支汇合、KV增长/SSM固定态 | pre64/decode8、原生chunks1/8/16连续，真实branches/cache；相同wire资源账本/合法传输 | CPU执行顺序非目标并发收益；未过数值门仅结构诊断，宏归属/PPA仍待真实端点 |

Granite官方revision a02780686e08a03fe0d2679a293b5c74a90efa89；Falcon 01087ec4c132d7f186908716b3530ea187f062a1。官方API原字节metadata和SHA在work/Liangruizhi/70/models；服务器网络失败后以本机D盘中转，服务器复核；以LFS SHA/小Git blob核字节并读取safetensors header dtype，不依赖配置推测权重精度。各阶段源码/输入/output SHA及实际实现另冻结。来源为官方模型卡/config与安装Transformers5.20.2，动态main网页不代替固定源。

Granite固定seed20261024、独立cal/eval文本，pre64+teacherforced decode8，数值只取4prefill尾+4decode，共8token完整8expert路径。2激活scale×2路由×2阶段=8个观测；FP64SiLU/softmax、scale编译桥保留。参考一致性预定relativeL2≤2e-4/maxabs≤2e-3，两者均须满足；并非模型质量阈值。

Falcon固定seed7002，独立16校准token及72评价token，pre64+decode8，只一个完整层细采。参考门预定：full/cached最终logits、layer0 chunks outputs/cache relativeL2≤2e-4且maxabs≤1e-2；hybrid join≤2e-6/1e-3；独立FP64 head state/y≤2e-4/1e-3。每项原始误差保留，不事后放宽。S16/S32 storage只作诊断，FP64系数/更新不称真正整数递推，不跨模型移用Issue68同范围S32结论。

所有实际模型/数值与服务均本人CPU服务器新issue70-moe-hybrid-20261024目录Slurm lrz-i70-*，独立out不覆盖，原权重只读复用。启动前只读盘点c96有1344空闲核，node13空闲且约503GB free；其他成员89448/node3未动，两个模型未发现已有目录。每模型先8CPU参考，并行上限不超实际申请；不安装新环境或启动其他机器。

同资源部分仅对相同声明精度/任务比较容量、打包和端口/传输，不把FP桥路径称全整数，也不把有界传输当完整compute。维持V16KiB/R32KiB/M32KiB/S8×32KiB、1RW128bit、32Bheader/16Bbeat、payload1984/FIFO2KiB；宽算术若未校准只列义务/拒绝/条件成本。出现无法实现的候选须明确拒绝。

至少双轮或独立接收；独立Python整数dot/RNE/merge和FP64 recurrence，原始SHA与真实篡改负例分层。大数据与权重留授权服务器，仓库只放精选、结构化指标、源码、命令、日志、版本和SHA索引。登记PR5 pending，看板unverified/同步pending待管理员，审查人待指定；未审查合并非done。

## 执行日志：来源与传输

首轮服务器90152/90153下载失败（URLError，登录节点官方及镜像metadata连接超时），原始失败保留。依赖90154/90155未执行，核对本人job后取消，以新任务替代。未改变TLS或系统网络配置。2026-10-24约15:10 UTC+08，本机D盘官方固定版本下载完成：Granite 6,602,372,644B、Falcon 6,304,067,182B（含配置/tokenizer）；四个BF16权重分片均与官方LFS SHA256一致，小文件与官方Git blob匹配。仅传输中转，未在本机加载模型；新server models-relay目录将再经Slurm复核，之后只读使用。ModelScope公开镜像完成元数据/HEAD备用调查但未采用，不能称其字节已验收。

源码生产/独立接收/传输共59项边界测试通过，check_project通过；这不是实际模型数值验收。传输审计已补Falcon先gate后norm的首扫gate及三输入residual+A+R汇合，避免少计通信。实际结果、Slurm和SHA后续追加，不覆盖原失败。
