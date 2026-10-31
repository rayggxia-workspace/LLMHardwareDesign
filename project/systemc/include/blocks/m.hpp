/**
 * M：矩阵分块乘加的无时钟事务模型。
 * LoadA/LoadB -> 双银行操作数 -> 分段点积 -> S40部分和 -> 精确缩放 -> S64结果。
 * ReadFinal才执行右移RNE和S8/S16/S32饱和；跨K分段不能提前舍入。
 * 一次Execute最多8行×K32×8列；错误按行提交/保留，不对整个命令统一回滚。
 * RTL的64个S8乘法器和S16数位分解在本层折叠成精确整数乘法，不代表单拍完成。
 */
#pragma once
#include "common.hpp"
namespace blocks {
struct MCommand : Printable {
    enum class Op {
        Reset, // 清空模型控制/有效性，恢复默认缩放1、左移0。
        LoadA, // 按bank/row/tile装8个S8或S16；仅低64/128位有效。
        LoadB, // 按bank/tile装64个S8，或先后两个32个S16半包。
        Scale, // 配置S16整数系数和0..31位左移，不触发计算。
        Execute, // 检查全部操作数后，按行计算分段、检查范围并提交结果。
        ReadFull, // 读row中的一对S64完整结果，不做舍入。
        ReadFinal, // 读row中的4个结果，右移RNE后按width饱和。
        ReadPartial, // 仅可读最后两行仍驻留的S40部分和，返回一对。
        InvalidateBank, // 只使一个操作数bank失效，保留完整结果。
        InvalidateAll // 使全部操作数、完整结果和部分和归属失效，保留缩放配置。
    };
    Op op = Op::Reset;
    // bank=0/1；row=0..7；tile=0..3（每tile沿K含8项）。
    // half：LoadB时S16的0/1半包；ReadFinal时选结果的前/后四列。
    // rows=1..8、tiles=1..4、last_k=1..8、columns=1..8，实际K=(tiles-1)*8+last_k。
    // shift：Scale为左移0..31，ReadFinal为右移0..63；width为8/16/32；pair为0..3。
    unsigned bank = 0, row = 0, tile = 0, half = 0, rows = 1, tiles = 1, last_k = 8, columns = 8,
             shift = 0, width = 16, pair = 0;
    // wide_a/wide_b=true表示S16，否则S8；clear=true覆盖本次成功行，false追加到已有S64结果。
    bool wide_a = false, wide_b = false, clear = true;
    // 有符号整数有效数，不是FP16/BF16编码；全局二进制尺度由调用方在最终读出时兑现。
    int16_t coefficient = 1;
    // 装载载荷低位优先。A使用低128位，B可使用完整512位；其他命令不读取此数组。
    Line data{};
};
class MEngine {
    // A地址=bank*256+row*32+tile*8+k；B地址=(bank*4+tile)*64+column*8+k。
    // 各512个S16容器=1KiB，包括两bank；装S8时在写入时符号扩展。
    std::array<int16_t, 512> a_{}, b_{};
    // A每8个元素一份valid/format，共2bank*8row*4tile；只有已装且格式吻合才可计算。
    std::array<bool, 64> a_valid_{}, a_format_{};
    // B每tile一份2位装载状态：0未装、1仅S16低半、3完整；b_format_记录对应格式。
    std::array<uint8_t, 8> b_valid_{};
    std::array<bool, 8> b_format_{};
    // 8行×8列完整结果S64；行有效标志及columns_保证追加命令的列数与已有结果一致。
    std::array<int64_t, 64> result_{};
    std::array<bool, 8> result_valid_{};
    std::array<unsigned, 8> columns_{};
    // 主机S64容器承载物理S40值；只保留row%2的两行，partial_owner_=-1表示不可读。
    std::array<int64_t, 16> partial_{}; // physically two rows, S40 values
    std::array<int, 2> partial_owner_{{-1, -1}};
    // 跨命令保持的缩放配置；Invalidate不改变它，Reset恢复默认值。
    int16_t coefficient_ = 1;
    unsigned shift_ = 0;

  public:
    using Command = MCommand;
    using Response = Reply;
    // 执行一条完整事务并更新有限状态；非法描述符/缺失数据在计算前拒绝。
    // 数值溢出则设置failed_rows并只保留对应行旧结果，其他成功行照常提交。
    Response execute(const Command &c) {
        auto r = reply(c);
        switch (c.op) {
        // 清空模型控制/有效性，恢复默认缩放1、左移0。
        case Command::Op::Reset:
            *this = MEngine{};
            break;
        // 按bank/row/tile装8个S8或S16；仅低64/128位有效。
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
        // 按bank/tile装64个S8，或先后两个32个S16半包。
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
        // 配置S16整数系数和0..31位左移，不触发计算。
        case Command::Op::Scale:
            if (c.shift > 31)
                return reply(c, true);
            coefficient_ = c.coefficient;
            shift_ = c.shift;
            break;
        // 检查全部操作数后，按行计算分段、检查范围并提交结果。
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
            // 新Execute开始后，旧命令的部分和不再承诺驻留；本次逐行复用两个槽。
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
                    // 点积先检查S40，乘系数并左移后检查S64，再与旧S64相加检查溢出；中间没有RNE。
                    Wide scaled = dot * coefficient_ * power(shift_);
                    fault |= !fits(scaled, 64);
                    Wide merged = scaled + (c.clear ? 0 : Wide(result_[row * 8 + n]));
                    fault |= !fits(merged, 64);
                    candidate[n] = fits(merged, 64) ? int64_t(merged) : 0;
                }
                // 整行8列检查结束才写回。candidate是主机事务临时量，对应行提交前的候选结果。
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
        // 读row中的一对S64完整结果，不做舍入。
        case Command::Op::ReadFull:
            if (c.row > 7 || c.pair > 3 || !result_valid_[c.row])
                return reply(c, true);
            r.count = 2;
            for (unsigned i = 0; i < 2; ++i)
                r.lane[i] = result_[c.row * 8 + c.pair * 2 + i];
            break;
        // 仅可读最后两行仍驻留的S40部分和，返回一对。
        case Command::Op::ReadPartial:
            if (c.row > 7 || c.pair > 3 || partial_owner_[c.row % 2] != int(c.row))
                return reply(c, true);
            r.count = 2;
            for (unsigned i = 0; i < 2; ++i)
                r.lane[i] = partial_[(c.row % 2) * 8 + c.pair * 2 + i];
            break;
        // 读row中的4个结果，右移RNE后按width饱和。
        case Command::Op::ReadFinal:
            if (c.row > 7 || c.half > 1 || !result_valid_[c.row] || c.shift > 63 ||
                (c.width != 8 && c.width != 16 && c.width != 32))
                return reply(c, true);
            r.count = 4;
            for (unsigned i = 0; i < 4; ++i)
                r.lane[i] =
                    clamp(rne(result_[c.row * 8 + c.half * 4 + i], c.shift), c.width, r.saturated);
            break;
        // 使全部操作数、完整结果和部分和归属失效，保留缩放配置。
        case Command::Op::InvalidateAll:
            a_valid_.fill(false);
            b_valid_.fill(0);
            result_valid_.fill(false);
            partial_owner_ = {{-1, -1}};
            break;
        // 只使一个操作数bank失效，保留完整结果。
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
