/**
 * E：八lane S16基础逐元素运算与局部配对RoPE，无跨命令长向量状态。
 * 一次命令 -> 八lane完整中间值 -> 可选RNE -> S16饱和或S8紧凑打包 -> 响应。
 * MUL/FMA/RoPE只在完整表达式后舍入一次；FMA的第三操作数以乘积单位输入。
 * 主机for循环表示独立lane的数学行为，不表示RTL把八lane串行成一个标量单元。
 */
#pragma once
#include "common.hpp"
namespace blocks {
struct ECommand : Printable {
    enum class Op {
        Add, // a+b，最后S16饱和。
        Sub, // a-b，最后S16饱和。
        Mul, // RNE((a*b)/2^shift)，再S16饱和。
        Fma, // RNE((a*b+c)/2^shift)，c已与乘积对齐。
        Max, // 逐lane选择较大值。
        Min, // 逐lane选择较小值。
        Select, // c非零选a，否则选b；c不作为逐位掩码。
        Left, // 乘2^shift后饱和，保留所有被移出的位用于检查。
        ArithmeticRight, // floor(a/2^shift)，向负无穷取整，不做RNE。
        RoPE, // 相邻两lane配对旋转，B偶数为cos、奇数为sin。
        RoundRight, // 对a执行RNE右移，与ArithmeticRight区分。
        Abs, // 绝对值，-32768的绝对值夹为32767。
        Pack8, // 按S8范围夹取，打包到bits[0]，不对输入额外移位。
        Reset // E没有跨命令算术状态，Reset只返回成功响应。
    };
    Op op = Op::Add;
    // 右移或左移位数0..31；普通Add/Sub/Max/Min/Select/Abs/Pack8忽略其数值作用。
    unsigned shift = 0;
    // 每数组八个原始S16编码；a为主输入，b为第二操作数/旋转参数，c为FMA加数或Select条件。
    std::array<int16_t, 8> a{}, b{}, c{};
};
class EEngine {
  public:
    using Command = ECommand;
    using Response = Reply;
    // 无状态执行：响应lane[0..7]返回八个带符号结果；任一lane夹取均置saturated。
    // 非法操作或shift越界返回error，不能把Reset枚举值当成旧RTL的裸操作码直接发送。
    Response execute(const Command &c) {
        auto r = reply(c);
        if (c.op == Command::Op::Reset)
            return r;
        if (unsigned(c.op) > 12 || c.shift > 31)
            return reply(c, true);
        r.count = 8;
        for (unsigned i = 0; i < 8; ++i) {
            // 使用宽主机中间量避免左移/乘积溢出；本层不会因此增加通用S128物理算术通路。
            Wide x = c.a[i], y = c.b[i], z = c.c[i], v = 0;
            bool round = false;
            switch (c.op) {
            // a+b，最后S16饱和。
            case Command::Op::Add:
                v = x + y;
                break;
            // a-b，最后S16饱和。
            case Command::Op::Sub:
                v = x - y;
                break;
            // RNE((a*b)/2^shift)，再S16饱和。
            case Command::Op::Mul:
                v = x * y;
                round = true;
                break;
            // RNE((a*b+c)/2^shift)，c已与乘积对齐。
            case Command::Op::Fma:
                v = x * y + z;
                round = true;
                break;
            // 逐lane选择较大值。
            case Command::Op::Max:
                v = std::max(x, y);
                break;
            // 逐lane选择较小值。
            case Command::Op::Min:
                v = std::min(x, y);
                break;
            // c非零选a，否则选b；c不作为逐位掩码。
            case Command::Op::Select:
                v = z ? x : y;
                break;
            // 乘2^shift后饱和，保留所有被移出的位用于检查。
            case Command::Op::Left:
                v = x * power(c.shift);
                break;
            // floor(a/2^shift)，向负无穷取整，不做RNE。
            case Command::Op::ArithmeticRight:
                v = floor_shift(x, c.shift);
                break;
            // 相邻两lane配对旋转，B偶数为cos、奇数为sin。
            case Command::Op::RoPE:
                // i&~1定位偶数cos参数，i|1定位奇数sin参数，i^1定位配对输入。
                // 偶数结果=a_even*cos-a_odd*sin；奇数结果=a_odd*cos+a_even*sin。
                v = x * c.b[i & ~1U] + (i % 2 ? 1 : -1) * Wide(c.a[i ^ 1]) * c.b[i | 1U];
                round = true;
                break;
            // 对a执行RNE右移，与ArithmeticRight区分。
            case Command::Op::RoundRight:
                v = x;
                round = true;
                break;
            // 绝对值，-32768的绝对值夹为32767。
            case Command::Op::Abs:
                v = x < 0 ? -x : x;
                break;
            // 按S8范围夹取，打包到bits[0]，不对输入额外移位。
            case Command::Op::Pack8:
                v = x;
                break;
            default:
                return reply(c, true);
            }
            // 仅标记为round的运算按shift执行一次RNE；之后统一夹取，避免乘法中途损失精度。
            if (round)
                v = rne(v, c.shift);
            r.lane[i] = clamp(v, c.op == Command::Op::Pack8 ? 8 : 16, r.saturated);
            // 打包低字节对应lane0；先转U8保留负数二补码位型，再组合低64位。
            if (c.op == Command::Op::Pack8)
                r.bits[0] |= uint64_t(uint8_t(r.lane[i])) << (8 * i);
        }
        return r;
    }
};
} // namespace blocks
