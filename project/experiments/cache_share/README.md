# Issue84 A缓存与乘法器共享

对应[Issue84](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/84)，[冻结协议](PROTOCOL.md)。四变体v=2*CACHE+SHARE；主批48条及端口压力36条完整真实M消费者命令，仅本人CPU服务器Slurm。源自Issue82 raw-unit输入，保留旧精度/结果，不重新加载模型。

RTL在project/rtl/cache_share：mfront84执行K512/8expert/H1536矩阵和有单位RQ/merge/residual；norm84执行完整行精确RMSNorm；mul84提供一个共享或两个独立S32乘法器、每client一个S64响应槽；sfu84是固定PROFILE1的整数除法/开方服务，只允许op1/2，op0不在合同；chain84通过memory_link五beat读与store82单16KiB1RW。未实现通用V18函数/ROM、整个M16x16阵列、router/SiLU和多context。

A缓存使用行768..1023，X/Y0..383、gamma384..767；额外128bit A寄存器和乘法器响应/控制/计数器计logic/FF。CACHE模式外部先256个A128，再1536x8的16B头+32个W128，每W128执行两次8laneMAC。无预取/第二端口。缓存可作为制造时不同版本；当前CACHE是编译参数，运行时旁路尚未实现。SHARE同样不是免费产品互联配置。

实际命令、Slurm配置/源码binding及所有失败见work/Liangruizhi/84/execution.json。复现须本人服务器新独立out，禁止覆盖旧目录。先python -B scripts/check_project.py；服务器固定源码zip解压后：

    python -B project/experiments/cache_share/inputs.py --old /public/home/yuzelu/RuizhiLiang/issue82-norm-circuit-20261025/M-input02 --out <new-input>
    python -B project/experiments/cache_share/run.py build --binding <binding.json> --out <new-build> --profile <0..3> --prefix '<JSON singularity argv>'
    python -B project/experiments/cache_share/run.py sim --binding <binding.json> --out <new-run> --profile <same> --prefix '<same>' --input <input> --build <build> --stall <0..4>
    python -B project/experiments/cache_share/verify.py --input <input> --run <run> --out <new-receipt.json>
    python -B project/experiments/cache_share/run.py map --binding <binding.json> --out <new-map> --profile <same> --prefix '<same>' --library <same-frozen-liberty>
    python -B project/experiments/cache_share/arbitration.py --binding <binding.json> --out <new-arb> --share <0..1> --prefix '<same>'
    python -B project/experiments/cache_share/analyze.py --root <Issue84 exact experiment tree> --library <same> --out <new-analysis>

--stall0静默、1三资源确定性背压、2/3/4仅SRAM固定额外4/8/12等待。分析器使用已记录目录名；跨环境修改目录需另冻结绑定，不能冒充原始SHA。先核输入manifest，接收器不导入RTL或pack生成逻辑；独立从物理payload算全K，再与旧原始codes比较。

全量数据在授权服务器，精选包用于字节/来源接收，不能在PC重做实际数组实验。字节工具project/experiments/closure/verify_delivery.py --index <index> --archive <必须名selected.zip> --out <new-D-path>；原Git源核验work/Liangruizhi/84/verify_sources.py参数见交接，不能拿当前工作副本替换历史源。实际完整数值接收已服务器执行。

logic-only面积不含整个共同store82 wrapper；真实单端口存储容量与读写另报。Nangate45研究库不是目标工艺，RTL cycles不能当ns/功率/整模型速度，真实pack/DMA与route/STA/PVT/宏未验。
