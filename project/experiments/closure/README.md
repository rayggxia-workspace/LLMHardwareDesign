# Issue72：路由精度与整数消费者闭环

范围与结论见[报告](../../../docs/experiments/issue-72-numeric-closure.md)；[结果索引](results/issue-72/index.json)区分数学接收、原生参考、局部误差、字节接收与条件服务。本批全部真实模型/张量/服务只在本人CPU服务器Slurm执行；本机仅小合成测试和元数据/字节校验。没有GPU或目标硬件速度/PPA结果。

## 合同与实现

- PROTOCOL.md：执行前G/F/C/B决策、原门、cal/eval及来源。
- GRANITE_REFERENCE.md / GRANITE_INTEGER.md：原失败、高精度eager参考、W8/W16实际top8和gate、宽lowering及证书。
- FALCON_CLOSURE.md / FALCON_OUTPROJ.md：完整32head整数R分支、持续conv、guard/重定标/原子发布；唯一输出投影粒度分叉。
- SERVICE_CONTRACT.md / SERVICE_IMPL.md：完整compute/宽算术/SFU/ROM、真实库存和保守串行调度；独立loop/端口/事务接收。
- RECEIVE_CONTRACT.md / AUDIT_FINDINGS.md：独立实现与真实SHA重写负例，以及不能宣称的结论。

主矩阵W8A8/INT32；数据、状态、缩放和非线性分别定义。编译常量/LUT的浮点与runtime整数分开。原生A分支/MLP切口外；Granite gate尚未完整传播到全部专家。不能把局部整数数学PASS等同完整模型质量或全整数硬件。

## 检查与接收命令

进程TEMP/TMP指定D:/Projects/Codex下当前任务目录，勿改变系统变量。使用已有NumPy环境：

~~~text
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/closure -p "test_*.py"
python -B -m unittest discover -s project/experiments/architecture_extensions -p "test_*.py"
python -B project/experiments/closure/verify_delivery.py --index project/experiments/closure/results/issue-72/delivery-index.json --archive project/experiments/closure/results/issue-72/selected.zip --out <新D盘receipt.json>
~~~

实际结果89项新检查、80项旧模块、管理结构通过。最后一条只验2.48MB精选metadata的SHA/全部286成员，不能在缺少完整数组时重算数学。完整9.90GB包按index.server_root取得，使用同工具指定full-results.zip核1096成员；原Issue70输入/权重仍是明确外部依赖。

## 原始执行与复跑

逐phase原Git commit/每文件SHA和原始Slurm命令在[work72](../../../work/Liangruizhi/72/README.md)。完整服务器包含phase1–15冻结source.zip/binding；必须先验包和source_gitreception，再用对应phase源码复跑，不能直接拿最新HEAD覆盖旧源绑定。每次指定全新out；不得覆盖原日志、负例或未合并成员成果。模型权重只读复用，不重复下载。

独立接收CLI示意（精确路径/参数用work72/slurm的实际command）：

~~~text
python receive_reference.py --result REFERENCE --original ISSUE70_CAPTURE --producer-source FROZEN_REFERENCE.py --binding RECEIVER_BINDING.json --out NEW
python receive_numeric.py --result ROUTER --reference REFERENCE --producer-source FROZEN_ROUTER.py --binding RECEIVER_BINDING.json --out NEW
python receive_falcon.py --result INTEGER --compiled COMPILED --capture CAPTURE --chain-source FROZEN_CHAIN.py --int-source FROZEN_INT.py --binding RECEIVER_BINDING.json --out NEW
python receive_continuity.py --result RESUME --baseline INTEGER --baseline-receipt INTEGER_PASS.json --compiled COMPILED --producer-source FROZEN_RESUME.py --int-source FROZEN_INT.py --binding RECEIVER_BINDING.json --out NEW
python receive_outproj.py --result GROUPED --baseline INTEGER --baseline-receipt INTEGER_PASS.json --compiled COMPILED --producer-source FROZEN_OUTPROJ.py --binding RECEIVER_BINDING.json --out NEW
python receive_service.py --result SERVICE --numeric INTEGER --compiled COMPILED --math-receipt INTEGER_PASS.json --producer-source FROZEN_SERVICE.py --binding RECEIVER_BINDING.json --out NEW
~~~

接收默认执行实际篡改并重写SHA的语义负例；skip-negatives只允许PARTIAL，不应冒充完整接收。stage文件和model_revision/格式/layout/单位/状态初末及事务均由producer manifest/SHA绑定。完整日志/失败和工作分工在交接中，不自并PR或提前done。
