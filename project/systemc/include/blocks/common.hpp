#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <ostream>
namespace blocks {
// Host-wide temporaries are arithmetic checks, not additional physical storage.
using Wide = __int128_t;
using Word = std::array<uint64_t, 2>; // 128 bits, least significant limb first
using Line = std::array<uint64_t, 8>; // 512 bits
struct Printable {
    uint64_t tag = 0;
};
inline std::ostream &operator<<(std::ostream &os, const Printable &p) {
    return os << "txn#" << p.tag;
}
struct Reply : Printable {
    bool error = false, saturated = false, last = false;
    uint8_t failed_rows = 0;
    unsigned count = 0, index = 0;
    std::array<int64_t, 8> lane{};
    Line bits{};
};
inline Wide power(unsigned s) { return Wide(1) << s; }
// Floor-quotient RNE works for negatives too; no signed-negative left shifts.
inline Wide rne(Wide x, unsigned s) {
    if (!s)
        return x;
    const Wide d = power(s);
    Wide q = x / d, r = x % d;
    if (r < 0) {
        --q;
        r += d;
    }
    return q + (r > d / 2 || (r == d / 2 && q % 2 != 0));
}
inline Wide floor_shift(Wide x, unsigned s) {
    const Wide d = power(s);
    return x / d - (x % d < 0);
}
inline bool fits(Wide x, unsigned width) { return x >= -power(width - 1) && x < power(width - 1); }
inline int64_t clamp(Wide x, unsigned width, bool &saturated) {
    const Wide lo = -power(width - 1), hi = power(width - 1) - 1;
    if (x < lo) {
        x = lo;
        saturated = true;
    }
    if (x > hi) {
        x = hi;
        saturated = true;
    }
    return int64_t(x);
}
inline int32_t wrap32(Wide x) {
    const uint32_t u = uint32_t(x);
    return u <= 0x7fffffffU ? int32_t(u) : int32_t(int64_t(u) - 0x100000000LL);
}
inline uint64_t isqrt(uint64_t x) {
    uint64_t root = 0, bit = uint64_t(1) << 62;
    while (bit > x)
        bit >>= 2;
    while (bit) {
        if (x >= root + bit) {
            x -= root + bit;
            root = (root >> 1) + bit;
        } else
            root >>= 1;
        bit >>= 2;
    }
    return root;
}
inline int16_t signed16(uint16_t u) { return u < 32768 ? int16_t(u) : int16_t(int32_t(u) - 65536); }
inline uint16_t halfword(const Line &w, unsigned i) { return uint16_t(w[i / 4] >> (16 * (i % 4))); }
inline uint8_t byte(const Line &w, unsigned i) { return uint8_t(w[i / 8] >> (8 * (i % 8))); }
inline Reply reply(const Printable &c, bool error = false) {
    Reply r;
    r.tag = c.tag;
    r.error = error;
    return r;
}
} // namespace blocks
