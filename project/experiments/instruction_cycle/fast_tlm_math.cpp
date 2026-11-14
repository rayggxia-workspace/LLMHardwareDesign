// Exact integer arithmetic for the archived native TLM providers.
#include <cstdint>
#include <limits>

namespace {

using Wide = __int128;
using Bits = unsigned __int128;

uint32_t little32(const uint8_t* bytes) noexcept {
    return uint32_t{bytes[0]} | uint32_t{bytes[1]} << 8 | uint32_t{bytes[2]} << 16 |
           uint32_t{bytes[3]} << 24;
}

int64_t signed32(const uint8_t* bytes) noexcept {
    const uint32_t raw = little32(bytes);
    return static_cast<int64_t>(raw) - (raw >> 31) * (int64_t{1} << 32);
}

template <typename Integer>
Integer rne(Integer value, int shift) noexcept {
    if (shift <= 0) {
        return value * (Integer{1} << -shift);
    }
    const Integer denominator = Integer{1} << shift;
    Integer quotient = value / denominator;
    Integer remainder = value % denominator;
    if (remainder < 0) {
        --quotient;
        remainder += denominator;
    }
    return quotient + (2 * remainder > denominator ||
                       (2 * remainder == denominator && quotient % 2 != 0));
}

constexpr auto s32_min = std::numeric_limits<int32_t>::min();
constexpr auto s32_max = std::numeric_limits<int32_t>::max();

int32_t clamp32(Wide value) noexcept {
    if (value < s32_min) return s32_min;
    if (value > s32_max) return s32_max;
    return static_cast<int32_t>(value);
}

}  // namespace

extern "C" int fast_tlm_projection(const uint8_t* weights, const int16_t* activation,
                                   int shift, int head16, int32_t* prefix) noexcept {
    if (shift < 0 || shift > 17) return 0;
    const unsigned steps = head16 ? 8 : 1;
    if (!head16) {
        for (unsigned i = 1040; i < 1088; ++i) {
            if (weights[i]) return 0;
        }
    }
    for (unsigned step = 0; step < steps; ++step) {
        int32_t totals[8]{};
        const unsigned begin = head16 ? step : 0;
        const unsigned end = head16 ? step + 1 : 8;
        for (unsigned chunk = begin; chunk < end; ++chunk) {
            for (unsigned lane = 0; lane < 8; ++lane) {
                const auto* packed = weights + chunk * 128 + lane * 16;
                // W8 × A16 × 128 fits signed 32 bits for every lane.
                for (unsigned i = 0; i < 16; ++i) {
                    const int weight = packed[i] - (packed[i] >> 7) * 256;
                    totals[lane] += weight * activation[chunk * 16 + i];
                }
            }
        }
        for (unsigned lane = 0; lane < 8; ++lane) {
            const unsigned scale = 1024 + 2 * (step * 8 + lane);
            const unsigned bits = weights[scale] | unsigned{weights[scale + 1]} << 8;
            if (bits == 0 || bits >= 0x7c00) return 0;
            const int exponent = bits >> 10;
            const int64_t significand = (bits & 1023) + (exponent ? 1024 : 0);
            const int64_t scaled = rne(totals[lane] * significand,
                                       25 - (exponent ? exponent : 1) - shift);
            const int64_t next = prefix[lane] + scaled;
            if (scaled < s32_min || scaled > s32_max || next < s32_min || next > s32_max) return 0;
            prefix[lane] = static_cast<int32_t>(next);
        }
    }
    return 1;
}

extern "C" void fast_tlm_qk(const uint8_t* query, const uint8_t* keys,
                            unsigned rows, int32_t* results) noexcept {
    int64_t q[128];
    for (unsigned i = 0; i < 128; ++i) {
        q[i] = signed32(query + 4 * i);
    }
    for (unsigned row = 0; row < rows; ++row) {
        Wide total = 0;
        for (unsigned i = 0; i < 128; ++i) {
            // One signed S32 product fits int64. The full dot can exceed it.
            total += q[i] * signed32(keys + 512 * row + 4 * i);
        }
        results[row] = clamp32(rne(total, 16));
    }
}

extern "C" void fast_tlm_av(const uint8_t* probabilities, const uint8_t* values,
                            unsigned rows, uint64_t* low, int64_t* high) noexcept {
    Wide totals[8]{};
    for (unsigned row = 0; row < rows; ++row) {
        const int64_t probability = signed32(probabilities + 4 * row);
        for (unsigned lane = 0; lane < 8; ++lane) {
            totals[lane] += probability * signed32(values + 32 * row + 4 * lane);
        }
    }
    for (unsigned lane = 0; lane < 8; ++lane) {
        const Bits raw = static_cast<Bits>(totals[lane]);
        low[lane] = static_cast<uint64_t>(raw);
        // The caller adds this fragment to its unbounded Python accumulator.
        high[lane] = static_cast<int64_t>(totals[lane] >> 64);
    }
}
