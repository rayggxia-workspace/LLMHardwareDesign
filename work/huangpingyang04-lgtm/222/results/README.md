# 结果读取与复现

net-comparison-compact.tsv 包含全部 2,491 根线。变化率以原上层 C 为分母，旧模型误差以耦合后 C 为分母。单位 fF，表保留八位有效数字，服务器 JSON 保留全精度。互容按目的网络类别统计，不能简单等同于金属所在层。

主上层包含旧模型 M10 落点，不能再加宏诊断的 M10。macro-wire-charge-reuse-selected.json 每项合计两端宏的相连 M1–M10 金属，不含器件 C。保留旧下层贡献、采用新上层贡献后比较金属总 C，是线网近似诊断，不是宏 Liberty 或时序验证。

使用 Python 3.13 实际封装通过。输入与原始服务器文件的精确映射见 final-input-index.json。从仓库根目录执行，输出必须是新目录：

```text
python -B project/experiments/m11_m12_rcx/native_package.py --comparison ../coupling222-final-inputs/full-comparison --primary-receipt ../coupling222-final-inputs/primary-solve.json --binding ../coupling222-final-inputs/case-binding.json --drivers work/huangpingyang04-lgtm/222/original-driver-limits.tsv --macro ../coupling222-final-inputs/macro-coarse ../coupling222-final-inputs/macro-fine03125 ../coupling222-final-inputs/macro-fine015625 --checks ../coupling222-final-inputs/checks/reciprocity.json ../coupling222-final-inputs/checks/offset-assessment.json ../coupling222-final-inputs/checks/depth-assessment.json ../coupling222-final-inputs/checks/extreme-assessment.json --fine-runs ../coupling222-final-inputs/primary-fine03125 ../coupling222-final-inputs/primary-fine015625 --output <新的输出目录>
```

封装核对完整覆盖、求解器指纹、来源一致、端点身份、电容加和及数值检查，不重算电场。direct_macro_reuse_qualified=false，表示没有宏时序复用验收。抽样检查不代表所有网络逐一收敛。
