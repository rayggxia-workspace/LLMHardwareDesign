# 架构先行的模型选择（Issue37）

这是公开元数据/配置、架构覆盖和容量公式研究，**不加载神经网络、不下载权重、不启动GPU**。
用户要求先筛选再设计实验，因此本轮不执行新模型或缩小模型数值推理。

- `catalog.json`：17个已提变体，12个官方config原字节/SHA，5个门控缺口。
- `plan.json`：拟定主测/保留验证及阶段门槛；`new_numerical_runs_enabled=false`。
- `analyze.py`：穷举小目录的显式覆盖筛查与逻辑容量记账，不是全局最优Block或实际VRAM预测。
- `test_catalog.py`：协议与独立容量已知值检查，不能当成模型验证通过。

从项目根目录执行，无第三方依赖：

```powershell
D:/APP/Python/python.exe -B scripts/check_project.py
D:/APP/Python/python.exe -B project/experiments/model_selection/test_catalog.py
D:/APP/Python/python.exe -B project/experiments/model_selection/analyze.py --output D:/Projects/Codex/gemma-phi-20261023/screen-replay.json
```

详细架构、取舍和可证伪实验见`docs/MODEL_ARCHITECTURE_REVIEW.md`。源版本/输入与结果SHA在
`work/Liangruizhi/37/`；`configs/`仅有小型公开配置，Gemma/Meta401未绕过或用默认配置补齐。
引用PR26的功能目录，不修改其他成员文件；本轮是资源受限首轮选型方案，未撤销其MoE/MLA覆盖缺口。
