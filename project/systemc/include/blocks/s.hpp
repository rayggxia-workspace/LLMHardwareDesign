#pragma once
#include "common.hpp"
namespace blocks {
struct SCommand : Printable {
    enum class Op { Read, Write, ReadWide, LoadBegin, LoadNext, Status, Reset };
    Op op = Op::Status;
    unsigned address = 0, bank = 0, rows = 1, tiles = 1, a_base = 0, b_base = 0;
    bool wide_a = false, wide_b = false, reuse_b = false;
    Word data{};
};
class SEngine {
    std::array<Word, 1024> memory_{};
    // Only a software diagnostic: physical RAM has no reset/initial-value promise.
    std::array<bool, 1024> initialized_{};
    bool loading_ = false, phase_a_ = false, aw_ = false, bw_ = false, reuse_ = false;
    unsigned bank_ = 0, rows_ = 0, tiles_ = 0, abase_ = 0, bbase_ = 0, tile_ = 0, row_ = 0,
             half_ = 0;

  public:
    using Command = SCommand;
    using Response = Reply;
    Response execute(const Command &c) {
        auto r = reply(c);
        switch (c.op) {
        case Command::Op::Reset:
            loading_ = false;
            break; // memory intentionally survives
        case Command::Op::Write:
            if (c.address >= 1024 || loading_)
                return reply(c, true);
            memory_[c.address] = c.data;
            initialized_[c.address] = true;
            r.bits[0] = c.data[0];
            r.bits[1] = c.data[1];
            break;
        case Command::Op::Read:
            if (c.address >= 1024 || loading_ || !initialized_[c.address])
                return reply(c, true);
            r.bits[0] = memory_[c.address][0];
            r.bits[1] = memory_[c.address][1];
            r.count = 1;
            break;
        case Command::Op::ReadWide:
            if (c.address >= 256 || loading_)
                return reply(c, true);
            for (unsigned i = 0; i < 4; ++i)
                if (!initialized_[c.address * 4 + i])
                    return reply(c, true);
            for (unsigned i = 0; i < 4; ++i)
                for (unsigned l = 0; l < 2; ++l)
                    r.bits[i * 2 + l] = memory_[c.address * 4 + i][l];
            r.count = 4;
            break;
        case Command::Op::LoadBegin:
            if (loading_ || c.bank > 1 || c.rows < 1 || c.rows > 8 || c.tiles < 1 || c.tiles > 4 ||
                c.a_base >= 1024 || c.b_base >= 1024 || c.a_base % 4 || c.b_base % 4 ||
                c.a_base + c.tiles * (c.rows > 4 ? 8 : 4) > 1024 ||
                (!c.reuse_b && c.b_base + c.tiles * (c.wide_b ? 8 : 4) > 1024))
                return reply(c, true);
            loading_ = true;
            bank_ = c.bank;
            rows_ = c.rows;
            tiles_ = c.tiles;
            abase_ = c.a_base;
            bbase_ = c.b_base;
            aw_ = c.wide_a;
            bw_ = c.wide_b;
            reuse_ = c.reuse_b;
            phase_a_ = reuse_;
            tile_ = row_ = half_ = 0;
            break;
        case Command::Op::LoadNext: {
            if (!loading_)
                return reply(c, true);
            // One typed beat per transaction. Consumer drives next only after
            // accepting the previous beat: no hidden unbounded staging queue.
            unsigned address = phase_a_ ? abase_ + tile_ * (rows_ > 4 ? 8 : 4) + row_
                                        : bbase_ + tile_ * (bw_ ? 8 : 4) + half_ * 4;
            unsigned words = phase_a_ ? 1 : 4;
            for (unsigned i = 0; i < words; ++i)
                if (!initialized_[address + i])
                    return reply(c, true);
            for (unsigned i = 0; i < words; ++i)
                for (unsigned l = 0; l < 2; ++l)
                    r.bits[i * 2 + l] = memory_[address + i][l];
            r.lane[0] = phase_a_ ? 0 : 1;
            r.lane[1] = bank_;
            r.lane[2] = phase_a_ ? row_ : half_;
            r.lane[3] = tile_;
            r.lane[4] = phase_a_ ? aw_ : bw_;
            r.count = words;
            if (!phase_a_) {
                if (bw_ && !half_)
                    half_ = 1;
                else {
                    half_ = 0;
                    phase_a_ = true;
                }
            } else if (++row_ == rows_) {
                row_ = 0;
                if (++tile_ == tiles_)
                    loading_ = false;
                else
                    phase_a_ = reuse_;
            }
            r.last = !loading_;
            break;
        }
        case Command::Op::Status:
            r.lane[0] = loading_;
            r.count = 1;
            break;
        default:
            return reply(c, true);
        }
        return r;
    }
};
} // namespace blocks
