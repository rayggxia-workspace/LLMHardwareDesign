/**
 * N：长向量归约、归一化和有限TopK的事务模型。
 * Softmax：Begin -> Stats若干 -> Finalize -> Exp若干 -> FinishExp -> SoftReplay若干。
 * RMS/L2：Begin -> Stats若干 -> Finalize -> NormReplay若干。
 * 只有一套向量统计上下文，没有整向量/256元素缓冲；x和EXP由S或调用方保存后回放。
 * 每个向量事务最多8元素；RTL内部两lane处理的拍数被折叠。TopK另有最多40项有限存储。
 */
#pragma once
#include "common.hpp"
#include "tables.hpp"
namespace blocks {
struct NCommand : Printable {
    enum class Op {
        Begin, // 开始/替换向量上下文，清零统计与回放计数，不清除独立TopK任务。
        Stats, // 累计本批1..8个S16的sum/sumsq/max/min，长度上限65535。
        Finalize, // 封闭统计；Softmax仅锁定最大值，RMS/L2同时生成归一化因子。
        Exp, // 用最终max计算本批指数，返回EXP并累计分母，调用方需保存返回值。
        FinishExp, // 仅在全部EXP到齐后，根据最终分母生成Softmax因子。
        NormReplay, // 输入原始S16与gamma，使用RMS/L2因子输出S16。
        SoftReplay, // 输入保存的无符号EXP，输出非负S16 Q1.14概率。
        ReadStats, // 只读查看统计及调试计数，不推进向量流程。
        TopBegin, // 建立独立TopK任务，设置k=1..8并清空其装载计数。
        TopLoad, // 每次装最多4组S16分数/U16 ID，累计不超过40项。
        TopSelect, // 反复选择最优未选项，返回k个ID后关闭本次TopK装载。
        ReadFactor, // 读取最终有效因子；尚未形成时拒绝。
        Reset // 重置向量和TopK两类上下文及有效性。
    };
    // Softmax输入x为Q5.10；RMS/L2按原始整数平方单位统计，gamma为Q5.10。
    enum class Mode { Softmax, RMS, L2 };
    Op op = Op::Begin;
    Mode mode = Mode::Softmax;
    // epsilon仅在RMS/L2时使用，必须非零，单位是原始输入整数的平方；不是预编码浮点。
    // count为本命令有效元素数（通常1..8，TopLoad为1..4），k仅TopBegin使用。
    uint32_t epsilon = 1;
    unsigned count = 8, k = 1;
    // SoftReplay uses unsigned EXP encodings 0..32768; other inputs are S16.
    // data承载原始16位位型：Stats/Exp/NormReplay按S16解释，SoftReplay按U16解释。
    // SoftReplay合法EXP编码0..32768，其中32768表示UQ1.15的1，不能误解为S16的-32768。
    std::array<uint16_t, 8> data{};
    // 仅NormReplay使用，每个gamma原始值1024表示1.0；SoftReplay不乘gamma。
    std::array<int16_t, 8> gamma{};
    // TopLoad中与data前count个分数配对的专家/选择ID，不表示该ID对应数据已搬运。
    std::array<uint16_t, 4> ids{};
};
class NEngine {
    // valid_=任务已建立，final_=禁止继续Stats，factor_valid_=允许归一化回放。
    // top_loading_属于独立TopK装载流程，不是第二套Softmax ping-pong上下文。
    bool valid_ = false, final_ = false, factor_valid_ = false, top_loading_ = false;
    NCommand::Mode mode_ = NCommand::Mode::Softmax;
    // epsilon_保存正则项；factor_按模式解释；exp_sum_累计UQ1.15编码，不能提前用局部和归一化。
    uint32_t epsilon_ = 0, factor_ = 0, exp_sum_ = 0;
    // count_=Stats累计元素数；exp_count_=Exp累计元素数；replayed_=归一化输出元素数。
    // top_count_=已装候选个数、k_=需选个数；主机unsigned容器不改变硬件16位向量计数合同。
    unsigned count_ = 0, exp_count_ = 0, replayed_ = 0, top_count_ = 0, k_ = 0;
    // S32普通求和；最大65535个S16元素在此范围内，Stats只访问本批真实收到的数据。
    int32_t sum_ = 0;
    // 物理合同U48平方和，主机用U64存储；Finalize左移16位并做U64精确除法/平方根。
    uint64_t sumsq_ = 0;
    // 运行中最大/最小值；初始为S16下界/上界。未收到的后续批次不会被预读。
    int16_t max_ = -32768, min_ = 32767;
    // 独立40项TopK分数与ID存储；全选只返回ID，不包含通用排序网络或MoE分发器。
    std::array<int16_t, 40> scores_{};
    std::array<uint16_t, 40> ids_{};

