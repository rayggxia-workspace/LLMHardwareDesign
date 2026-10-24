# 新架构的同资源容量与传输下界

Issue70；本工具只验证精确字节、有限容量拒绝与COPY/最小读写端口日历。**算术执行周期未建模**，不能称完整compute调度、端到端加速或物理PPA；不能用FP32对S16的字节差当同精度划分收益。

```text
python -B transport.py --granite GRANITE_NUMERIC_DIR --falcon FALCON_CAPTURE_DIR --binding BINDING.json --out NEW
```

两输入可只提供其一，以便独立并行。binding须有`commit`、`transport_sha256`及`interval_checker_sha256`（`project/experiments/range_service/receive_service.py`）。严格核来源manifest及全部实际artifact SHA，不接受下载/脚本完成代替执行结果；Falcon还核NPZ实际header的完整state、branch、gatednorm形状和dtype，不据配置推测已采集。禁止覆盖输出。

固定库存沿用Issue68：V16KiB、R32KiB、M32KiB、S八bank各32KiB、EXT128MiB，各一共享1RW128bit端口；单128bit BUS，32B包头、16Bbeat、每packet最多1984B payload、每端TX/RX各2KiB FIFO。EXT端口II1为未测敏感性假设。每packet显式source read→BUS→dest write，完整依赖、地址、资源保留和FIFO credits保存在gzip witness；独立`receive_service.verify_intervals`对全图扫资源、依赖、容量及下界。没有引用生产scheduler作接收。每个bank的TX/RX endpoint独占保守限制仍保留。

Granite保持S32八专家返回、S64合并、Q31 multiplier/int16 shift、Q15权重，输出共同S32。48KiB整返回物化于V16KiB拒绝；12KiB S64累加器加6KiB单专家完整返回也拒绝。tile512/256明确给incoming、RQ参数、S64累加器和98B路由/scale描述符分槽；RQ参数先EXT→M→V逐tile加载，不免费驻留。专家权重/weight-scale/matrix计算未在COPY子图调度，实际unique payload下界和完全无复用字节从真实metrics一并展示；不能据省略这些项的COPY日历宣称完整流水线可行。source/staging/return、RQ参数、输出均有BUS和端口服务；local IO仅列必需读写，不提供免费算术吞吐。规范化元数据布局的打包/地址生成尚未定价。

Falcon完整head为D128×N256：FP32为128KiB、S16候选64KiB，都超R32KiB。全部32heads为4MiB/2MiB，整层old/new超八bank总256KiB。对一个实际完整head保留完整N归约，只沿D分tile，old/new各8KiB+aux8KiB分槽。COPY包括old EXT→S→R、new R→S→EXT及发布屏障后的完整new readback EXT→S→R；guard/发布/状态更新和输出收缩算术均未计时。S16仅storage候选，不代表所有heads整数质量通过。所有32heads/全层容量与逻辑payload单列，不将单head周期直接乘32宣称整层时间；全模型所有层的state、真实conv/KV持久容量另与EXT128MiB比较。

4096宽gatednorm必须完成整行first scan，再执行x second read/gate/gamma与输出；不会把分tile独立norm当正确算法。实际hidden宽从捕获读取（3B为2560），A/R两branch与输出和64B sequence/position/precision/epoch描述符均计价；全宽同时物化和256/512tile容量分别列。join只算读写，完整norm/branch compute未计时。

受控比较为相同precision和payload下tile256/512、roundrobin/all-one bank mapping、fifo/critical两个既定COPY顺序。若保守依赖及共享BUS令两layout相同，照实保留0收益；不添加免费bank或更强端口制造优势。超容量物化候选只给拒绝证书，无虚构周期。每项结果注明逻辑payload、wire含头/打包字节、端口/BUS资源下界。最终物理宏边界仍需包含真实compute、权重驻留、定点实现、时序与布局布线的后续同资源验证。
