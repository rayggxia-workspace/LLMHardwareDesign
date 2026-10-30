#pragma once
#include "common.hpp"
namespace blocks {
struct MCommand : Printable {
    enum class Op {
        Reset,
        LoadA,
        LoadB,
        Scale,
        Execute,
        ReadFull,
        ReadFinal,
        ReadPartial,
        InvalidateBank,
        InvalidateAll
    };
    Op op = Op::Reset;
    unsigned bank = 0, row = 0, tile = 0, half = 0, rows = 1, tiles = 1, last_k = 8, columns = 8,
             shift = 0, width = 16, pair = 0;
    bool wide_a = false, wide_b = false, clear = true;
    int16_t coefficient = 1;
    Line data{};
};
class MEngine {
    std::array<int16_t, 512> a_{}, b_{};
    std::array<bool, 64> a_valid_{}, a_format_{};
    std::array<uint8_t, 8> b_valid_{};
    std::array<bool, 8> b_format_{};
    std::array<int64_t, 64> result_{};
    std::array<bool, 8> result_valid_{};
    std::array<unsigned, 8> columns_{};
    std::array<int64_t, 16> partial_{}; // physically two rows, S40 values
    std::array<int, 2> partial_owner_{{-1, -1}};
    int16_t coefficient_ = 1;
    unsigned shift_ = 0;

  public:
    using Command = MCommand;
    using Response = Reply;
    Response execute(const Command &c) {
        auto r = reply(c);
        switch (c.op) {
        case Command::Op::Reset:
            *this = MEngine{};
            break;
        case Command::Op::LoadA: {
            if (c.bank > 1 || c.row > 7 || c.tile > 3)
                return reply(c, true);
            unsigned slot = c.bank * 32 + c.row * 4 + c.tile;
            for (unsigned k = 0; k < 8; ++k)
                a_[slot * 8 + k] =
                    c.wide_a ? signed16(halfword(c.data, k)) : int16_t(int8_t(byte(c.data, k)));
            a_valid_[slot] = true;
            a_format_[slot] = c.wide_a;
            break;
        }
        case Command::Op::LoadB: {
            if (c.bank > 1 || c.tile > 3 || c.half > 1 || (!c.wide_b && c.half) ||
                (c.wide_b && c.half &&
                 (!(b_valid_[c.bank * 4 + c.tile] & 1) || !b_format_[c.bank * 4 + c.tile])))
                return reply(c, true);
            unsigned slot = c.bank * 4 + c.tile;
            if (c.wide_b)
                for (unsigned k = 0; k < 32; ++k)
                    b_[slot * 64 + c.half * 32 + k] = signed16(halfword(c.data, k));
            else
                for (unsigned k = 0; k < 64; ++k)
                    b_[slot * 64 + k] = int8_t(byte(c.data, k));
            b_format_[slot] = c.wide_b;
            b_valid_[slot] = c.wide_b && !c.half ? 1 : 3;
            break;
        }
        case Command::Op::Scale:
            if (c.shift > 31)
                return reply(c, true);
            coefficient_ = c.coefficient;
            shift_ = c.shift;
            break;
        case Command::Op::Execute: {
            if (c.bank > 1 || c.rows < 1 || c.rows > 8 || c.tiles < 1 || c.tiles > 4 ||
                c.last_k < 1 || c.last_k > 8 || c.columns < 1 || c.columns > 8)
                return reply(c, true);
            for (unsigned t = 0; t < c.tiles; ++t) {
                unsigned bi = c.bank * 4 + t;
                if (b_valid_[bi] != 3 || b_format_[bi] != c.wide_b)
                    return reply(c, true);
                for (unsigned row = 0; row < c.rows; ++row) {
                    unsigned ai = c.bank * 32 + row * 4 + t;
                    if (!a_valid_[ai] || a_format_[ai] != c.wide_a)
                        return reply(c, true);
                }
            }
            for (unsigned row = 0; row < c.rows; ++row)
                if (!c.clear && (!result_valid_[row] || columns_[row] != c.columns))
                    return reply(c, true);
            partial_owner_ = {{-1, -1}};
            for (unsigned row = 0; row < c.rows; ++row) {
                unsigned pb = row % 2;
                partial_owner_[pb] = int(row);
                std::array<int64_t, 8> candidate{};
                bool fault = false;
                for (unsigned n = 0; n < 8; ++n) {
                    Wide dot = 0;
                    if (n < c.columns)
                        for (unsigned t = 0; t < c.tiles; ++t)
                            for (unsigned k = 0; k < (t + 1 == c.tiles ? c.last_k : 8); ++k)
                                dot += Wide(a_[c.bank * 256 + row * 32 + t * 8 + k]) *
                                       b_[(c.bank * 4 + t) * 64 + n * 8 + k];
                    partial_[pb * 8 + n] = int64_t(dot);
                    fault |= !fits(dot, 40);
                    Wide scaled = dot * coefficient_ * power(shift_);
                    fault |= !fits(scaled, 64);
                    Wide merged = scaled + (c.clear ? 0 : Wide(result_[row * 8 + n]));
                    fault |= !fits(merged, 64);
                    candidate[n] = fits(merged, 64) ? int64_t(merged) : 0;
                }
                if (fault)
                    r.failed_rows |= uint8_t(1U << row);
                else {
                    for (unsigned n = 0; n < 8; ++n)
                        result_[row * 8 + n] = candidate[n];
                    result_valid_[row] = true;
                    columns_[row] = c.columns;
                }
            }
            r.error = r.failed_rows != 0;
            break;
        }
        case Command::Op::ReadFull:
            if (c.row > 7 || c.pair > 3 || !result_valid_[c.row])
                return reply(c, true);
            r.count = 2;
            for (unsigned i = 0; i < 2; ++i)
                r.lane[i] = result_[c.row * 8 + c.pair * 2 + i];
            break;
        case Command::Op::ReadPartial:
            if (c.row > 7 || c.pair > 3 || partial_owner_[c.row % 2] != int(c.row))
                return reply(c, true);
            r.count = 2;
            for (unsigned i = 0; i < 2; ++i)
                r.lane[i] = partial_[(c.row % 2) * 8 + c.pair * 2 + i];
            break;
        case Command::Op::ReadFinal:
            if (c.row > 7 || c.half > 1 || !result_valid_[c.row] || c.shift > 63 ||
                (c.width != 8 && c.width != 16 && c.width != 32))
                return reply(c, true);
            r.count = 4;
            for (unsigned i = 0; i < 4; ++i)
                r.lane[i] =
                    clamp(rne(result_[c.row * 8 + c.half * 4 + i], c.shift), c.width, r.saturated);
            break;
        case Command::Op::InvalidateAll:
            a_valid_.fill(false);
            b_valid_.fill(0);
            result_valid_.fill(false);
            partial_owner_ = {{-1, -1}};
            break;
        case Command::Op::InvalidateBank:
            if (c.bank > 1)
                return reply(c, true);
            for (unsigned i = 0; i < 32; ++i)
                a_valid_[c.bank * 32 + i] = false;
            for (unsigned i = 0; i < 4; ++i)
                b_valid_[c.bank * 4 + i] = 0;
            break;
        default:
            return reply(c, true);
        }
        return r;
    }
};
} // namespace blocks
