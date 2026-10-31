/**
 * G：两lane激活函数与可选紧邻门乘的无时钟模型。
 * x(Q5.10) -> 区间判断 -> 两表项线性插值/RNE -> 可选gate(Q5.10) -> S16饱和。
 * SiLU/GELU_tanh/Softplus的函数结果为Q5.10，Sigmoid的函数结果为Q1.14。
 * 启用gate后四种函数都输出Q5.10；表整数与RTL同源，但不代表已经做RTL等价证明。
 * RTL四级流水及II=1未在本文件逐拍展开。
 */
#pragma once
#include "common.hpp"
#include "tables.hpp"
namespace blocks {
struct GCommand : Printable {
    // Function枚举顺序对应激活表0..3；Reset是事务接口扩展，不读取系数表。
    // SiLU=x*sigmoid(x)；GELU为tanh近似；Softplus=ln(1+exp(x))。
    enum class Function { SiLU, Sigmoid, GELU, Softplus, Reset };
    // gated=false只输出函数值；true则以完整函数近似结果乘gate，再对乘积RNE。
    Function function = Function::SiLU;
    bool gated = false;
    // 两路S16原始编码，x和gate的1024都表示1.0；gate仅在gated=true时读取。
    std::array<int16_t, 2> x{}, gate{};
};
class GEngine {
  public:
    using Command = GCommand;
    using Response = Reply;
    // 每条命令独立，无整向量缓存；返回两lane结果，域外近似本身不置saturated。
    // 只有最终数值超出S16而夹取时才置saturated；非法函数返回error。
    Response execute(const Command &c) {
        auto r = reply(c);
        if (c.function == Command::Function::Reset)
            return r;
        unsigned f = unsigned(c.function);
        if (f > 3)
            return reply(c, true);
        r.count = 2;
        for (unsigned i = 0; i < 2; ++i) {
            // 前三函数表域[-8,8]，Softplus表域[-16,16]；bound为Q5.10编码的边界值。
            int x = c.x[i], bound = f == 3 ? 16384 : 8192;
            Wide v;
            // 域外使用已声明近似：左侧全取0，右侧Sigmoid取1、其余函数取identity(x)。
            // 恰在边界仍查表，不能把域外策略误当成所有真实数学函数的精确值。
            if (x < -bound)
                v = 0;
            else if (x > bound)
                v = f == 1 ? 16384 : x;
            else {
                // 网格1/32对应原始编码32：j=下表项，frac=区间内偏移0..31。
                // 右端点j到最后有效表项时hi固定在末项；此时frac=0，不访问填充区域。
                unsigned offset = unsigned(x + bound), j = offset / 32, frac = offset % 32;
                int lo = table::activation[f][j],
                    hi = table::activation[f][std::min(j + 1, unsigned(f == 3 ? 1024 : 512))];
                v = lo + rne(Wide(hi - lo) * frac, 5);
            }
            // Sigmoid输出原为Q1.14，乘Q5.10门值后右移14；其他函数右移10，均落回Q5.10。
            if (c.gated)
                v = rne(v * c.gate[i], f == 1 ? 14 : 10);
            r.lane[i] = clamp(v, 16, r.saturated);
        }
        return r;
    }
};
} // namespace blocks
