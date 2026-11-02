/**
 * R：八lane递推/状态更新模型，支持GDN、SSM及固定四抽头因果深度卷积。
 * Open/装载 -> Execute写shadow及输出 -> ReadOutput -> Commit或Revoke。
 * active银行保存正式状态；shadow保存候选状态，成功执行也不会立即替换active。
 * 状态矩阵最多256行×8lane，每元素S32；两银行共16KiB。卷积历史单独保留正式/候选副本。
 * 本层按完整8lane行装载，折叠原RTL的半行总线事务、乘法器共享和逐拍FSM。
 */
#pragma once
#include "common.hpp"
namespace blocks {
// Coalesced rows replace packed half-row bus writes. Values retain raw scales.
struct RCommand : Printable {
    enum class Op {
        Open, // 建立length和owner/epoch/position，必须先处理已有候选。
        StateRow, // 将8个S32写到正式状态的index行，标记该行已装载。
        DecayRow, // 将8个UQ1.31因子写到shadow的index行，供下一次SSM使用。
        Key, // coefficients[0]写第index个K或B系数，Q1.14。
        Query, // coefficients[0]写第index个Q或C系数，Q1.14。
        X, // 装本次当前输入/目标值，八个S32。
        Inject, // 装已由外部计算的SSM注入量，例如dt*X。
        Parameters, // 设置全局GDN decay/beta，每项UQ1.31且<=1。
        Skip, // 装八路S32 Q16.16的SSM skip系数。
        History, // 装index=0..2的八路过去输入，最近历史在index0。
        Taps, // 装index=0..3的八路Q1.14卷积权重，0对应当前输入。
        Execute, // 核验标签和输入齐备性，再生成候选状态/历史及输出。
        Commit, // 核验旧标签，交换银行/提交历史，epoch+1并更新position。
        Revoke, // 清除候选和输出有效性，正式状态不变，SSM因子需重装。
        ReadState, // 读取active中一整行，只返回已装载的正式状态。
        ReadOutput, // 读取成功Execute产生的八路输出，Commit/Revoke后不再有效。
        ReadHistory, // 读取正式历史，不返回尚未提交的next_history。
        Status, // 只读返回length、三种标签、候选/输出有效位及active银行号。
        Reset // 重置任务、所有有效性和银行角色，旧状态不再可读。
    };
    // GDN共享全局decay/beta，SSM使用逐元素decay，Conv4使用四组可装载权重和三组历史。
    enum class Mode { GDN, SSM, Conv4 };
    Op op = Op::Status;
    Mode mode = Mode::GDN;
    // Open的length为状态行数1..256；index按操作解释为状态行、系数元素或历史/抽头组。
    unsigned length = 1, index = 0;
    // Open保存owner/epoch/position，Execute和Commit必须匹配这三项。
    // next_position仅Commit使用，由调用方明确指定；epoch在Commit内部加1且禁止32位回绕。
    // decay/beta为UQ1.31编码，0x80000000表示1.0。
    uint32_t owner = 0, epoch = 0, position = 0, next_position = 0, decay = 0x80000000U,
             beta = 0x80000000U;
    // values按操作承载一行状态、X、inject、skip或一组历史；状态/X/inject的二进制尺度由外部一致约定。
    // x_=当前输入/目标，inject_=外算注入项，skip_=Q16.16系数，error_=GDN修正量，out_=最近读出。
    std::array<int32_t, 8> values{};
    // 仅DecayRow读取，八lane逐元素衰减因子，合法0..0x80000000。
    std::array<uint32_t, 8> factors{};
    // Taps读取全部八项；Key/Query只读取第0项，写入index指定的单个系数。
    std::array<int16_t, 8> coefficients{};
};
class REngine {
    // 物理两银行，每bank2048*S32=8KiB。地址=row*8+lane；active_选择正式bank，另一份是shadow。
    // shadow在SSM执行前暂存因子，执行后变为候选状态，不能同时当成第三份因子RAM。
    std::array<std::array<int32_t, 2048>, 2> state_{};
    unsigned active_ = 0;
    // 按行/系数记录已装数据；这些布尔数组是可读事务模型的有效性表达，非逐位复制RTL分组有效位。
    std::array<bool, 256> state_valid_{}, decay_valid_{}, key_valid_{}, query_valid_{};
    // GDN：key_=K、query_=Q；SSM：key_=B、query_=C；所有系数Q1.14。
    std::array<int16_t, 256> key_{}, query_{};
    std::array<int32_t, 8> x_{}, inject_{}, skip_{}, error_{}, out_{};
    // history_按最近、次近、第三近各8lane排列；next_history_只有Commit才转为正式历史。
    std::array<int32_t, 24> history_{}, next_history_{};
    // taps_[tap*8+lane]；固定4抽头布局、权重可加载，不是任意核长卷积。
    std::array<int16_t, 32> taps_{};
    // 三组历史和四组抽头的装载完成标志，Conv4必须全部齐备。
    std::array<bool, 3> history_valid_{};
    std::array<bool, 4> taps_valid_{};
    // valid_=Open成功；parameters_/x_valid_/inject_valid_/skip_valid_记录各组输入是否齐备。
    bool valid_ = false, parameters_ = false, x_valid_ = false, inject_valid_ = false,
         skip_valid_ = false;
    // pending_state_/pending_history_表示已有成功候选，不能直接覆盖；output_valid_控制ReadOutput。
    // 成功Conv4之后可以继续做状态计算；若后者失败，已有pending_history_仍需显式处理。
    bool pending_state_ = false, pending_history_ = false, output_valid_ = false;
    // 当前任务规模和正式标签；decay_/beta_保留配置，可跨步复用。
    unsigned length_ = 0;
    uint32_t owner_ = 0, epoch_ = 0, position_ = 0, decay_ = 0, beta_ = 0;
    // 对Execute/Commit检查本次操作是否属于同一状态版本；只比较标签，不隐含更强的系统认证。
    bool matches(const RCommand &c) const {
        return c.owner == owner_ && c.epoch == epoch_ && c.position == position_;
    }
    // 每个要求S32的算术边界都先检查范围，失败累积到failed，再模拟低32位写入候选寄存器。
    // 计算可继续以复现窄化边界，但failed最终使候选无效，active绝不会提交这些溢出值。
    static int32_t checked(Wide v, bool &failed) {
        failed |= !fits(v, 32);
        return wrap32(v);
    }

