#pragma once
#include "common.hpp"
namespace blocks {
struct ECommand : Printable {
    enum class Op {
        Add,
        Sub,
        Mul,
        Fma,
        Max,
        Min,
        Select,
        Left,
        ArithmeticRight,
        RoPE,
        RoundRight,
        Abs,
        Pack8,
        Reset
    };
    Op op = Op::Add;
    unsigned shift = 0;
    std::array<int16_t, 8> a{}, b{}, c{};
};
class EEngine {
  public:
    using Command = ECommand;
    using Response = Reply;
    Response execute(const Command &c) {
        auto r = reply(c);
        if (c.op == Command::Op::Reset)
            return r;
        if (unsigned(c.op) > 12 || c.shift > 31)
            return reply(c, true);
        r.count = 8;
        for (unsigned i = 0; i < 8; ++i) {
            Wide x = c.a[i], y = c.b[i], z = c.c[i], v = 0;
            bool round = false;
            switch (c.op) {
            case Command::Op::Add:
                v = x + y;
                break;
            case Command::Op::Sub:
                v = x - y;
                break;
            case Command::Op::Mul:
                v = x * y;
                round = true;
                break;
            case Command::Op::Fma:
                v = x * y + z;
                round = true;
                break;
            case Command::Op::Max:
                v = std::max(x, y);
                break;
            case Command::Op::Min:
                v = std::min(x, y);
                break;
            case Command::Op::Select:
                v = z ? x : y;
                break;
            case Command::Op::Left:
                v = x * power(c.shift);
                break;
            case Command::Op::ArithmeticRight:
                v = floor_shift(x, c.shift);
                break;
            case Command::Op::RoPE:
                v = x * c.b[i & ~1U] + (i % 2 ? 1 : -1) * Wide(c.a[i ^ 1]) * c.b[i | 1U];
                round = true;
                break;
            case Command::Op::RoundRight:
                v = x;
                round = true;
                break;
            case Command::Op::Abs:
                v = x < 0 ? -x : x;
                break;
            case Command::Op::Pack8:
                v = x;
                break;
            default:
                return reply(c, true);
            }
            if (round)
                v = rne(v, c.shift);
            r.lane[i] = clamp(v, c.op == Command::Op::Pack8 ? 8 : 16, r.saturated);
            if (c.op == Command::Op::Pack8)
                r.bits[0] |= uint64_t(uint8_t(r.lane[i])) << (8 * i);
        }
        return r;
    }
};
} // namespace blocks