  public:
    using Command = NCommand;
    using Response = Reply;
    // 输入difference是x_raw-max_raw，Q5.10且至少17位带符号；小于-16返回0，非负返回32768。
    // 表网格1/64对应原始编码16；j为区间下标，frac为区间内0..15偏移，RNE作用于插值增量。
    static uint16_t exponential(int difference) {
        if (difference < -16384)
            return 0;
        if (difference >= 0)
            return 32768;
        unsigned offset = unsigned(difference + 16384), j = offset / 16, frac = offset % 16;
        return uint16_t(table::exp[j] + rne(Wide(table::exp[j + 1] - table::exp[j]) * frac, 4));
    }
    // 先验证阶段、模式和累计计数，再改变状态；拒绝的分块不会消耗元素配额。
    // 本模型只核验数量/顺序，不能验证回放内容是否与先前输入完全相同，此责任属于调用方。
    Response execute(const Command &c) {
        auto r = reply(c);
        bool chunk = c.count >= 1 && c.count <= 8;
        switch (c.op) {
        // 重置向量和TopK两类上下文及有效性。
        case Command::Op::Reset:
            *this = NEngine{};
            break;
        // 开始/替换向量上下文，清零统计与回放计数，不清除独立TopK任务。
        case Command::Op::Begin:
            if (unsigned(c.mode) > 2 || (c.mode != Command::Mode::Softmax && c.epsilon == 0))
                return reply(c, true);
            mode_ = c.mode;
            epsilon_ = c.epsilon;
            valid_ = true;
            final_ = factor_valid_ = false;
            count_ = exp_count_ = replayed_ = 0;
            sum_ = 0;
            sumsq_ = 0;
            exp_sum_ = 0;
            max_ = -32768;
            min_ = 32767;
            break;
        // 累计本批1..8个S16的sum/sumsq/max/min，长度上限65535。
        case Command::Op::Stats:
            if (!valid_ || final_ || !chunk || count_ + c.count > 65535)
                return reply(c, true);
            for (unsigned i = 0; i < c.count; ++i) {
                int16_t x = signed16(c.data[i]);
                sum_ += x;
                sumsq_ += int64_t(x) * x;
                max_ = std::max(max_, x);
                min_ = std::min(min_, x);
            }
            count_ += c.count;
            break;
        // 封闭统计；Softmax仅锁定最大值，RMS/L2同时生成归一化因子。
        case Command::Op::Finalize: {
            if (!valid_ || final_ || !count_)
                return reply(c, true);
            final_ = true;
            if (mode_ == Command::Mode::Softmax)
                break;
            // Q16附加精度：RMS的d=floor(sumsq*2^16/count)+epsilon*2^16；L2不除count。
            // root=floor(sqrt(d))；factor=floor(2^38/root)，要求可用U32表示。
            uint64_t d = sumsq_ * 65536ULL;
            if (mode_ == Command::Mode::RMS)
                d /= count_;
            d += uint64_t(epsilon_) * 65536ULL;
            uint64_t root = isqrt(d), f = root ? (uint64_t(1) << 38) / root : 0;
            factor_valid_ = root && f <= 0xffffffffULL;
            factor_ = uint32_t(f);
            r.error = !factor_valid_;
            break;
        }
        // 用最终max计算本批指数，返回EXP并累计分母，调用方需保存返回值。
        case Command::Op::Exp:
            if (!valid_ || mode_ != Command::Mode::Softmax || !final_ || factor_valid_ || !chunk ||
                exp_count_ + c.count > count_)
                return reply(c, true);
            r.count = c.count;
            for (unsigned i = 0; i < c.count; ++i) {
                auto e = exponential(int(signed16(c.data[i])) - max_);
                r.lane[i] = e;
                exp_sum_ += e;
            }
            exp_count_ += c.count;
            break;
        // 仅在全部EXP到齐后，根据最终分母生成Softmax因子。
        case Command::Op::FinishExp: {
            if (!valid_ || mode_ != Command::Mode::Softmax || !final_ || factor_valid_ ||
                exp_count_ != count_ || !exp_sum_)
                return reply(c, true);
            // 令e为UQ1.15整数编码，factor=floor(2^44/sum(e))。
            // 输出RNE(e*factor/2^30)约等于概率乘2^14，因此1.0编码16384并可直接作为M的非负S16输入。
            uint64_t f = (uint64_t(1) << 44) / exp_sum_;
            factor_ = uint32_t(f);
            factor_valid_ = f <= 0xffffffffULL;
            r.error = !factor_valid_;
            break;
        }
        // 输入原始S16与gamma，使用RMS/L2因子输出S16。
        case Command::Op::NormReplay:
        // 输入保存的无符号EXP，输出非负S16 Q1.14概率。
        case Command::Op::SoftReplay: {
            bool soft = c.op == Command::Op::SoftReplay;
            if (!valid_ || !factor_valid_ || !chunk || replayed_ + c.count > count_ ||
                soft != (mode_ == Command::Mode::Softmax))
                return reply(c, true);
            if (soft)
                for (unsigned i = 0; i < c.count; ++i)
                    if (c.data[i] > 32768)
                        return reply(c, true);
            r.count = c.count;
            for (unsigned i = 0; i < c.count; ++i) {
                // SoftReplay：RNE(e*factor/2^30)；NormReplay：RNE(x*factor*gamma/2^30)。
                // 两种操作共用因子/输出处理，本事务内只在完整乘积上舍入一次。
                Wide v = Wide(soft ? int(c.data[i]) : int(signed16(c.data[i]))) * factor_;
                if (!soft)
                    v *= c.gamma[i];
                v = rne(v, 30);
                if (soft) {
                    if (v < 0) {
                        v = 0;
                        r.saturated = true;
                    }
                    if (v > 16384) {
                        v = 16384;
                        r.saturated = true;
                    }
                    r.lane[i] = int64_t(v);
                } else
                    r.lane[i] = clamp(v, 16, r.saturated);
            }
            replayed_ += c.count;
            break;
        }
        // 只读查看统计及调试计数，不推进向量流程。
        case Command::Op::ReadStats:
            if (!valid_)
                return reply(c, true);
            // 调试响应lane[0..7]依次为count/max/min/sum/sumsq/exp_count/exp_sum/replayed。
            // 这是事务级可观测信息的扩展，不代表RTL现有128位响应可同时带出全部字段。
            r.lane[0] = count_;
            r.lane[1] = max_;
            r.lane[2] = min_;
            r.lane[3] = sum_;
            r.lane[4] = int64_t(sumsq_);
            r.lane[5] = exp_count_;
            r.lane[6] = exp_sum_;
            r.lane[7] = replayed_;
            r.count = 8;
            break;
        // 读取最终有效因子；尚未形成时拒绝。
        case Command::Op::ReadFactor:
            if (!factor_valid_)
                return reply(c, true);
            r.lane[0] = factor_;
            r.count = 1;
            break;
        // 建立独立TopK任务，设置k=1..8并清空其装载计数。
        case Command::Op::TopBegin:
            if (c.k < 1 || c.k > 8)
                return reply(c, true);
            top_count_ = 0;
            k_ = c.k;
            top_loading_ = true;
            break;
        // 每次装最多4组S16分数/U16 ID，累计不超过40项。
        case Command::Op::TopLoad:
            if (!top_loading_ || c.count < 1 || c.count > 4 || top_count_ + c.count > 40)
                return reply(c, true);
            for (unsigned i = 0; i < c.count; ++i) {
                scores_[top_count_ + i] = signed16(c.data[i]);
                ids_[top_count_ + i] = c.ids[i];
            }
            top_count_ += c.count;
            break;
        // 反复选择最优未选项，返回k个ID后关闭本次TopK装载。
        case Command::Op::TopSelect: {
            if (!top_loading_ || !top_count_ || k_ > top_count_)
                return reply(c, true);
            // 本次选择的有限标记；每轮扫描未选项，分数大者优先，分数相等时ID小者优先。
            // 分数和ID都相同则保留较早装入项，选择过程中不改写原候选数据。
            std::array<bool, 40> chosen{};
            for (unsigned i = 0; i < k_; ++i) {
                unsigned best = 40;
                for (unsigned j = 0; j < top_count_; ++j)
                    if (!chosen[j] && (best == 40 || scores_[j] > scores_[best] ||
                                       (scores_[j] == scores_[best] && ids_[j] < ids_[best])))
                        best = j;
                chosen[best] = true;
                r.lane[i] = ids_[best];
            }
            r.count = k_;
            top_loading_ = false;
            break;
        }
        default:
            return reply(c, true);
        }
        return r;
    }
};
} // namespace blocks
