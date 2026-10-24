# Issue72：路由、因果整数R与完整消费者的最小闭环

2026-10-24 UTC+08，负责人Liangruizhi，承接PR71@f4d2c46。新任务Issue72，根D:/Projects/LLMHardwareDesign-numeric-closure，task/72-numeric-closure；Granite/Falcon/审计三个独立worktree，分支task/72-granite-routing、task/72-falcon-chain、task/72-closure-audit。所有实际模型/张量/服务走本人CPU服务器新issue72-numeric-closure-20261024目录Slurm lrz-i72-*；本机只源码/小合成测试，无新下载/Phi解封/他人55/63任务。

## 先冻结的决策与实验

| 决策 | 最小实验 | 接受/拒绝与限定 |
| --- | --- | --- |
| G 高精度路由合同 | Granite原cal/eval各72token，native32/router64/model64三条件独立job，各full/cached64+8/chunk16；完整32层route/hidden证据 | 旧relativeL2≤2e-4且maxabs≤2e-3双门原样；old32失败保留，64是新精度参考，框架内部强制FP32 cast显式；固定ID非参考，exact tie与near tie区分 |
| G整数router与代价 | 真实各层输入与完整router weights，W8A8/W16A16等校准独立候选，真实top8/权重/翻转/margin | 先cal冻结单位/策略再eval；逐位独立math及边界；宽格式增加S8 digit/累加/重标代价，不能称主矩阵天然有INT16 |
| F/C源数据闭包 | 复用70真实cal16/eval72，补采完整层0 Mamba in/out weights与两norm gamma，原BF16提取FP32，无整模型重复推理 | 核原全部artifact/source/modelrevision，完整后继norm独立参考；新out不覆盖旧结果 |
| F状态范围 | Mamba2完整32头D128×N256，S16/S32，static_sat/static_guard/guard_rescale | online只当前integer输入/旧state，不读future/native；RNE逐次右移、私有trial/重试、epoch/version/原子commit，逐位/续接/负例必须过；clip发布仅诊断 |
| C完整整数R消费者 | 明确真实输入→完整inputnorm→inproj/MuP→conv/SiLU→dt/alpha→全部head递推→4096 gatednorm→outproj→residual+A+R→完整pre_ff norm | A为明确外部编码边界，未覆盖其计算及MLP；离线LUT/scale编译与runtime分开，runtime封闭段不许FP桥；所有width/unit、round/sat/溢出及非线性定义记录 |
| B同精度/资源边界 | 消费通过math与来源接收的相同code/unit/policy/epoch/提交轨迹，同算术总量/ROM/RAM/1RW/FIFO/BUS/backing | 数值合同先明确；真实compute/通信/clone/retry/元数据/地址物理拍全部计价，label-only无收益也保留；未RTL校准只是条件服务，非PPA/E2E |

不在看完评价误差后改单位、门限或挑token。应用质量没有已确认的整体误差预算，不把局部相对误差宣布模型质量通过；原生参考门、整数逐位一致、零非法发布/溢出及接续规则是本轮严格验收。不同精度/range policy不得混为placement收益。

Granite官方revision a02780686e08a03fe0d2679a293b5c74a90efa89；Falcon01087ec4c132d7f186908716b3530ea187f062a1；均只读Issue70已官方/服务器SHA复核的权重。70 native32 chunk16 FAIL、S16/S32各4sat、FP桥及COPY-only证据不重写。每phase干净commit/source/input/output SHA，独立新目录；至少独立接收，必要双轮。新整数核心独立Python int/Fraction/位算法与实际篡改后重写SHA负例，不能只函数名推定复现。

资源初核17:33 UTC+08：c96 1344 idle，node13 96核idle/~508190MB free，12TB盘空闲；仅其他成员89448/node3，未中断/重复。并行先3×8CPU Granite参考及2CPU Falcon补采，实际分配控制线程，Slurm RealMemory配置异常不以错误--mem触发拒绝。使用既有issue61 venv-modern，原生Torch2.10CPU/Transformers5.20.2/NumPy2.2.6，不改网络或安装新软件。

登记PR5 pending；无board.json/Projects工具，看板unverified、同步pending待管理员，审查人待指定。实际未运行项保持未执行，PR/Issue未审查合并不done。
