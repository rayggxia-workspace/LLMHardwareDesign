# Issue68 独立接收口径

接收器不导入生产端算术或调度器。通过源文件 SHA、源 commit、原始结果清单与双轮逐文件 SHA 绑定输入；SHA 一致只证明相同字节，不替代数值或服务验证。

## R 范围与重定标

`receive_range.py` 独立使用 Python 整数实现完整 K 归约、逐阶段 signed RNE、原 S16/S32 **同物理范围**及状态码验证。S32 上界为 `32767 << 16`，不能改成 INT32_MAX 后声称相同范围对照。

预先固定全量算术审计条件：native evaluation 的 S16/S32 D31 完整 32 步，以及 legacy layer0/end8192 的 S16/S32 D31 完整 256 步，分别覆盖 `static_sat`、`static_guard`、`guard_rescale`。因此每 suite 6 个条件；其他条件只作双轮 SHA 接收，不能称全部数值独立重放。

接收器逐 token、逐 retry 检查未饱和 proposal、guard 的实际越界个数、只对坏 head 重编码、单位与 epoch 的因果演变、原子 state/output/scale/epoch 发布，以及拒绝后已发布状态完全不变。连续多次 RNE1 不能合并为一次 RNEn：`5→2→1→0`，而直接 RNE3 为 1。

重试与重编码的扫描、乘法、旧/新状态字节、scale/epoch 元数据写入独立计数。质量参考只用于已提交前缀的物理量误差，不能参与 guard 或未来校准。执行协议通过、运行期范围通过及质量未验分别记录；`static_guard` 正确拒绝属于执行通过、范围未完成。精选条件若遇到额外 I64/shift guard，接收应停止，须补该路径审计，不能默默跳过。

负例必须修改真实 NPZ 码或 epoch，并重写 NPZ、条件行及 manifest 全部 SHA；先通过字节清单，再由独立语义拒绝。原文件只读复用，不原地污染。

## V/R/S 有限服务

同组比较先固定精度、整数任务、完整归约和发布/恢复合同；仅改变资源归属与调度。不同 old/new shadow 或重算合同不得合并排名。独立接收器核 DAG 依赖、操作时长、1RW/bus/算术/FIFO 区间、常驻分配、信用、完整行 norm 与 R old/new shadow，并保留下界和有限候选搜索范围。

条件服务周期不等于 RTL、时序、PPA 或完整模型性能。未来物理边界只能使用同资源且数值合同相同的有效对照。
