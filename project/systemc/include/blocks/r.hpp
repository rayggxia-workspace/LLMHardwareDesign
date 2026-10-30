#pragma once
#include "common.hpp"
namespace blocks {
// Coalesced rows replace packed half-row bus writes. Values retain raw scales.
struct RCommand : Printable {
    enum class Op {
        Open,
        StateRow,
        DecayRow,
        Key,
        Query,
        X,
        Inject,
        Parameters,
        Skip,
        History,
        Taps,
        Execute,
        Commit,
        Revoke,
        ReadState,
        ReadOutput,
        ReadHistory,
        Status,
        Reset
    };
    enum class Mode { GDN, SSM, Conv4 };
    Op op = Op::Status;
    Mode mode = Mode::GDN;
    unsigned length = 1, index = 0;
    uint32_t owner = 0, epoch = 0, position = 0, next_position = 0, decay = 0x80000000U,
             beta = 0x80000000U;
    std::array<int32_t, 8> values{};
    std::array<uint32_t, 8> factors{};
    std::array<int16_t, 8> coefficients{};
};
class REngine {
    std::array<std::array<int32_t, 2048>, 2> state_{};
    unsigned active_ = 0;
    std::array<bool, 256> state_valid_{}, decay_valid_{}, key_valid_{}, query_valid_{};
    std::array<int16_t, 256> key_{}, query_{};
    std::array<int32_t, 8> x_{}, inject_{}, skip_{}, error_{}, out_{};
    std::array<int32_t, 24> history_{}, next_history_{};
    std::array<int16_t, 32> taps_{};
    std::array<bool, 3> history_valid_{};
    std::array<bool, 4> taps_valid_{};
    bool valid_ = false, parameters_ = false, x_valid_ = false, inject_valid_ = false,
         skip_valid_ = false;
    bool pending_state_ = false, pending_history_ = false, output_valid_ = false;
    unsigned length_ = 0;
    uint32_t owner_ = 0, epoch_ = 0, position_ = 0, decay_ = 0, beta_ = 0;
    bool matches(const RCommand &c) const {
        return c.owner == owner_ && c.epoch == epoch_ && c.position == position_;
    }
    static int32_t checked(Wide v, bool &failed) {
        failed |= !fits(v, 32);
        return wrap32(v);
    }

  public:
    using Command = RCommand;
    using Response = Reply;
    Response execute(const Command &c) {
        auto r = reply(c);
        unsigned shadow = active_ ^ 1;
        switch (c.op) {
        case Command::Op::Reset:
            *this = REngine{};
            break;
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
        case Command::Op::StateRow:
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
        case Command::Op::Key:
        case Command::Op::Query:
            if (!valid_ || c.index >= 256 || pending_state_)
                return reply(c, true);
            (c.op == Command::Op::Key ? key_ : query_)[c.index] = c.coefficients[0];
            (c.op == Command::Op::Key ? key_valid_ : query_valid_)[c.index] = true;
            break;
        case Command::Op::X:
        case Command::Op::Inject:
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
        case Command::Op::Parameters:
            if (!valid_ || pending_state_ || c.decay > 0x80000000U || c.beta > 0x80000000U)
                return reply(c, true);
            decay_ = c.decay;
            beta_ = c.beta;
            parameters_ = true;
            break;
        case Command::Op::History:
            if (!valid_ || pending_state_ || pending_history_ || c.index > 2)
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                history_[c.index * 8 + i] = c.values[i];
            history_valid_[c.index] = true;
            break;
        case Command::Op::Taps:
            if (!valid_ || pending_state_ || pending_history_ || c.index > 3)
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                taps_[c.index * 8 + i] = c.coefficients[i];
            taps_valid_[c.index] = true;
            break;
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
            bool failed = false;
            output_valid_ = false;
            if (conv) {
                for (unsigned i = 0; i < 8; ++i) {
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
                        uint32_t d = ssm ? uint32_t(state_[shadow][a]) : decay_;
                        state_[shadow][a] = checked(rne(Wide(state_[active_][a]) * d, 31), failed);
                    }
                decay_valid_.fill(false);
                if (!ssm)
                    for (unsigned i = 0; i < 8; ++i) {
                        Wide dot = 0;
                        for (unsigned row = 0; row < length_; ++row)
                            dot += Wide(state_[shadow][row * 8 + i]) * key_[row];
                        int32_t predicted = checked(rne(dot, 14), failed);
                        int32_t delta = checked(Wide(x_[i]) - predicted, failed);
                        error_[i] = checked(rne(Wide(delta) * beta_, 31), failed);
                    }
                for (unsigned row = 0; row < length_; ++row)
                    for (unsigned i = 0; i < 8; ++i) {
                        unsigned a = row * 8 + i;
                        state_[shadow][a] =
                            checked(Wide(state_[shadow][a]) +
                                        rne(Wide(key_[row]) * (ssm ? inject_[i] : error_[i]), 14),
                                    failed);
                    }
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
            output_valid_ = !failed;
            r.error = failed;
            break;
        }
        case Command::Op::Commit:
            if (!valid_ || (!pending_state_ && !pending_history_) || !matches(c) ||
                epoch_ == 0xffffffffU)
                return reply(c, true);
            if (pending_state_)
                active_ ^= 1;
            if (pending_history_)
                history_ = next_history_;
            pending_state_ = pending_history_ = false;
            position_ = c.next_position;
            ++epoch_;
            x_valid_ = inject_valid_ = output_valid_ = false;
            break;
        case Command::Op::Revoke:
            pending_state_ = pending_history_ = output_valid_ = false;
            decay_valid_.fill(false);
            break;
        case Command::Op::ReadState:
            if (!valid_ || c.index >= length_ || !state_valid_[c.index])
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                r.lane[i] = state_[active_][c.index * 8 + i];
            r.count = 8;
            break;
        case Command::Op::ReadOutput:
            if (!output_valid_)
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                r.lane[i] = out_[i];
            r.count = 8;
            break;
        case Command::Op::ReadHistory:
            if (!valid_ || c.index > 2 || !history_valid_[c.index])
                return reply(c, true);
            for (unsigned i = 0; i < 8; ++i)
                r.lane[i] = history_[c.index * 8 + i];
            r.count = 8;
            break;
        case Command::Op::Status:
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
