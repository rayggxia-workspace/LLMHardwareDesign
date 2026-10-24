# Issue74 执行前冻结：完整MoE与分组重标边界

2026-10-24 UTC+08，负责人Liangruizhi；[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)，承接PR73@88e9c4b2c3bb1b93b7155ba87ad11853e6c15512。新根D:/Projects/LLMHardwareDesign-moe-grouped，task/74-moe-grouped；三个独立子worktree/branch见work74。全部真实模型/张量/数值/服务通过本人新服务器目录/public/home/yuzelu/RuizhiLiang/issue74-moe-grouped-20261024的Slurm lrz-i74-*；PC只源码、微合成测试、元数据/字节接收。旧70/72原样只读，无新模型/Phi解封/其他机器/成员55与63接管。

## A 完整Granite cut

最小层0稳定基线+13原敏感层，calibration/evaluation各原72token，报告prefill64/decode8。只读官方revision a02780686e08a03fe0d2679a293b5c74a90efa89的已有BF16权重，核原receipt/shardSHA和实际header键/loader转换。新model64条件参考保留内部FP32 cast与旧native32 FAIL；新增真实post-attention residual hook、post-norm和下一层inputnorm gamma/输出，禁止从最终hidden减MoE倒推残差，禁止拼旧FP32专家输入。

闭包：真实post-attention residual的明确整数编码 → 完整post RMSNorm → 实际integer router dot/top8/Q15 gate → 全部8个所选expert gate/up/SiLU/门乘/down → 明确共同Q12 down RQ → 全8路宽weighted merge/RNE → residual_multiplier0.22的Q20编译 → 加真实残差 → 下一层完整input RMSNorm。Attention计算及更后层是外部边界，不称整模型质量或完整GPU推理。

只比较R8/R16动态router两种能力；专家统一W8A8/完整K INT32，向量/缩放/LUT/边界由GRANITE.md冻结，calibration与evaluation隔离。current integer row选择激活单位，不读取native误差/未来值；权重与静态系数只离线编译。共2层×2router×2split=8最小数值任务；不盲跑旧静态/选择性合同，后者已全部回退。不能把不同RQ/舍入顺序当placement，运行时封闭段不得FP桥。

下游norm、全部8expert、完整K和merge的码/单位/溢出/饱和必须保留；独立接收逐stage与真实SHA重写负例。没有确认的应用质量预算，不以局部L2宣布质量PASS；完整整数执行和数值误差分列。完整链失败保留并解释，不挑有利token。

容量义务：单层全部40expert W8约94,371,840B，两层不能同驻EXT128MiB；分层独立数值profile不意味着双层同时部署。每expert完整512维mid选择动态单位需2KiB整数缓冲或重读；8路完整S32输出49,152B，S64 merge12,288B+一份output6,144B超V16KiB，需真实流式tile/端口/背压。

## B 分组函数的匹配部署

只读复用72已独立接收同gatedinput/W8/scale与g0/K512/K256完整integer函数，每种函数分别比较M驻留对齐/RQ与V驻留，不跨精度或数值函数排名。混合单位完整K先I64对齐/累加，再一次最终Q31/RNE；不能逐组RQ冒等价。g0 control须逐码复现原whole。

守恒M25616×16/B1有效16PE、合计8S8 VR lane、单SFU和4,260,100B ROM、M32KiB/V16KiB/R32KiB/S8×32KiB/EXT128MiB，128bit1RW/单BUS、32B header/16B beat/payload1984/FIFO2048。M旁不赠ALU/端口/寄存器；使用同VR8接口，所有operand/回写/重排/metadata/partial/weight/consumer都计物理bank拍和声明传输路径。假设固定接口/连线成本需标明，不伪称真实物理locality。

首轮3函数×2部署×2labels=12配置，先pilot独立过后并行。纯label轨迹零差；真实tiling/bank变量单列。64×32→I128以S8 radix128 9×5=45 products与44次wide重组等显式lowering、对齐/累加/RNE/打包、元数据因式分解/保留/装载、物理拍/FIFO/容量/生命周期和完整consumer一起记账。实际小值fitI64不能变成无条件硬件能力。旧whole-row时隙不能套新group。

条件服务未校准RTL/时序，不称最优/芯片周期/PPA/E2E。VR factor敏感性含copy/reorder/guard/control，不单独归因宽乘；S32全码域N256读出需72signedbits的旧勘误继续有效。默认不扩模型/长度，只有真正分叉的失败触发最小补测。

## 来源、验证、交付

每阶段干净commit/每源SHA/source.zip、输入来源/官方revision/工具配置/随机种子、真实命令/Slurm及完整数组manifest。独立out，不覆盖旧phase；所有适用边界/校验实际执行，不只脚本或下载完成。运行check_project、新数学/资源边界、相关旧模块回归；完整大数据留授权服务器，仓库精选/索引/收据、报告/方案/决策/个人进度/交接和同一PR。

本人认证已核Liangruizhi/182389313、2663955430@qq.com；最新PR73 ready/open/unmerged，无新评论，成员55 in_progress/63 blocked。c96 1344idle，约418050MB available、12TB空盘，其他成员89448/node3不动。管理登记PR5 pending；无board.json/Projects能力，看板unverified/同步pending、管理员/审查人待指定。未审查合并不done。
