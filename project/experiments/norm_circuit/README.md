# Issue82：精确归一化与真实 M 完整消费者

[协议](PROTOCOL.md) · [报告](../../../docs/experiments/issue-82-norm-circuit.md) · [结果索引](results/issue-82/index.json) · [Issue82](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/82) / [PR83](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/83)。工具用于已有整数合同的电路成本校准，不下载或运行新模型。

## 数值与资源

norm82采用I32Q12输入、S32Q20 gamma、U128平方和/floor H/epsilonQ24、isqrt(var<<40)、signedRNE→I32Q12。PROFILE0是单U8乘法器分片，但仍有实际128bit宽加减、比较及迭代SFU，不能称全部只用8bit硬件；PROFILE1增加专用S32乘法，PROFILE2每拍展开4个SFU步骤。相同单16KiB/128bit1RW，x/output原位、gamma在偏移6144B，完整H1536占12288B，非任意hidden规模都可容纳。

Mfront82从真实midA8/W8切入，实际8条S8 MAC/INT32完整K512，逐坐标交错8专家→Q31重标→Q15全merge→输出比例/真实residual→完整H1536 norm。输入为raw权重exp16/A单位delta16，RTL求31-exp-delta，guard及大移位clamp遵守S64 RNE精确零值规则；不从host接收acc/down/joined中间结果。epsilon/输出比例在命令接受时锁存，驱动随后改变输入仍须得到相同结果。router/SiLU/输入编码在此cut之外，不是全模型全整数验证。

实际取数为128bit单在途memory_link，完整读事务5beats；每beat同时含8个A和8个W，A重复输送及metadata padding入账，没有免费A缓存。共享store先由M写入完整行，再由norm读取/覆盖；不把逻辑同top当已冻结合宏或已验布线。

## 代码和实际复现

- project/rtl/norm_service：arith82、store82、norm82、block82，以及mfront82/chain82；真实控制/寄存/接口。
- inputs.py / boundaries.py：源SHA核验的旧真实行与正负RNE半值、非法H、零分母边界。
- m_inputs.py / m_units.py：只读旧74，打包实际选中专家W8、midA8和元数据；最终raw-unit格式另存新out。原数据和每层revision留SHA。
- run.py / chain_run.py / sim.cpp / chain_sim.cpp：服务器Verilator/实际端口/完整链，host为被动存储与观察器。
- verify.py / m_verify.py / analyze.py：独立bigint/完整K乘积/舍入/平方根与真实mapped实例/原Liberty面积求和接收，不信只写入报告的指标。

源码phase/精确argv/资源申请/输出和Slurm ID见work/Liangruizhi/82/execution.json。真实编译/矩阵/RTL/综合/接收只本人CPU服务器新issue82目录；PC只源码、小合成、JSON及字节。既有Verilator5.042/Yosys0.63和只读SIF、固定Nangate45研究库，未安装软件。

```powershell
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/norm_circuit -p "test_*.py"
python -B -m unittest discover -s project/experiments/block_circuit -p "test_*.py"
```

进程TEMP/TMP指向D盘独立任务目录，PYTHONDONTWRITEBYTECODE=1。接收精选用已有closure/verify_delivery.py，接收历史Git来源用work/Liangruizhi/82/verify_sources.py（expected-phases以最终索引为准），输出必须为新文件；这些只核字节，不重做数学。

服务器CLI：run.py build/sim/map；chain_run.py build/sim/map；--binding SRC/binding.json --profile 0/1/2 --out NEW --prefix JSON_PREFIX；sim另加--input DATA --build BUILT --stall 0/1，map加--library LIB。verify.py / m_verify.py使用--input DATA --run ACTUAL --out NEW_RECEIPT；analyze.py使用--root TASK --library LIB --out NEW。所有实际可执行命令在execution.json；不能覆盖旧out，不能省略来源SHA或把不同库存称同面积。

## 解释限制

研究库logic-only映射排除整个共同store82 wrapper；其131072memory位和generic寄存另记，宏面积/时序填未验。4步SFU降低周期但可能拉长组合路径，未测STA前不能称实际时延或功耗获益。当前单context/协调复位，未验独立fabric的旧响应、CDC、全系统18函数V/ROM共享仲裁或完整应用质量。所有先前失败/中间批次留档，正式批以报告所指来源和receipt为准。
