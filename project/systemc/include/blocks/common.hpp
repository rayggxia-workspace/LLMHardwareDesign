/**
 * 公共数值与事务类型：七类宏共享的原始整数编码、RNE和范围检查。
 * S16/S32表示有符号整数位宽；Q格式/二进制尺度由各块的命令合同说明。
 * Wide和S64运输容器是主机实现手段，不能由sizeof推导物理寄存器宽度。
 * 本层不调度时钟，不访问RTL，也不分配可增长的片上数据缓冲。
 */
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <ostream>
namespace blocks {
// Host-wide temporaries are arithmetic checks, not additional physical storage.
// 主机有符号128位临时量：完整保留乘积/对齐位，检查物理S40/S64边界后才窄化。
using Wide = __int128_t;
// Word[0]为低64位、Word[1]为高64位；只描述一个128位运输字。
using Word = std::array<uint64_t, 2>; // 128 bits, least significant limb first
// Line[0]最低；一个512位运输包可容纳64个S8或32个S16。
using Line = std::array<uint64_t, 8>; // 512 bits
// 所有命令/响应的公共基类。tag由调用方指定，仅用于对应请求和响应，不是硬件身份认证。
struct Printable {
    uint64_t tag = 0;
};
// SystemC FIFO在打印诊断信息时需要流输出运算符；这里只输出事务tag。
inline std::ostream &operator<<(std::ostream &os, const Printable &p) {
    return os << "txn#" << p.tag;
}
// 公共响应容器，只有当前命令定义的字段有效，未使用位置保持零。
// error=非法事务或计算失败；saturated=允许的夹取；last=供数/消费的末包。
// failed_rows=M失败行掩码；count=有效lane数，S中则为128位字数；index=T当前消费字序号。
// lane为有符号数值/调试字段，bits为原始打包数据；二者并非一组新物理端口。
struct Reply : Printable {
    bool error = false, saturated = false, last = false;
    uint8_t failed_rows = 0;
    unsigned count = 0, index = 0;
    std::array<int64_t, 8> lane{};
    Line bits{};
};
// 精确生成2^s；调用方保证s在主机有符号128位正值可表示范围内。
inline Wide power(unsigned s) { return Wide(1) << s; }
// Floor-quotient RNE works for negatives too; no signed-negative left shifts.
// 计算RNE(x/2^s)：最近舍入、恰好一半时取偶数；s=0原样返回。
// C++负数除法向零截断，先把(q,r)修成向下取整且0<=r<2^s，再统一处理正负数。
// 例如RNE(-3/2)=-2、RNE(-5/2)=-2；不能用“加半后右移”代替所有负数情况。
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
// 有符号算术右移的数学定义floor(x/2^s)，不依赖编译器对负数右移的实现选择。
inline Wide floor_shift(Wide x, unsigned s) {
    const Wide d = power(s);
    return x / d - (x % d < 0);
}
// 检查有符号width位范围[-2^(width-1),2^(width-1)-1]；调用方提供合法正位宽。
inline bool fits(Wide x, unsigned width) { return x >= -power(width - 1) && x < power(width - 1); }
// 按目标有符号位宽夹取；发生任一夹取就置saturated，已有true不会被后续正常lane清除。
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
// 取低32位并按二补码解释。供R仿真物理窄寄存器/存储原始衰减位型使用，绝非饱和。
// 若计算原值溢出，REngine::checked会先记录失败；截断值不允许作为成功状态提交。
inline int32_t wrap32(Wide x) {
    const uint32_t u = uint32_t(x);
    return u <= 0x7fffffffU ? int32_t(u) : int32_t(int64_t(u) - 0x100000000LL);
}
// 无浮点的整数平方根floor(sqrt(x))；逐个二进制位对试减，返回值满足root²<=原x<(root+1)²。
// bit从2^62开始，每轮除4；x是逐步扣除的余量，root是算法的部分根。
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
// 把0..65535的原始16位位型显式解释为-32768..32767，不把EXP的无符号编码直接送此函数。
inline int16_t signed16(uint16_t u) { return u < 32768 ? int16_t(u) : int16_t(int32_t(u) - 65536); }
// 取512位包中第i个16位元素，i=0为最低16位；调用方保证i<32。
inline uint16_t halfword(const Line &w, unsigned i) { return uint16_t(w[i / 4] >> (16 * (i % 4))); }
// 取第i个8位元素，i=0为最低字节；调用方保证i<64。
inline uint8_t byte(const Line &w, unsigned i) { return uint8_t(w[i / 8] >> (8 * (i % 8))); }
// 建立零初始化响应并继承命令tag；可选错误标记，其余载荷由具体操作填入。
inline Reply reply(const Printable &c, bool error = false) {
    Reply r;
    r.tag = c.tag;
    r.error = error;
    return r;
}
} // namespace blocks
