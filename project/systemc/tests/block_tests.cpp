#include "blocks/modules.hpp"
#include <cmath>
#include <iostream>
#include <random>
#include <stdexcept>
#include <vector>
using namespace blocks;
static uint64_t checks = 0;
static void require(bool ok, const char *message) {
    ++checks;
    if (!ok)
        throw std::runtime_error(message);
}
static void ok(const Reply &r) { require(!r.error, "unexpected transaction rejection"); }
static void put16(Line &a, unsigned i, int value) {
    unsigned s = (i % 4) * 16;
    a[i / 4] = (a[i / 4] & ~(uint64_t(65535) << s)) | (uint64_t(uint16_t(value)) << s);
}
static void put8(Line &a, unsigned i, int value) {
    unsigned s = (i % 8) * 8;
    a[i / 8] = (a[i / 8] & ~(uint64_t(255) << s)) | (uint64_t(uint8_t(value)) << s);
}
static int64_t reference_round(int64_t x, unsigned shift) {
    // Independent magnitude-based implementation, used over safe S64 ranges.
    if (!shift)
        return x;
    uint64_t magnitude = x < 0 ? uint64_t(-(x + 1)) + 1 : uint64_t(x), q = magnitude >> shift;
    uint64_t rem = magnitude & ((uint64_t(1) << shift) - 1), half = uint64_t(1) << (shift - 1);
    if (rem > half || (rem == half && (q & 1)))
        ++q;
    return x < 0 ? -int64_t(q) : int64_t(q);
}
static void test_arithmetic() {
    for (int x = -2000; x <= 2000; ++x)
        for (unsigned s = 0; s < 11; ++s)
            require(rne(x, s) == reference_round(x, s), "signed RNE tie");
    std::mt19937_64 rng(145);
    for (unsigned i = 0; i < 20000; ++i) {
        uint64_t x = rng(), root = isqrt(x);
        require(Wide(root) * root <= x && Wide(root + 1) * (root + 1) > x,
                "integer square root floor");
    }
}
static void test_e() {
    EEngine e;
    ECommand c;
    c.op = ECommand::Op::RoPE;
    c.shift = 10;
    c.a = {{1024, 2048, -1024, -2048, 32767, -32768, 1, -1}};
    c.b = {{1024, 0, 0, 1024, 1024, 0, 1024, 0}};
    auto r = e.execute(c);
    ok(r);
    require(r.lane[0] == 1024 && r.lane[1] == 2048 && r.lane[2] == 2048 && r.lane[3] == -1024,
            "RoPE pair layout");
    c.op = ECommand::Op::Fma;
    c.a.fill(3);
    c.b.fill(5);
    c.c.fill(1);
    c.shift = 1;
    r = e.execute(c);
    require(r.lane[0] == 8, "FMA third operand in product units");
    c.op = ECommand::Op::Pack8;
    c.a = {{-32768, -129, -128, -1, 0, 127, 128, 32767}};
    r = e.execute(c);
    require(r.saturated && r.bits[0] == 0x7f7f7f00ff808080ULL, "signed eight-bit compact packing");
    c.op = ECommand::Op::Abs;
    c.a.fill(-32768);
    require(e.execute(c).lane[0] == 32767, "ABS saturation");
    std::mt19937 rng(145);
    for (unsigned op = 0; op < 13; ++op)
        for (unsigned z = 0; z < 1200; ++z) {
            c.op = ECommand::Op(op);
            c.shift = rng() % 32;
            for (unsigned i = 0; i < 8; ++i) {
                c.a[i] = signed16(uint16_t(rng()));
                c.b[i] = signed16(uint16_t(rng()));
                c.c[i] = signed16(uint16_t(rng()));
            }
            r = e.execute(c);
            ok(r);
            bool saturated = false;
            for (unsigned i = 0; i < 8; ++i) {
                int64_t a = c.a[i], b = c.b[i], d = c.c[i], v = 0;
                switch (op) {
                case 0:
                    v = a + b;
                    break;
                case 1:
                    v = a - b;
                    break;
                case 2:
                    v = reference_round(a * b, c.shift);
                    break;
                case 3:
                    v = reference_round(a * b + d, c.shift);
                    break;
                case 4:
                    v = std::max(a, b);
                    break;
                case 5:
                    v = std::min(a, b);
                    break;
                case 6:
                    v = d ? a : b;
                    break;
                case 7:
                    v = a * (int64_t(1) << c.shift);
                    break;
                case 8: {
                    int64_t den = int64_t(1) << c.shift;
                    v = a / den - (a % den < 0);
                    break;
                }
                case 9:
                    v = reference_round(a * c.b[i & ~1U] +
                                            (i % 2 ? 1 : -1) * int64_t(c.a[i ^ 1]) * c.b[i | 1U],
                                        c.shift);
                    break;
                case 10:
                    v = reference_round(a, c.shift);
                    break;
                case 11:
                    v = a < 0 ? -a : a;
                    break;
                case 12:
                    v = a;
                    break;
                }
                int64_t lo = op == 12 ? -128 : -32768, hi = op == 12 ? 127 : 32767;
                saturated |= v < lo || v > hi;
                v = std::max(lo, std::min(hi, v));
                require(r.lane[i] == v, "E integer reference");
            }
            require(r.saturated == saturated, "E saturation flag");
        }
    c.op = ECommand::Op(99);
    require(e.execute(c).error, "E invalid operation");
}
static void test_g() {
    GEngine g;
    GCommand c;
    for (unsigned fn = 0; fn < 4; ++fn) {
        c.function = GCommand::Function(fn);
        c.gated = false;
        double max_error = 0;
        for (int raw = -32768; raw <= 32766; raw += 2) {
            c.x = {{int16_t(raw), int16_t(raw + 1)}};
            auto r = g.execute(c);
            ok(r);
            for (unsigned i = 0; i < 2; ++i) {
                double x = c.x[i] / 1024.0,
                       y = fn == 0   ? x / (1 + std::exp(-x))
                           : fn == 1 ? 1 / (1 + std::exp(-x))
                           : fn == 2 ? 0.5 * x *
                                           (1 + std::tanh(std::sqrt(2 / std::acos(-1.0)) *
                                                          (x + 0.044715 * x * x * x)))
                                     : std::log1p(std::exp(x));
                double model = r.lane[i] / double(fn == 1 ? 16384 : 1024);
                max_error = std::max(max_error, std::abs(model - y));
            }
        }
        require(max_error < (fn == 0   ? 0.0027
                             : fn == 1 ? 0.00034
                                       : 0.001),
                "G full-domain function error bound");
        c.x = {{0, 1024}};
        c.gated = true;
        c.gate = {{1024, -1024}};
        auto gated = g.execute(c);
        c.gated = false;
        auto plain = g.execute(c);
        require(gated.lane[0] == (fn == 1 ? 512 : plain.lane[0]) &&
                    gated.lane[1] ==
                        (fn == 1 ? reference_round(-plain.lane[1] * 1024, 14) : -plain.lane[1]),
                "G gate output scale");
    }
    c.function = GCommand::Function(99);
    require(g.execute(c).error, "G invalid function");
}
static void load_m(MEngine &m, const std::array<std::array<int16_t, 32>, 8> &a,
                   const std::array<std::array<int16_t, 32>, 8> &b, bool aw, bool bw,
                   unsigned rows = 8, unsigned tiles = 4) {
    MCommand c;
    for (unsigned t = 0; t < tiles; ++t) {
        c.op = MCommand::Op::LoadB;
        c.tile = t;
        c.wide_b = bw;
        for (unsigned h = 0; h < (bw ? 2 : 1); ++h) {
            c.half = h;
            c.data = {};
            for (unsigned j = 0; j < (bw ? 32 : 64); ++j) {
                unsigned n = (j + h * 32) / 8, k = (j + h * 32) % 8;
                if (bw)
                    put16(c.data, j, b[n][t * 8 + k]);
                else
                    put8(c.data, j, b[n][t * 8 + k]);
            }
            ok(m.execute(c));
        }
        for (unsigned row = 0; row < rows; ++row) {
            c.op = MCommand::Op::LoadA;
            c.row = row;
            c.wide_a = aw;
            c.data = {};
            for (unsigned k = 0; k < 8; ++k)
                if (aw)
                    put16(c.data, k, a[row][t * 8 + k]);
                else
                    put8(c.data, k, a[row][t * 8 + k]);
            ok(m.execute(c));
        }
    }
}
static void test_m() {
    MEngine m;
    std::mt19937 rng(43);
    std::array<std::array<int16_t, 32>, 8> a{}, b{};
    for (unsigned trial = 0; trial < 48; ++trial) {
        bool aw = trial & 1, bw = trial & 2;
        unsigned rows = 1 + rng() % 8, tiles = 1 + rng() % 4, last = 1 + rng() % 8,
                 n = 1 + rng() % 8;
        for (auto &row : a)
            for (auto &v : row)
                v = aw ? signed16(uint16_t(rng())) : int8_t(rng());
        for (auto &row : b)
            for (auto &v : row)
                v = bw ? signed16(uint16_t(rng())) : int8_t(rng());
        load_m(m, a, b, aw, bw, rows, tiles);
        MCommand c;
        c.op = MCommand::Op::Scale;
        c.coefficient = -17;
        c.shift = 2;
        ok(m.execute(c));
        c.op = MCommand::Op::Execute;
        c.rows = rows;
        c.tiles = tiles;
        c.last_k = last;
        c.columns = n;
        c.wide_a = aw;
        c.wide_b = bw;
        ok(m.execute(c));
        for (unsigned row = 0; row < rows; ++row)
            for (unsigned pair = 0; pair < 4; ++pair) {
                c.op = MCommand::Op::ReadFull;
                c.row = row;
                c.pair = pair;
                auto r = m.execute(c);
                ok(r);
                for (unsigned j = 0; j < 2; ++j) {
                    unsigned col = pair * 2 + j;
                    int64_t dot = 0;
                    if (col < n)
                        for (unsigned k = 0; k < (tiles - 1) * 8 + last; ++k)
                            dot += int64_t(a[row][k]) * b[col][k];
                    require(r.lane[j] == dot * -68, "M all formats and K-tail");
                }
            }
        c.op = MCommand::Op::Execute;
        c.clear = false;
        ok(m.execute(c));
        c.op = MCommand::Op::ReadFull;
        c.row = 0;
        c.pair = 0;
        auto twice = m.execute(c);
        ok(twice);
        int64_t ref = 0;
        for (unsigned k = 0; k < (tiles - 1) * 8 + last; ++k)
            ref += int64_t(a[0][k]) * b[0][k];
        require(twice.lane[0] == ref * -136, "M segment append without early rounding");
        c.op = MCommand::Op::ReadPartial;
        c.row = rows - 1;
        ok(m.execute(c));
        if (rows > 2) {
            c.row = rows - 3;
            require(m.execute(c).error, "M nonresident partial row");
        }
    }
    for (auto &row : a)
        row.fill(32767);
    for (auto &row : b)
        row.fill(32767);
    a[1].fill(0);
    load_m(m, a, b, true, true, 2, 4);
    MCommand c;
    c.op = MCommand::Op::Scale;
    c.coefficient = 1;
    ok(m.execute(c));
    c.op = MCommand::Op::Execute;
    c.rows = 2;
    c.tiles = 4;
    c.wide_a = c.wide_b = true;
    ok(m.execute(c));
    c.op = MCommand::Op::ReadFull;
    auto before = m.execute(c);
    ok(before);
    c.op = MCommand::Op::Scale;
    c.coefficient = 32767;
    c.shift = 31;
    ok(m.execute(c));
    c.op = MCommand::Op::Execute;
    auto fault = m.execute(c);
    require(fault.error && fault.failed_rows == 1, "M row-level overflow mask");
    c.op = MCommand::Op::ReadFull;
    require(m.execute(c).lane[0] == before.lane[0], "M failed row retained");
    c.row = 1;
    require(m.execute(c).lane[0] == 0, "M successful row commits");
    c.row = 0;
    c.op = MCommand::Op::InvalidateBank;
    ok(m.execute(c));
    c.op = MCommand::Op::ReadFull;
    ok(m.execute(c));
    c.op = MCommand::Op::Execute;
    require(m.execute(c).error, "M rejects invalid operand banks");
}
static void softmax_case(unsigned length) {
    NEngine n;
    NCommand c;
    c.op = NCommand::Op::Begin;
    ok(n.execute(c));
    std::vector<int16_t> x(length);
    std::vector<uint16_t> exp(length);
    for (unsigned i = 0; i < length; ++i)
        x[i] = int16_t((int(i) % 17) * 79 - 600);
    if (length > 256)
        x.back() = 3000;
    for (unsigned start = 0; start < length; start += 8) {
        c.op = NCommand::Op::Stats;
        c.count = std::min(8U, length - start);
        for (unsigned i = 0; i < c.count; ++i)
            c.data[i] = uint16_t(x[start + i]);
        ok(n.execute(c));
        if (start == 248 && length > 256) {
            c.op = NCommand::Op::ReadStats;
            auto s = n.execute(c);
            require(s.lane[1] < 3000 && s.lane[0] == 256, "maximum cannot see unloaded tail");
        }
    }
    c.op = NCommand::Op::Finalize;
    ok(n.execute(c));
    c.op = NCommand::Op::ReadStats;
    auto stats = n.execute(c);
    require(stats.lane[0] == length, "N length count");
    c.op = NCommand::Op::FinishExp;
    require(n.execute(c).error, "N rejects incomplete exp phase");
    uint64_t sum = 0;
    for (unsigned start = 0; start < length; start += 8) {
        c.op = NCommand::Op::Exp;
        c.count = std::min(8U, length - start);
        for (unsigned i = 0; i < c.count; ++i)
            c.data[i] = uint16_t(x[start + i]);
        auto r = n.execute(c);
        ok(r);
        for (unsigned i = 0; i < c.count; ++i) {
            exp[start + i] = uint16_t(r.lane[i]);
            sum += r.lane[i];
        }
    }
    c.op = NCommand::Op::FinishExp;
    ok(n.execute(c));
    double denominator = 0, max = *std::max_element(x.begin(), x.end());
    for (auto v : x)
        denominator += std::exp((v - max) / 1024.0);
    for (unsigned start = 0; start < length; start += 8) {
        c.op = NCommand::Op::SoftReplay;
        c.count = std::min(8U, length - start);
        for (unsigned i = 0; i < c.count; ++i)
            c.data[i] = exp[start + i];
        auto r = n.execute(c);
        ok(r);
        for (unsigned i = 0; i < c.count; ++i) {
            int64_t expected =
                reference_round(int64_t(exp[start + i]) * ((uint64_t(1) << 44) / sum), 30);
            require(r.lane[i] == expected && r.lane[i] >= 0 && r.lane[i] <= 16384,
                    "Softmax signed Q1.14 integer contract");
            double exact = std::exp((x[start + i] - max) / 1024.0) / denominator;
            require(std::abs(r.lane[i] / 16384.0 - exact) < 3.5e-5, "Softmax real-valued error");
        }
    }
    require(n.execute(c).error, "N replay overrun rejected");
    c.op = NCommand::Op::ReadStats;
    auto end = n.execute(c);
    require(end.lane[5] == length && end.lane[6] == int64_t(sum) && end.lane[7] == length,
            "N final counters");
}
static void test_m_segments() {
    MEngine m;
    std::array<std::array<int16_t, 32>, 8> a{}, b{};
    std::array<std::array<int64_t, 8>, 8> expected{};
    for (unsigned segment = 0; segment < 8; ++segment) {
        for (unsigned row = 0; row < 8; ++row)
            for (unsigned k = 0; k < 32; ++k)
                a[row][k] = int16_t((int(segment * 32 + k) * 13 + int(row) * 7) % 201 - 100);
        for (unsigned col = 0; col < 8; ++col)
            for (unsigned k = 0; k < 32; ++k)
                b[col][k] = int16_t((int(segment * 32 + k) * 5 + int(col) * 3) % 127 - 63);
        load_m(m, a, b, false, false);
        MCommand c;
        c.op = MCommand::Op::Scale;
        c.coefficient = 37;
        c.shift = 3;
        ok(m.execute(c));
        c.op = MCommand::Op::Execute;
        c.rows = 8;
        c.tiles = 4;
        c.clear = segment == 0;
        ok(m.execute(c));
        for (unsigned row = 0; row < 8; ++row)
            for (unsigned col = 0; col < 8; ++col)
                for (unsigned k = 0; k < 32; ++k)
                    expected[row][col] += int64_t(a[row][k]) * b[col][k] * 296;
    }
    for (unsigned row = 0; row < 8; ++row)
        for (unsigned pair = 0; pair < 4; ++pair) {
            MCommand c;
            c.op = MCommand::Op::ReadFull;
            c.row = row;
            c.pair = pair;
            auto r = m.execute(c);
            ok(r);
            require(r.lane[0] == expected[row][pair * 2] &&
                        r.lane[1] == expected[row][pair * 2 + 1],
                    "M K256 eight segments distributes exact scaling");
        }
}
static void test_n() {
    softmax_case(1);
    softmax_case(8);
    softmax_case(257);
    softmax_case(65535);
    for (auto mode : {NCommand::Mode::RMS, NCommand::Mode::L2})
        for (unsigned len : {1U, 7U, 257U}) {
            NEngine n;
            NCommand c;
            c.mode = mode;
            c.epsilon = 1;
            c.op = NCommand::Op::Begin;
            ok(n.execute(c));
            uint64_t sumsq = 0;
            for (unsigned start = 0; start < len; start += 8) {
                c.op = NCommand::Op::Stats;
                c.count = std::min(8U, len - start);
                for (unsigned i = 0; i < c.count; ++i) {
                    int x = (int(start + i) % 9 - 4) * 1024;
                    c.data[i] = uint16_t(x);
                    sumsq += int64_t(x) * x;
                }
                ok(n.execute(c));
            }
            c.op = NCommand::Op::Finalize;
            ok(n.execute(c));
            uint64_t d = sumsq * 65536ULL;
            if (mode == NCommand::Mode::RMS)
                d /= len;
            d += 65536;
            uint64_t root = uint64_t(std::sqrt((long double)d));
            while (Wide(root) * root > d)
                --root;
            while (Wide(root + 1) * (root + 1) <= d)
                ++root;
            c.op = NCommand::Op::ReadFactor;
            require(n.execute(c).lane[0] == int64_t((uint64_t(1) << 38) / root),
                    "norm exact factor");
            for (unsigned start = 0; start < len; start += 8) {
                c.op = NCommand::Op::NormReplay;
                c.count = std::min(8U, len - start);
                c.gamma.fill(1024);
                for (unsigned i = 0; i < c.count; ++i)
                    c.data[i] = uint16_t((int(start + i) % 9 - 4) * 1024);
                auto r = n.execute(c);
                ok(r);
                for (unsigned i = 0; i < c.count; ++i) {
                    double real =
                        (int(start + i) % 9 - 4) * 1024.0 /
                        std::sqrt(double(sumsq) / (mode == NCommand::Mode::RMS ? len : 1) + 1) *
                        1024;
                    require(std::abs(r.lane[i] - real) < 1.1, "norm real-valued scale");
                }
            }
        }
    NEngine n;
    NCommand c;
    c.op = NCommand::Op::Begin;
    c.mode = NCommand::Mode::RMS;
    c.epsilon = 0;
    require(n.execute(c).error, "N zero epsilon");
    c.op = NCommand::Op::TopBegin;
    c.k = 8;
    ok(n.execute(c));
    for (unsigned j = 0; j < 10; ++j) {
        c.op = NCommand::Op::TopLoad;
        c.count = 4;
        for (unsigned i = 0; i < 4; ++i) {
            c.data[i] = 10;
            c.ids[i] = uint16_t(39 - j * 4 - i);
        }
        ok(n.execute(c));
    }
    require(n.execute(c).error, "TopK finite capacity");
    c.op = NCommand::Op::TopSelect;
    auto top = n.execute(c);
    ok(top);
    for (unsigned i = 0; i < 8; ++i)
        require(top.lane[i] == i, "TopK equal scores prefer smaller IDs");
    require(n.execute(c).error, "TopK closes loading");
}
static void setup_r(REngine &r, RCommand &c) {
    c.op = RCommand::Op::Open;
    c.length = 2;
    c.owner = 7;
    c.epoch = 11;
    c.position = 19;
    ok(r.execute(c));
    for (unsigned row = 0; row < 2; ++row) {
        c.op = RCommand::Op::StateRow;
        c.index = row;
        c.values.fill(int32_t((row + 1) * 10));
        ok(r.execute(c));
        c.op = RCommand::Op::Key;
        c.coefficients[0] = row == 0 ? 16384 : 0;
        ok(r.execute(c));
        c.op = RCommand::Op::Query;
        c.coefficients[0] = 8192;
        ok(r.execute(c));
    }
    c.op = RCommand::Op::Parameters;
    c.decay = 0x40000000U;
    c.beta = 0x80000000U;
    ok(r.execute(c));
    c.op = RCommand::Op::X;
    c.values.fill(9);
    ok(r.execute(c));
}
static void test_r() {
    REngine r;
    RCommand c;
    setup_r(r, c);
    c.op = RCommand::Op::Execute;
    c.owner = 8;
    require(r.execute(c).error, "R owner mismatch");
    c.owner = 7;
    ok(r.execute(c));
    c.op = RCommand::Op::ReadOutput;
    require(r.execute(c).lane[0] == 10, "GDN readout after update");
    c.op = RCommand::Op::ReadState;
    c.index = 0;
    require(r.execute(c).lane[0] == 10, "GDN candidate invisible before commit");
    c.op = RCommand::Op::Commit;
    c.epoch = 10;
    require(r.execute(c).error, "R stale epoch");
    c.epoch = 11;
    c.next_position = 20;
    ok(r.execute(c));
    c.op = RCommand::Op::ReadState;
    require(r.execute(c).lane[0] == 9, "R atomic bank swap");
    c.op = RCommand::Op::Status;
    auto status = r.execute(c);
    require(status.lane[2] == 12 && status.lane[3] == 20, "R commit advances tags");
    REngine s;
    RCommand d;
    setup_r(s, d);
    for (unsigned row = 0; row < 2; ++row) {
        d.op = RCommand::Op::DecayRow;
        d.index = row;
        d.factors.fill(0x40000000U);
        ok(s.execute(d));
        d.op = RCommand::Op::Key;
        d.coefficients[0] = 16384;
        ok(s.execute(d));
    }
    d.op = RCommand::Op::X;
    d.values.fill(4);
    ok(s.execute(d));
    d.op = RCommand::Op::Inject;
    d.values.fill(3);
    ok(s.execute(d));
    d.op = RCommand::Op::Skip;
    d.values.fill(32768);
    ok(s.execute(d));
    d.op = RCommand::Op::Execute;
    d.mode = RCommand::Mode::SSM;
    ok(s.execute(d));
    d.op = RCommand::Op::ReadOutput;
    require(s.execute(d).lane[0] == 12, "SSM decay injection readout skip");
    d.op = RCommand::Op::Revoke;
    ok(s.execute(d));
    d.op = RCommand::Op::ReadState;
    d.index = 0;
    require(s.execute(d).lane[0] == 10, "R revoke retains active");
    d.op = RCommand::Op::Execute;
    require(s.execute(d).error, "SSM consumes decay bank factors");
    REngine q;
    RCommand a;
    setup_r(q, a);
    for (unsigned t = 0; t < 3; ++t) {
        a.op = RCommand::Op::History;
        a.index = t;
        a.values.fill(int32_t(t + 2));
        ok(q.execute(a));
    }
    for (unsigned t = 0; t < 4; ++t) {
        a.op = RCommand::Op::Taps;
        a.index = t;
        a.coefficients.fill(16384);
        ok(q.execute(a));
    }
    a.op = RCommand::Op::X;
    a.values.fill(1);
    ok(q.execute(a));
    a.op = RCommand::Op::Execute;
    a.mode = RCommand::Mode::Conv4;
    ok(q.execute(a));
    a.op = RCommand::Op::ReadOutput;
    require(q.execute(a).lane[0] == 10, "four tap causal convolution");
    a.op = RCommand::Op::Parameters;
    a.decay = 0x80000000U;
    a.beta = 0x80000000U;
    ok(q.execute(a));
    a.op = RCommand::Op::X;
    a.values.fill(std::numeric_limits<int32_t>::min());
    ok(q.execute(a));
    a.op = RCommand::Op::Execute;
    a.mode = RCommand::Mode::GDN;
    require(q.execute(a).error, "R rejects overflow without saturation");
    a.op = RCommand::Op::Status;
    status = q.execute(a);
    require(status.lane[4] == 0 && status.lane[5] == 1,
            "failed state does not revoke pending convolution");
    a.op = RCommand::Op::Commit;
    a.next_position = 20;
    ok(q.execute(a));
    a.op = RCommand::Op::ReadHistory;
    a.index = 0;
    require(q.execute(a).lane[0] == 1, "convolution history commits");
    a.op = RCommand::Op::ReadState;
    require(q.execute(a).lane[0] == 10, "failed state preserved original bank");
}
static void test_s_t() {
    SEngine s;
    SCommand c;
    c.op = SCommand::Op::Read;
    require(s.execute(c).error, "uninitialized S read diagnostic");
    c.op = SCommand::Op::Write;
    c.address = 1024;
    require(s.execute(c).error, "S bounded capacity");
    for (unsigned i = 0; i < 1024; ++i) {
        c.address = i;
        c.data = {{i, ~uint64_t(i)}};
        auto r = s.execute(c);
        ok(r);
        require(r.bits[0] == i, "S write acknowledgement echoes data");
    }
    c.op = SCommand::Op::ReadWide;
    c.address = 255;
    auto line = s.execute(c);
    ok(line);
    require(line.bits[0] == 1020 && line.bits[6] == 1023, "S bank interleave mapping");
    c.op = SCommand::Op::Reset;
    ok(s.execute(c));
    c.op = SCommand::Op::Read;
    c.address = 5;
    require(s.execute(c).bits[0] == 5, "S reset preserves memory");
    c.op = SCommand::Op::LoadBegin;
    c.rows = 5;
    c.tiles = 2;
    c.wide_a = true;
    c.wide_b = true;
    c.a_base = 0;
    c.b_base = 32;
    ok(s.execute(c));
    unsigned ab = 0, bb = 0;
    while (true) {
        c.op = SCommand::Op::LoadNext;
        auto r = s.execute(c);
        ok(r);
        if (r.lane[0] == 0) {
            require(r.bits[0] == uint64_t(r.lane[3] * 8 + r.lane[2]), "S A descriptor order");
            ++ab;
        } else {
            require(r.bits[0] == uint64_t(32 + r.lane[3] * 8 + r.lane[2] * 4), "S B half ordering");
            ++bb;
        }
        if (r.last)
            break;
    }
    require(ab == 10 && bb == 4, "S bounded loader emits exact beat counts");
    require(s.execute(c).error, "S finished loader rejects next");
    TEngine t;
    TCommand d;
    d.op = TCommand::Op::Begin;
    require(t.execute(d).error, "T zero length");
    d.words = 384;
    d.owner = 2;
    d.generation = 123;
    ok(t.execute(d));
    d.op = TCommand::Op::Commit;
    require(t.execute(d).error, "T incomplete cannot commit");
    d.op = TCommand::Op::Write;
    d.index = 1;
    require(t.execute(d).error, "T nonsequential write");
    for (unsigned i = 0; i < 384; ++i) {
        d.index = i;
        d.data = {{i, i + 1000}};
        ok(t.execute(d));
    }
    d.op = TCommand::Op::Commit;
    ok(t.execute(d));
    d.op = TCommand::Op::Revoke;
    require(t.execute(d).error, "T committed cannot revoke");
    for (unsigned i = 0; i < 384; ++i) {
        d.op = TCommand::Op::Peek;
        auto r = t.execute(d);
        require(r.bits[0] == i && r.index == i && r.last == (i == 383), "T held output and last");
        auto again = t.execute(d);
        require(again.bits == r.bits, "T stalled output stable");
        d.op = TCommand::Op::Take;
        ok(t.execute(d));
    }
    d.op = TCommand::Op::Begin;
    require(t.execute(d).error, "T lease requires release");
    d.op = TCommand::Op::Release;
    ok(t.execute(d));
    d.op = TCommand::Op::Status;
    require(t.execute(d).lane[5] == 1, "T protocol error sticky");
    d.op = TCommand::Op::Reset;
    ok(t.execute(d));
    d.op = TCommand::Op::Peek;
    require(t.execute(d).error, "T reset prevents stale payload exposure");
}
static void test_limits() {
    REngine r;
    RCommand c;
    c.op = RCommand::Op::Open;
    c.length = 256;
    c.epoch = 0xffffffffU;
    ok(r.execute(c));
    for (unsigned row = 0; row < 256; ++row) {
        c.op = RCommand::Op::StateRow;
        c.index = row;
        c.values.fill(0);
        ok(r.execute(c));
        c.op = RCommand::Op::Key;
        c.coefficients[0] = 0;
        ok(r.execute(c));
        c.op = RCommand::Op::Query;
        ok(r.execute(c));
    }
    c.op = RCommand::Op::StateRow;
    c.index = 256;
    require(r.execute(c).error, "R state capacity boundary");
    c.op = RCommand::Op::Parameters;
    ok(r.execute(c));
    c.op = RCommand::Op::X;
    ok(r.execute(c));
    c.op = RCommand::Op::Execute;
    ok(r.execute(c));
    c.op = RCommand::Op::Commit;
    require(r.execute(c).error, "R epoch overflow cannot commit");
    c.op = RCommand::Op::Revoke;
    ok(r.execute(c));
    NEngine n;
    NCommand q;
    q.op = NCommand::Op::Begin;
    ok(n.execute(q));
    q.op = NCommand::Op::Stats;
    q.data.fill(32768);
    for (unsigned i = 0; i < 8191; ++i)
        ok(n.execute(q));
    q.count = 7;
    ok(n.execute(q));
    require(n.execute(q).error, "N statistics count capacity");
    q.op = NCommand::Op::ReadStats;
    auto stats = n.execute(q);
    require(stats.lane[0] == 65535 && stats.lane[3] == -2147450880LL &&
                stats.lane[4] == 70367670435840LL,
            "N extreme signed sum and sumsq exact widths");
    q.op = NCommand::Op::Begin;
    ok(n.execute(q));
    q.op = NCommand::Op::Stats;
    q.count = 1;
    q.data[0] = 0;
    ok(n.execute(q));
    q.op = NCommand::Op::Finalize;
    ok(n.execute(q));
    q.op = NCommand::Op::Exp;
    ok(n.execute(q));
    q.op = NCommand::Op::FinishExp;
    ok(n.execute(q));
    q.op = NCommand::Op::SoftReplay;
    q.data[0] = 65535;
    require(n.execute(q).error, "N invalid unsigned exponential replay encoding");
    q.data[0] = 32768;
    require(n.execute(q).lane[0] == 16384, "N rejected replay did not advance count");
    MEngine m;
    std::array<std::array<int16_t, 32>, 8> a{}, b{};
    for (auto &row : a)
        row.fill(-128);
    for (auto &row : b)
        row.fill(127);
    load_m(m, a, b, false, false, 1, 1);
    MCommand z;
    z.op = MCommand::Op::Execute;
    ok(m.execute(z));
    z.op = MCommand::Op::ReadFinal;
    z.width = 8;
    auto small = m.execute(z);
    require(small.saturated && small.lane[0] == -128, "M final signed-eight saturation");
    z.width = 16;
    z.shift = 11;
    require(m.execute(z).lane[0] == -64, "M final negative RNE");
}
// All seven modules run on the real SystemC kernel. Every channel depth is one.
struct Harness : sc_core::sc_module {
    M m{"M"};
    N n{"N"};
    E e{"E"};
    G g{"G"};
    R r{"R"};
    S s{"S"};
    T t{"T"};
    sc_core::sc_fifo<MCommand> mi{"mi", 1};
    sc_core::sc_fifo<NCommand> ni{"ni", 1};
    sc_core::sc_fifo<ECommand> ei{"ei", 1};
    sc_core::sc_fifo<GCommand> gi{"gi", 1};
    sc_core::sc_fifo<RCommand> ri{"ri", 1};
    sc_core::sc_fifo<SCommand> si{"si", 1};
    sc_core::sc_fifo<TCommand> ti{"ti", 1};
    sc_core::sc_fifo<Reply> mo{"mo", 1}, no{"no", 1}, eo{"eo", 1}, go{"go", 1}, ro{"ro", 1},
        so{"so", 1}, to{"to", 1};
    sc_core::sc_event start_pressure;
    unsigned sent = 0;
    bool pressure = false, done = false;
    SC_HAS_PROCESS(Harness);
    Harness(sc_core::sc_module_name name) : sc_core::sc_module(name) {
        m.commands(mi);
        m.responses(mo);
        n.commands(ni);
        n.responses(no);
        e.commands(ei);
        e.responses(eo);
        g.commands(gi);
        g.responses(go);
        r.commands(ri);
        r.responses(ro);
        s.commands(si);
        s.responses(so);
        t.commands(ti);
        t.responses(to);
        SC_THREAD(run);
        SC_THREAD(producer);
        SC_THREAD(watchdog);
    }
    template <class C> Reply call(sc_core::sc_fifo<C> &in, sc_core::sc_fifo<Reply> &out, C c) {
        c.tag = ++checks;
        in.write(c);
        auto v = out.read();
        require(v.tag == c.tag, "SystemC response tag/order");
        ok(v);
        return v;
    }
    void producer() {
        wait(start_pressure);
        for (unsigned i = 0; i < 12; ++i) {
            ECommand c;
            c.tag = 1000 + i;
            c.a.fill(int16_t(i));
            c.b.fill(2);
            ei.write(c);
            ++sent;
        }
        pressure = true;
    }
    void watchdog() {
        wait(1, sc_core::SC_US);
        require(done, "SystemC deadlock watchdog");
        sc_core::sc_stop();
    }
    void run() {
        // S -> M uses a real descriptor and typed port beats, not direct memory access.
        SCommand sc;
        sc.op = SCommand::Op::Write;
        for (unsigned i = 0; i < 8; ++i) {
            sc.address = i;
            Line w{};
            for (unsigned j = 0; j < 16; ++j)
                put8(w, j, i < 4 ? 1 : 2);
            sc.data = {{w[0], w[1]}};
            call(si, so, sc);
        }
        sc.op = SCommand::Op::LoadBegin;
        sc.rows = 1;
        sc.tiles = 1;
        sc.b_base = 4;
        call(si, so, sc);
        while (true) {
            sc.op = SCommand::Op::LoadNext;
            auto beat = call(si, so, sc);
            MCommand mc;
            mc.data = beat.bits;
            mc.tile = unsigned(beat.lane[3]);
            mc.bank = unsigned(beat.lane[1]);
            if (beat.lane[0] == 0) {
                mc.op = MCommand::Op::LoadA;
                mc.row = unsigned(beat.lane[2]);
            } else {
                mc.op = MCommand::Op::LoadB;
                mc.half = unsigned(beat.lane[2]);
            }
            call(mi, mo, mc);
            if (beat.last)
                break;
        }
        MCommand mc;
        mc.op = MCommand::Op::Execute;
        call(mi, mo, mc);
        mc.op = MCommand::Op::ReadFull;
        auto mr = call(mi, mo, mc);
        require(mr.lane[0] == 16, "SystemC S to M dot product");
        ECommand ec;
        ec.op = ECommand::Op::Add;
        ec.a.fill(int16_t(mr.lane[0]));
        ec.b.fill(1008);
        auto er = call(ei, eo, ec);
        GCommand gc;
        gc.function = GCommand::Function::Sigmoid;
        gc.x.fill(int16_t(er.lane[0]));
        auto gr = call(gi, go, gc);
        NCommand nc;
        nc.op = NCommand::Op::Begin;
        call(ni, no, nc);
        nc.op = NCommand::Op::Stats;
        nc.count = 2;
        nc.data = {{uint16_t(gr.lane[0]), uint16_t(gr.lane[1])}};
        call(ni, no, nc);
        nc.op = NCommand::Op::Finalize;
        call(ni, no, nc);
        nc.op = NCommand::Op::Exp;
        auto ex = call(ni, no, nc);
        nc.op = NCommand::Op::FinishExp;
        call(ni, no, nc);
        nc.op = NCommand::Op::SoftReplay;
        nc.data[0] = uint16_t(ex.lane[0]);
        nc.data[1] = uint16_t(ex.lane[1]);
        auto nr = call(ni, no, nc);
        require(nr.lane[0] == 8192 && nr.lane[1] == 8192, "SystemC two-value Softmax");
        TCommand tc;
        tc.op = TCommand::Op::Begin;
        tc.words = 1;
        call(ti, to, tc);
        tc.op = TCommand::Op::Write;
        tc.data = {{uint64_t(nr.lane[0]), uint64_t(nr.lane[1])}};
        call(ti, to, tc);
        tc.op = TCommand::Op::Commit;
        call(ti, to, tc);
        tc.op = TCommand::Op::Take;
        require(call(ti, to, tc).bits[0] == 8192, "SystemC N to T retains result");
        tc.op = TCommand::Op::Release;
        call(ti, to, tc);
        RCommand rc;
        rc.op = RCommand::Op::Open;
        call(ri, ro, rc);
        rc.op = RCommand::Op::Status;
        require(call(ri, ro, rc).lane[0] == 1, "R instantiated and scheduled");
        start_pressure.notify(sc_core::SC_ZERO_TIME);
        wait(10, sc_core::SC_NS);
        require(sent == 3 && !pressure && eo.num_available() == 1 && ei.num_available() == 1,
                "finite command/response queues block producer at three packets");
        for (unsigned i = 0; i < 12; ++i) {
            auto v = eo.read();
            require(v.tag == 1000 + i && v.lane[0] == int64_t(i + 2),
                    "backpressure no loss duplication reordering");
            wait(1, sc_core::SC_NS);
        }
        require(sent == 12 && pressure, "backpressure resumes producer");
        done = true;
        sc_core::sc_stop();
    }
};
int sc_main(int, char **) {
    try {
        test_arithmetic();
        test_e();
        test_g();
        test_m();
        test_m_segments();
        test_n();
        test_r();
        test_s_t();
        test_limits();
        Harness top{"seven_blocks"};
        sc_core::sc_start();
        require(top.done, "SystemC completed");
        std::cout
            << "PASS " << checks
            << " assertions; seven engines, seven scheduled modules, finite FIFO backpressure\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL after " << checks << ": " << e.what() << '\n';
        return 1;
    }
}
