#pragma once
#include "common.hpp"
#include "tables.hpp"
namespace blocks {
struct NCommand : Printable {
    enum class Op {
        Begin,
        Stats,
        Finalize,
        Exp,
        FinishExp,
        NormReplay,
        SoftReplay,
        ReadStats,
        TopBegin,
        TopLoad,
        TopSelect,
        ReadFactor,
        Reset
    };
    enum class Mode { Softmax, RMS, L2 };
    Op op = Op::Begin;
    Mode mode = Mode::Softmax;
    uint32_t epsilon = 1;
    unsigned count = 8, k = 1;
    // SoftReplay uses unsigned EXP encodings 0..32768; other inputs are S16.
    std::array<uint16_t, 8> data{};
    std::array<int16_t, 8> gamma{};
    std::array<uint16_t, 4> ids{};
};
class NEngine {
    bool valid_ = false, final_ = false, factor_valid_ = false, top_loading_ = false;
    NCommand::Mode mode_ = NCommand::Mode::Softmax;
    uint32_t epsilon_ = 0, factor_ = 0, exp_sum_ = 0;
    unsigned count_ = 0, exp_count_ = 0, replayed_ = 0, top_count_ = 0, k_ = 0;
    int32_t sum_ = 0;
    uint64_t sumsq_ = 0;
    int16_t max_ = -32768, min_ = 32767;
    std::array<int16_t, 40> scores_{};
    std::array<uint16_t, 40> ids_{};

  public:
    using Command = NCommand;
    using Response = Reply;
    static uint16_t exponential(int difference) {
        if (difference < -16384)
            return 0;
        if (difference >= 0)
            return 32768;
        unsigned offset = unsigned(difference + 16384), j = offset / 16, frac = offset % 16;
        return uint16_t(table::exp[j] + rne(Wide(table::exp[j + 1] - table::exp[j]) * frac, 4));
    }
    Response execute(const Command &c) {
        auto r = reply(c);
        bool chunk = c.count >= 1 && c.count <= 8;
        switch (c.op) {
        case Command::Op::Reset:
            *this = NEngine{};
            break;
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
        case Command::Op::Finalize: {
            if (!valid_ || final_ || !count_)
                return reply(c, true);
            final_ = true;
            if (mode_ == Command::Mode::Softmax)
                break;
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
        case Command::Op::FinishExp: {
            if (!valid_ || mode_ != Command::Mode::Softmax || !final_ || factor_valid_ ||
                exp_count_ != count_ || !exp_sum_)
                return reply(c, true);
            uint64_t f = (uint64_t(1) << 44) / exp_sum_;
            factor_ = uint32_t(f);
            factor_valid_ = f <= 0xffffffffULL;
            r.error = !factor_valid_;
            break;
        }
        case Command::Op::NormReplay:
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
        case Command::Op::ReadStats:
            if (!valid_)
                return reply(c, true);
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
        case Command::Op::ReadFactor:
            if (!factor_valid_)
                return reply(c, true);
            r.lane[0] = factor_;
            r.count = 1;
            break;
        case Command::Op::TopBegin:
            if (c.k < 1 || c.k > 8)
                return reply(c, true);
            top_count_ = 0;
            k_ = c.k;
            top_loading_ = true;
            break;
        case Command::Op::TopLoad:
            if (!top_loading_ || c.count < 1 || c.count > 4 || top_count_ + c.count > 40)
                return reply(c, true);
            for (unsigned i = 0; i < c.count; ++i) {
                scores_[top_count_ + i] = signed16(c.data[i]);
                ids_[top_count_ + i] = c.ids[i];
            }
            top_count_ += c.count;
            break;
        case Command::Op::TopSelect: {
            if (!top_loading_ || !top_count_ || k_ > top_count_)
                return reply(c, true);
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
