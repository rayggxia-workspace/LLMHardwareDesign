# Granite3.1-3B-A800M最小实验

Issue70；此页记录生产协议，实际执行与结果须以manifest/作业回执为准。

官方config为40专家、top8、H1536、专家中间512、32层，含完整GQA。MoE新增的路由、稀疏权重访问、分发/收集、不同expert输出scale合并将检验V/M/S/D边界；不新增固定“专家宏”假设。

`granite.py capture --model MODEL_DIR --binding BINDING.json --out NEW --threads 8`
冻结B1/prefill64+teacher-forced cached decode8，独立校准/评价固定文本，chunk16对照。CPU FP32由原始BF16权重cast，仅layer0完整MoE转存。核验完整expert路径重放，失败不接受后续量化证据。源码binding要求`commit`与`granite_sha256`，可加`model_revision`；model所有权重和配置运行时逐文件SHA，安装HF实现另存并SHA。

官方参考：[模型config](https://huggingface.co/ibm-granite/granite-3.1-3b-a800m-instruct/raw/main/config.json)、[HF实现](https://github.com/huggingface/transformers/blob/main/src/transformers/models/granitemoe/modeling_granitemoe.py)。运行时实现以manifest SHA为准，不能把动态网页main当固定版本证据。布局只支持两种明确形式并以完整MoE输出重放确认。

参考完整/cached/chunk门：relative L2≤2e-4且max abs≤2e-3；仅参考一致性，非语言能力、全模型量化或目标硬件接受标准。性能测量未执行。
