# F1024/N-long交付与Qwen3来源、数值准入审阅

Issue151 / PR152；输入`75d99a5ba01adba1e978db3933a41e1d43c49c30`，原生选定源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。只操作本轮drafts/review。下述Python数学构建/复现与源码阅读已执行，RTL编译/仿真由根负责，本审阅没有本地RTL运行、服务器访问或ref-project操作。原八模型准入表不修改、不放宽。

## 1. 新N-long控制器与实际接口改动

新增`block_w4_n_long_ctrl.sv`，独立module，原N controller/leaf不改。公开input/output声明与旧ABI逐字节相同：mode0 Softmax、1 RMS、2 L2，req_count仍16bit，地址仍10bit、payload128bit、最后真实写ACK后service rsp、错误后poison直到协调reset。

| 项目 | 新实现 | 核对理由 |
|---|---|---|
| count准入 | 1..1024 | 0/1025不得进入native BEGIN |
| request_words | 17bit扩展`(count+7)>>3` | 高count不经16bit加法回绕 |
| words_hold/index | 均8bit，最大128字、有效index0..127 | 513项经过index64，1023/1024经过index127，不再受6bit截断 |
| remaining | 16bit减`({8'd0,index}<<3)` | 保留完整1024元素偏移 |
| last_word | 两侧9bit，`index+9'd1==words` | 末128字比较不截成0 |
| mem offset | `{2'd0,index}`为10bit | 与S实际字地址一致 |
| range/disjoint | 保留17bit扩展加法和两两不重叠 | base+words≤1024；src/gamma/dst或src/exp/dst相离 |

phase顺序不变：完整group统计→共同factor→逐字原值/gamma或exact EXP回放。没有把1024拆成128个独立RMS。local admission失败不改N、不poison；开始后native/S服务错误保留已发生写，poison直到ctrl/N/helper协调reset，不宣称回滚。

## 2. 独立TB、数学预期及可复现范围

`nlong_integer_reference.py`独立重建RNE、floor-root、RMS/L2和U16 EXP。周期8的输入/gamma用于压缩字面期望；最后有效元素单独变化，会影响整组统计/max，**实际执行组仍为1024/1023/513/257，不是缩小组**。生成的TB使用数学常量输出，不从DUT计算期望。

15组数学向量覆盖三mode的1024、1023/尾7、513/尾1、257回归；RMS1024零输入与signed非对称gamma；count1极值gamma饱和；Softmax1024等值的每项概率码16、exact EXP0x8000；1023最后新max的整组one-hot；cutoff/插值。手工数学事实另核对负数RNE ties、floor-root上下界和上述概率/饱和值。1024 RMS应258 native cmd/rsp、512普通S=384R+128W；Softmax1024应387 native、640普通S=384R+256W。

TB连接真实native N、S16KiB及S helper，保留强monitor：native opcode/count/tail/raw/EXP/gamma序列、每次普通S地址/读写/值、写ACK echo与最后dst ACK完成门、valid停顿保持。38个CASE还包含命令/响应/helper/最后写ACK停顿；count0/1025、mode3、epsilon0、overlap、越界及full1024地址防wrap拒绝；poison/协调reset恢复；第二个写ACK错误后两字prefix保留；pending EXP ACK/held native response时reset；完整1024 source/dst恰止1023以及count1地址1023。

controller没有独立abort pin；父abort对应协调reset。TB不把硬reset后的取消当作普通service完成，也不按正常总数强制错误/取消前缀守恒。S服务错误是对mem_rsp_error的TB注入，用于验证controller的poison/partial策略；原生S没有error pin，既有helper正常rsp_error恒0，不因此新增实际RAM故障检测。CASE清单为唯一集合；native/S阶段顺序由monitor单独检查，清单枚举顺序不是行为合同。

```powershell
python -B -X utf8 work/Melodydt/151/build_nlong_tb.py --root . --output-dir <新的独立输出目录>
```

该命令只生成数学常量/TB/contract，不运行RTL。正式辅助文件为`nlong_integer_reference.py`、`build_nlong_tb.py`、`nlong-math-vectors.json`、`nlong-tb-contract.json`；TB安装到project/tb/block_connection_w4，controller安装到project/rtl/block_connection_w4。contract列出compile_sources/include_dirs/reference_dependencies/input_paths，最终成功标记为独立一行`PASS_NLONG cases=38`，统计另走`NL_STATS`。已在Python3.7.0新目录重生三文件并逐字节相等；EXP1025数学节点与选定source一致，公开ABI字节核对PASS。以上不是编译/功能PASS。

## 3. Qwen3真实参数并非“从来没有”，但当前质量链未闭合

锁定config确定Qwen3-0.6B：H1024、I3072、28层、Q16/KV8/D128、普通RMS、SiLU、epsilon1e-6；原config dtype BF16，图导出使用FP32/B1/Sq2/use_cache=False。[固定配置](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/qwen3/config.json)

