# 师兄GPU采集与本机接收合同 v0.1（Issue33）

供16GB显卡上的Qwen3.5-4B等实验复用；Qwen3-4B不必跑。本文件是数据接口与需求，
不是已经安排或完成的GPU实验。较长上下文、完整权重与量化质量由师兄负责；本机不重复。
用户通知结果完成后才核验/整合，当前用合成与已有小模型数据验证接收器。

> 2026-10-23 Issue61更新：用户已授权本会话在既有CPU服务器完成原委托批次，并已接收PR36、补齐Gemma/Qwen完整GQA及Phi封存；上文分工/等待通知是历史。接口合同继续复用，CPU结果与原GPU数据分列，不代表GPU性能/显存/4bit或全整数硬件。实际条件/范围/失败见[Issue61报告](experiments/issue-61-server-models.md)。

## 必须记录

1. 模型准确ID/revision、权重/分词器/配置的逐文件SHA；代码commit、dirty状态与源文件SHA，
   运行脚本/完整参数、框架/量化工具/CUDA/驱动/GPU型号与实际可用显存。
2. 数据/校准/评价版本、文本/样本范围或公开位置与SHA、token IDs与mask/position、batch、
   prefill/decode、prefix/追加token数。校准与评价分离；teacher-forced与生成分别标记。
3. 采集边界：层/头/专家、投影输入输出及权重通道、RQ前INT32部分和与后输出、Q/K/V，
   hybrid层conv与递推状态、q/k规范化、beta/decay、输出gate/RMS、KV追加；
   原生框架具体缓存算法明确标记，不由模型名推定compressed/expanded。
4. 分别记录权重/激活/acc/KV/state/scale格式、粒度/轴/布局、静态或动态scale、
   M/r或fraction_bits/dyadic exponent、零点、舍入/饱和、校准统计、裁剪/overflow计数。
   全部浮点回退节点和执行backend列出；fake-quant不标成真实INT8 kernel测量。
5. 数值：原浮点参考、量化结果、逐层误差/饱和随长度、任务质量与评价方法；
   吞吐/时延需说明warmup、同步、计时窗口、采集hook是否开启，和真实INT8/混合路径。

16GB显存装不下某配置时记录OOM、量化/卸载/裁剪策略及实际范围，不为了填表改变模型或
省掉较宽状态。无需一次保存全模型所有大张量：提供分层统计和少量可复查代表切片，
但切片必须记录原shape、offset/axis/长度与选择规则，不能伪称完整层/模型。

## 包结构与严格格式

根目录`capture.json`使用`llm-precision-capture/1`；tensor payload为little-endian、C连续
raw `.bin`，每文件bytes/SHA固定，dtype枚举f32/f16/i8/u8/i16/u16/i32/u32/i64/u64。
scale/指数/M/r也是manifest内独立tensor或明确常量，不得只有无法追溯的浮点scale字段。
每tensor包含shape、axis_names、角色/阶段/层和quantization；标明reference_float、
integer_reference、integer_kernel或fake_quant，说明浮点回退。未量化参考不能冒用integer_kernel。

分组量化的`group_axes/group_shape`与原tensor维度严格对应，metadata引用指向真实payload。
按token-block分组还需`block_shape`，组数按对应维度除block长度向上取整。
INT32 accumulator通过`scaled_accumulator`的`scale_factor_tensors/scale_factor_axes`
声明输入scale与权重scale的外积映射，不能省掉实际累加scale。
可选`selection`记录原shape、连续切片offset与规则；teacher-forced/generated用`token_mode`。
建议payload和metadata分开文件，打包/对齐由布局描述明示；接收器先核路径、大小、SHA、
shape/dtype/axis/格式，再进入计算，拒绝pickle/object、路径逃逸和缺少缩放定义。
数据包源码、样例与验证CLI将放`project/experiments/integer_precision/`。
机器可读入口为[capture.schema.json](../project/experiments/integer_precision/capture.schema.json)。
整数Python参考用integer_reference；真实设备整数kernel才用integer_kernel，不能混写。
当前接收器核验payload及manifest内部一致性，不能凭model SHA证明未提供的全部权重/源码正确；
整合时仍须与获授权源包和预期commit/revision核对。

大文件存项目认可且获授权共享存储，Git只存manifest、脚本、统计、SHA与位置。
本机接收器不会自行去其他机器运行或下载新大模型；没有真实包时只报告接口测试结果。

## 师兄结果到达后的整合顺序

用户通知→核对指定GitHub身份及最新Issue/PR/成员交接→下载获授权包与核SHA→
严格格式和数值路径检查→复现少量整数核→同精度/库存下重建容量/端口/连接图→
结合实际GPU质量与后续物理证据比较。缺少字段时保持pending，不能用猜测补齐测量。
