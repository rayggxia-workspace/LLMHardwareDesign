#pragma once
#include "common.hpp"
#include "tables.hpp"
namespace blocks {
struct GCommand : Printable {
    enum class Function { SiLU, Sigmoid, GELU, Softplus, Reset };
    Function function = Function::SiLU;
    bool gated = false;
    std::array<int16_t, 2> x{}, gate{};
};
class GEngine {
  public:
    using Command = GCommand;
    using Response = Reply;
    Response execute(const Command &c) {
        auto r = reply(c);
        if (c.function == Command::Function::Reset)
            return r;
        unsigned f = unsigned(c.function);
        if (f > 3)
            return reply(c, true);
        r.count = 2;
        for (unsigned i = 0; i < 2; ++i) {
            int x = c.x[i], bound = f == 3 ? 16384 : 8192;
            Wide v;
            if (x < -bound)
                v = 0;
            else if (x > bound)
                v = f == 1 ? 16384 : x;
            else {
                unsigned offset = unsigned(x + bound), j = offset / 32, frac = offset % 32;
                int lo = table::activation[f][j],
                    hi = table::activation[f][std::min(j + 1, unsigned(f == 3 ? 1024 : 512))];
                v = lo + rne(Wide(hi - lo) * frac, 5);
            }
            if (c.gated)
                v = rne(v * c.gate[i], f == 1 ? 14 : 10);
            r.lane[i] = clamp(v, 16, r.saturated);
        }
        return r;
    }
};
} // namespace blocks