既有render01 manifest记录layer0加载了11个checkpoint张量，missing/unexpected均空；对按名称排序、转FP32后连接的层state给出SHA `cad26f832d63bfaa2b6f23f618b189540aae2f54c915375a99ba0bc0b6dfe7b7`。这包括MLP与Norm等层参数的历史来源证据，不能写成“Qwen3只用随机权重”。记录的checkpoint文件约1.503GB，但仅记路径/size，没有该文件的完整内容SHA；combined tensor SHA也不是本F1024的量化S8镜像SHA。历史路径位于其他成员目录，本轮只读已有JSON/源码中的字符串，未检查该目录、当前文件存在性或访问权限。[固定导出实现](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/sources/native_export.py#L39)

导出源码使用`torch.randn(1,2,H)*0.1`的随机hidden和外给cos/sin/mask，再用seeds17/31/73检查FP32 native/ONNX一致性。完整层内部确实计算了F的输入，但该包没有为本次selected整数profile交付代表性语言cal/eval的F切口激活、per-stage scale、完整量化权重/gamma、误差门及质量证书。不能把三个随机seed的导出一致性当成trained-checkpoint量化校准或生成质量。历史CPU整网一致性报告也不自动移交这些量化证据。[固定导出输入与验证](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/sources/native_export.py#L78)

选定本轮隔离checkout中未发现safetensors/ONNX/PT/NPZ/NPY张量实体；这里的结论是“本轮没有可读且获授权的实际tensor交付”，不是断言整个仓库历史或服务器不存在。原始大文件保持既有获授权存储及索引规则。

## 4. F1024 selected合同与真实Qwen3尚差什么

F1024对齐真实H1024/I3072，但当前provider由独立seed/配方生成9MiB S8数据，X/gamma也是合成整数输入。selected合同固定X/gamma/mid/output S16 Fin10、权重S8 Fin7、epsilon_code1；每个完整gate/up/down输出组全部K归约完才RNE7，SiLU门乘RNE10，最后原X残差。它的正确描述是**合成数据、真实样本尺寸的完整整数F行**。

Fin10下code1代表2^-20=9.5367431640625e-7，与source1e-6相差约-4.6326%（这是epsilon参数相对差，不是输出RMSE）。选择更细Fin会改变输入可表示范围；不得只增Fin或凭initializer_range0.02推断训练权重/激活范围。S8 Fin7权重、gamma量化与所有stage clip也仍需实际张量评价。

| 门 | 本轮实际范围 | 当前结论 |
|---|---|---|
| H/I/普通RMS/SiLU/原残差结构 | 源维度与selected程序相符 | 结构静态匹配，不等于模型准入 |
| 全H统计、K32分块但最后统一量化、真实layout/ACK/有序供参 | 新controller/top/TB候选；实际RTL结果由根回执确认 | 源码/数学合同已明确；测试资格单列 |
| 训练层参数历史来源 | manifest loaded11及combined FP32 tensor SHA | 已有历史证据；当前可访问镜像/权限仍UNKNOWN |
| 本F1024的实际S8三矩阵/S16 gamma | 未交付trained参数量化镜像 | UNKNOWN |
| 代表性F输入/held-out数据 | 本次只有synthetic recipe；导出seed非质量集 | UNKNOWN |
| epsilon/Fin/scale/clip/误差预算 | 仅selected整数函数冻结 | 真实Qwen3接受仍UNKNOWN |
| 完整A、28层推理/质量、L5/MEM/物理 | 不在本切口 | 不准入 |

恢复真实Qwen3准入的第一步是由资料拥有者向获授权任务存储交付：确切checkpoint/revision与内容指纹；layer0的post-attention RMS gamma、Wgate[3072,1024]、Wup[3072,1024]、Wdown[1024,3072] FP32张量及逐tensor SHA；实际F输入Y（attention残差之后）和FP32 F(Y)；cal/eval划分及误差门。无需访问他人目录来完成本轮可独立进行的整数RTL工作。

之后在同一FP32参考上生成量化镜像、Fin/epsilon转换、完整归约和每级clip统计，冻结每stage与最终误差标准，检查任意重定标是否需要新增硬件/供参字段。再以相同镜像/输入贯穿独立整数参考→provider→真实RTL，分别签收“整数函数一致”和“模型误差可接受”。不能用RTL与synthetic golden逐位一致补填后一项。

## 5. 另一作者F1024顶层关键源码审阅

读取top `699836a9673062545b46a346ae77e805a5693ceb9ddc17bd5e4c7dd6976e6634`：N-long连接1024、src0/gamma128/dst256；compact A按gate/up `256+4*chunk+tile`、down `384+4*chunk+tile`读取，写896+4*tile；12个容器padding实际初始化。首chunk c885、后续c881保持同M raw merged，最后才读op5；gate/up8结果保存，384组mid全落S384..767后才down；残差src是原X group0..127，输出768..895。未发现这部分单位/地址/完整归约边界阻断。

独立复算正常S888076=739084W+148992R；M40448=36864 EXEC+896×(clear+scale+2read)；loader36864组、294912次512bit读。S固定预约0..931=14912B，T128字2048B；源provider与错误/reset的完整资格仍以实际测试为准，不将源码阅读当执行。八模型原admission保持原状，后续为F1024新增受限profile也不能自动升级A16/F16/AF16的真实样本或整模型质量结论。
