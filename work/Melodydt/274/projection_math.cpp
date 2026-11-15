#include <cstdint>
#include <limits>

static int64_t round_to_even(int64_t value, int shift) {
    if (shift <= 0) {
        return value * (int64_t{1} << -shift);
    }
    const int64_t divisor = int64_t{1} << shift;
    int64_t quotient = value / divisor;
    int64_t remainder = value % divisor;
    if (remainder < 0) {
        --quotient;
        remainder += divisor;
    }
    return quotient + (remainder*2 > divisor || (remainder*2 == divisor && quotient % 2 != 0));
}

static bool fits_s32(int64_t value) {
    return value >= std::numeric_limits<int32_t>::min() &&
           value <= std::numeric_limits<int32_t>::max();
}

extern "C" int accumulate_projection(const uint8_t* weights, const int16_t* activation,
                                     int shift, int32_t* prefix, bool head16) {
    if (!head16) {
        for (int i = 1040; i < 1088; ++i) {
            if (weights[i]) {
                return 1;
            }
        }
    }
    const int steps = head16 ? 8 : 1;
    for (int step = 0; step < steps; ++step) {
        for (int lane = 0; lane < 8; ++lane) {
            int64_t total = 0;
            const int chunk_start = head16 ? step : 0;
            const int chunk_end = head16 ? step+1 : 8;
            for (int chunk = chunk_start; chunk < chunk_end; ++chunk) {
                const int start = 128*chunk+16*lane;
                for (int col = 0; col < 16; ++col) {
                    const auto byte = weights[start+col];
                    const int coefficient = byte < 128 ? byte : byte-256;
                    total += coefficient*activation[16*chunk+col];
                }
            }
            const int offset = 1024+16*step+2*lane;
            const int bits = weights[offset] | (weights[offset+1] << 8);
            if (bits <= 0 || bits >= 0x7c00) {
                return 2;
            }
            const int exponent = bits >> 10;
            const int mantissa = (bits & 1023)+(exponent ? 1024 : 0);
            const int64_t scaled = round_to_even(total*mantissa, 25-(exponent ? exponent : 1)-shift);
            const int64_t next = prefix[lane]+scaled;
            if (!fits_s32(scaled) || !fits_s32(next)) {
                return 3;
            }
            prefix[lane] = static_cast<int32_t>(next);
        }
    }
    return 0;
}
