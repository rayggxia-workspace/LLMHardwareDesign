# 完整消费者 scale 与连续整数状态（Issue66）

[实际报告](../../../docs/experiments/issue-66-scale-state.md) / [Block方案](../../../docs/BLOCK_PARTITION_V2.md) / [索引](results/issue-66/index.json)。负责人Liangruizhi，PR67基于PR65。本模块是可审查数值候选与成本账本；不代表目标硬件已支持INT16/宽乘/除法/开方或整图质量/周期/PPA通过。

## 执行分层

- export_legacy_state.py按原SHA无损导出PR36真实窗口，不能拼窗；capture_qwen35.py只读复用原Qwen3.5权重，补H2560消费者和真实32步R/conv边界，校准与评价独立。
- consumer.py比较同一A8K128/W8K128下四种出口，完整残差/FP32 RMSNorm/新A8/next前16输出；[合同](consumer.md)。consumer_receive.py不导入producer，核8profile、独立下一投影整数数学和真实重写SHA负例。
- norm.py在已保存consumer sums后添加真正整数RMS候选，sqrt/div/RNE与fresh A8直接整数；[合同/有限buffer成本](NORM.md)。receive_norm.py独立完整H2560码、next16、成本和负例。它不覆盖R内部L2norm/GatedRMSNorm；norm01/02旧账本保留，norm03/04补源重读和A8/Ae写读，NPZ码完全相同。
- conv.py做H8/H16-W8四槽INT32，SiLU仍桥。receive_conv.py独立所有四tap数学/history。state.py做非零初态、固定单位的S16/S32×D15/D31连续R，含8/16 chunk、guard/commit；[详细合同](STATE.md)。receive_state.py接收新8条件；receive_state_extra.py独立coupled两条件与预先固定三个真实256步见证，明确其余长条件只核二轮SHA。
- collect.py只验证绑定/双轮并归档；selected_review.py只读精选编码数据，独立重放两个完整32步R和两个decode消费者，不能替代全量capture/down编译或整数norm验收。

## 真实运行与绑定

所有完整命令、source binding及提交记录在work/Liangruizhi/66，阶段源码commit不能用最后文档HEAD替代。服务器Python3.12.7/NumPy2.2.6/Torch2.10.0+cpu/Transformers5.20.2；lrz-i66-* Slurm，输入只读，输出新目录，OMP/MKL/OpenBLAS=1，未增加模型下载。job90059–90082实际完成；这不是推理性能测量。

在已核输入和相同环境中，命令形状如下（binding必须填写实际源码SHA/commit；下列占位不是已运行路径）：

~~~text
python -B scripts/check_project.py
python -B scripts/check_research.py
python -B -m unittest discover -s project/experiments/scale_state -p "test_*.py" -v
python -B project/experiments/scale_state/consumer.py --input <capture01> --binding <consumer-binding.json> --out <new-consumer>
python -B project/experiments/scale_state/conv.py --capture <capture01> --binding <conv-binding.json> --out <new-conv>
python -B project/experiments/scale_state/state.py --root <capture01> --binding <state-binding.json> --out <new-state>
python -B project/experiments/scale_state/state.py --root <legacy01> --steps 256 --binding <state-binding.json> --out <new-long-state>
python -B project/experiments/scale_state/norm.py --capture <capture01> --consumer <consumer01> --binding <norm-binding.json> --out <new-norm>
python -B project/experiments/scale_state/receive_norm.py --capture <capture01> --consumer <consumer01> --integer <norm03> --repeat <norm04> --binding <receiver-binding.json> --out <new-receipt.json>
~~~

每个producer/receiver还有其专用CLI，先看--help；不要把consumer参数套给conv。实际完整启动脚本已逐份保存，不重复跑模型证明管理结构。校准/evaluation、FP桥、浮点假量化与整数软件/硬件必须分开；日志/清单PASS表示内核执行/接收，不保证零饱和或应用可接受。

## 另一台电脑最小接收

只需Git源码与NumPy，无需模型权重、Torch或网络。使用索引中的实际SHA，输出必须新建：

~~~text
python -B work/Liangruizhi/66/verify_delivery.py --archive project/experiments/scale_state/results/issue-66/selected-evidence01.zip --sha256 36791d8b553490c914fc720df31abc179bb1442c2ca0c5a93645c139ab6bca0b --repo . --extract <new-extracted> --out <new-intake.json>
python -B project/experiments/scale_state/selected_review.py --root <new-extracted> --helpers . --out <new-selected-review.json>
~~~

外层/member SHA、安全解包、15阶段源码与原Git blob核对，加数值重放分别验收。精选19,581,351B（133ZIP成员），完整5,207,960,397B留授权服务器；后者包含原始采集/两轮全NPZ/源快照/日志/接收，完整权重未入包。真正重跑完整原始数据时按索引安全取回完整包，不从小精选推断全模型已验证。