  public:
    using Command = RCommand;
    using Response = Reply;
    // 执行完整状态事务。输入未齐或标签错误在改动计算状态前拒绝；算术失败返回error。
    // Execute成功只置pending；Commit才公开新状态，因此读取旧状态/撤销都具有确定行为。
    Response execute(const Command &c) {
        auto r = reply(c);
        unsigned shadow = active_ ^ 1;
        switch (c.op) {
        // 重置任务、所有有效性和银行角色，旧状态不再可读。
        case Command::Op::Reset:
            *this = REngine{};
            break;
        // 建立length和owner/epoch/position，必须先处理已有候选。
        case Command::Op::Open:
            if (c.length < 1 || c.length > 256 || pending_state_ || pending_history_)
                return reply(c, true);
            length_ = c.length;
            owner_ = c.owner;
            epoch_ = c.epoch;
            position_ = c.position;
            valid_ = true;
            state_valid_.fill(false);
            decay_valid_.fill(false);
            key_valid_.fill(false);
            query_valid_.fill(false);
            history_valid_.fill(false);
            taps_valid_.fill(false);
            parameters_ = x_valid_ = inject_valid_ = skip_valid_ = output_valid_ = false;
            break;
        // 将8个S32写到正式状态的index行，标记该行已装载。
        case Command::Op::StateRow:
        // 将8个UQ1.31因子写到shadow的index行，供下一次SSM使用。
        case Command::Op::DecayRow:
            if (!valid_ || c.index >= length_ || pending_state_ || pending_history_)
                return reply(c, true);
            if (c.op == Command::Op::DecayRow)
                for (auto f : c.factors)
                    if (f > 0x80000000U)
                        return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                state_[c.op == Command::Op::StateRow ? active_ : shadow][c.index * 8 + i] =
                    c.op == Command::Op::StateRow ? c.values[i] : wrap32(c.factors[i]);
            (c.op == Command::Op::StateRow ? state_valid_ : decay_valid_)[c.index] = true;
            break;
        // coefficients[0]写第index个K或B系数，Q1.14。
        case Command::Op::Key:
        // coefficients[0]写第index个Q或C系数，Q1.14。
        case Command::Op::Query:
            if (!valid_ || c.index >= 256 || pending_state_)
                return reply(c, true);
            (c.op == Command::Op::Key ? key_ : query_)[c.index] = c.coefficients[0];
            (c.op == Command::Op::Key ? key_valid_ : query_valid_)[c.index] = true;
            break;
        // 装本次当前输入/目标值，八个S32。
        case Command::Op::X:
        // 装已由外部计算的SSM注入量，例如dt*X。
        case Command::Op::Inject:
        // 装八路S32 Q16.16的SSM skip系数。
        case Command::Op::Skip:
            if (!valid_ || pending_state_)
                return reply(c, true);
            if (c.op == Command::Op::X) {
                x_ = c.values;
                x_valid_ = true;
            }
            if (c.op == Command::Op::Inject) {
                inject_ = c.values;
                inject_valid_ = true;
            }
            if (c.op == Command::Op::Skip) {
                skip_ = c.values;
                skip_valid_ = true;
            }
            break;
        // 设置全局GDN decay/beta，每项UQ1.31且<=1。
        case Command::Op::Parameters:
            if (!valid_ || pending_state_ || c.decay > 0x80000000U || c.beta > 0x80000000U)
                return reply(c, true);
            decay_ = c.decay;
            beta_ = c.beta;
            parameters_ = true;
            break;
        // 装index=0..2的八路过去输入，最近历史在index0。
        case Command::Op::History:
            if (!valid_ || pending_state_ || pending_history_ || c.index > 2)
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                history_[c.index * 8 + i] = c.values[i];
            history_valid_[c.index] = true;
            break;
        // 装index=0..3的八路Q1.14卷积权重，0对应当前输入。
        case Command::Op::Taps:
            if (!valid_ || pending_state_ || pending_history_ || c.index > 3)
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                taps_[c.index * 8 + i] = c.coefficients[i];
            taps_valid_[c.index] = true;
            break;
        // 核验标签和输入齐备性，再生成候选状态/历史及输出。
        case Command::Op::Execute: {
            if (!valid_ || !matches(c) || pending_state_ || unsigned(c.mode) > 2)
                return reply(c, true);
            bool conv = c.mode == Command::Mode::Conv4, ssm = c.mode == Command::Mode::SSM;
            if (!x_valid_)
                return reply(c, true);
            if (conv) {
                if (pending_history_ ||
                    !std::all_of(history_valid_.begin(), history_valid_.end(),
                                 [](bool b) { return b; }) ||
                    !std::all_of(taps_valid_.begin(), taps_valid_.end(), [](bool b) { return b; }))
                    return reply(c, true);
            } else {
                if (!parameters_ || (ssm && (!inject_valid_ || !skip_valid_)))
                    return reply(c, true);
                for (unsigned row = 0; row < length_; ++row)
                    if (!state_valid_[row] || !key_valid_[row] || !query_valid_[row] ||
                        (ssm && !decay_valid_[row]))
                        return reply(c, true);
            }
            // 以下才开始实际计算：每个S32边界检查都汇入failed，输出有效性在结尾统一确定。
            bool failed = false;
            output_valid_ = false;
            if (conv) {
                for (unsigned i = 0; i < 8; ++i) {
                    // Conv4：y=RNE14(tap0*x+tap1*h0+tap2*h1+tap3*h2)，每lane独立。
                    // 新历史候选为[x,h0,h1]，本步没有修改正式history_。
                    Wide dot = Wide(x_[i]) * taps_[i];
                    for (unsigned t = 1; t < 4; ++t)
                        dot += Wide(history_[(t - 1) * 8 + i]) * taps_[t * 8 + i];
                    out_[i] = checked(rne(dot, 14), failed);
                    next_history_[i] = x_[i];
                    next_history_[8 + i] = history_[i];
                    next_history_[16 + i] = history_[8 + i];
                }
                if (!failed)
                    pending_history_ = true;
            } else {
                for (unsigned row = 0; row < length_; ++row)
                    for (unsigned i = 0; i < 8; ++i) {
                        unsigned a = row * 8 + i;
                        // 第一阶段衰减：Sd=RNE31(Sold*d)。SSM先从shadow读出该元素因子，再覆盖同一位置。
                        uint32_t d = ssm ? uint32_t(state_[shadow][a]) : decay_;
                        state_[shadow][a] = checked(rne(Wide(state_[active_][a]) * d, 31), failed);
                    }
                // 本次执行已经消耗shadow中的因子存储；无论后续成功失败，下一次SSM都必须重新装因子。
                decay_valid_.fill(false);
                if (!ssm)
                    for (unsigned i = 0; i < 8; ++i) {
                        Wide dot = 0;
                        for (unsigned row = 0; row < length_; ++row)
                            dot += Wide(state_[shadow][row * 8 + i]) * key_[row];
                        // GDN：p=RNE14(sum(Sd*K))，delta=X-p，error=RNE31(delta*beta)。
                        // 预测、误差减法与beta缩放分别检查S32边界，不能只检查最终结果。
                        int32_t predicted = checked(rne(dot, 14), failed);
                        int32_t delta = checked(Wide(x_[i]) - predicted, failed);
                        error_[i] = checked(rne(Wide(delta) * beta_, 31), failed);
                    }
                for (unsigned row = 0; row < length_; ++row)
                    for (unsigned i = 0; i < 8; ++i) {
                        unsigned a = row * 8 + i;
                        state_[shadow][a] =
                            // 第二阶段：Snew=Sd+RNE14(K*error)或Sd+RNE14(B*inject)。
                            // 更新留在shadow，正式bank继续可读。
                            checked(Wide(state_[shadow][a]) +
                                        rne(Wide(key_[row]) * (ssm ? inject_[i] : error_[i]), 14),
                                    failed);
                    }
                // 第三阶段：由更新后的shadow与Q/C点积读出；SSM另加RNE16(X*skip)。
                for (unsigned i = 0; i < 8; ++i) {
                    Wide dot = 0;
                    for (unsigned row = 0; row < length_; ++row)
                        dot += Wide(state_[shadow][row * 8 + i]) * query_[row];
                    out_[i] = checked(rne(dot, 14), failed);
                    if (ssm)
                        out_[i] = checked(Wide(out_[i]) + rne(Wide(x_[i]) * skip_[i], 16), failed);
                }
                if (!failed)
                    pending_state_ = true;
            }
            // 失败不新建pending_state_/pending_history_，也不抹去此前成功卷积的pending_history_。
            output_valid_ = !failed;
            r.error = failed;
            break;
        }
        // 核验旧标签，交换银行/提交历史，epoch+1并更新position。
        case Command::Op::Commit:
            if (!valid_ || (!pending_state_ && !pending_history_) || !matches(c) ||
                epoch_ == 0xffffffffU)
                return reply(c, true);
            // Commit是可见状态改变点：有状态候选才交换bank，有历史候选才复制历史；然后推进版本。
            if (pending_state_)
                active_ ^= 1;
            if (pending_history_)
                history_ = next_history_;
            pending_state_ = pending_history_ = false;
            position_ = c.next_position;
            ++epoch_;
            x_valid_ = inject_valid_ = output_valid_ = false;
            break;
        // 清除候选和输出有效性，正式状态不变，SSM因子需重装。
        case Command::Op::Revoke:
            pending_state_ = pending_history_ = output_valid_ = false;
            decay_valid_.fill(false);
            break;
        // 读取active中一整行，只返回已装载的正式状态。
        case Command::Op::ReadState:
            if (!valid_ || c.index >= length_ || !state_valid_[c.index])
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                r.lane[i] = state_[active_][c.index * 8 + i];
            r.count = 8;
            break;
        // 读取成功Execute产生的八路输出，Commit/Revoke后不再有效。
        case Command::Op::ReadOutput:
            if (!output_valid_)
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                r.lane[i] = out_[i];
            r.count = 8;
            break;
        // 读取正式历史，不返回尚未提交的next_history。
        case Command::Op::ReadHistory:
            if (!valid_ || c.index > 2 || !history_valid_[c.index])
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                r.lane[i] = history_[c.index * 8 + i];
            r.count = 8;
            break;
        // 只读返回length、三种标签、候选/输出有效位及active银行号。
        case Command::Op::Status:
            // Status.lane[0..7]=length/owner/epoch/position/pending_state/pending_history/output_valid/active。
            r.lane = {{int64_t(length_), owner_, epoch_, position_, pending_state_,
                       pending_history_, output_valid_, int64_t(active_)}};
            r.count = 8;
            break;
        default:
            return reply(c, true);
        }
        return r;
    }
};
} // namespace blocks
