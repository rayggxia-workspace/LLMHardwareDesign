/**
 * S：16KiB有限工作存储与S->M供数的事务模型。
 * 1024个128位字，窄地址按低2位选bank；ReadWide合并同一宽行的4个窄字。
 * LoadBegin冻结布局，LoadNext逐个返回A128或B512包，由调用方送入M装载端。
 * 本层串行化存取和供数，不模拟RTL两项A队列/一项B槽、同步读等待、A/B同时发射或仲裁优先级。
 * 因此可验证布局、范围及供数顺序，不能据此计算S带宽或推断物理存储是SRAM。
 */
#pragma once
#include "common.hpp"
namespace blocks {
struct SCommand : Printable {
    // Read/Write为普通存取；ReadWide为512位读取；LoadBegin/LoadNext为有限供数序列。
    // 所有操作通过同一事务入口顺序执行，Reset不会擦除存储。
    enum class Op { Read, Write, ReadWide, LoadBegin, LoadNext, Status, Reset };
    Op op = Op::Status;
    // address：Read/Write为窄字地址0..1023；ReadWide为宽行号0..255。
    // bank指定M的目标银行0/1；rows=1..8、tiles=1..4；a_base/b_base单位为128位字，必须4字对齐。
    unsigned address = 0, bank = 0, rows = 1, tiles = 1, a_base = 0, b_base = 0;
    // wide_a/b选择S16或S8装载格式；reuse_b=true跳过B供数，调用方必须确保M已有匹配的B。
    bool wide_a = false, wide_b = false, reuse_b = false;
    // 仅Write使用，低64位在data[0]，高64位在data[1]。
    Word data{};
};
class SEngine {
    // 固定16KiB载荷空间：窄地址=4*wide_row+bank；每次宽读返回4bank各一个字。
    std::array<Word, 1024> memory_{};
    // Only a software diagnostic: physical RAM has no reset/initial-value promise.
    // 仅为软件诊断：读取从未写过的数据会报错；不意味着RTL为每个字实现初始化位或提供上电值。
    std::array<bool, 1024> initialized_{};
    // loading_=供数未完成；phase_a_=当前供A；aw_/bw_/reuse_为冻结的格式与复用标志。
    bool loading_ = false, phase_a_ = false, aw_ = false, bw_ = false, reuse_ = false;
    // bank_/rows_/tiles_/abase_/bbase_保存描述符；tile_=当前K8块，row_=当前A行，half_=当前B半包。
    unsigned bank_ = 0, rows_ = 0, tiles_ = 0, abase_ = 0, bbase_ = 0, tile_ = 0, row_ = 0,
             half_ = 0;

  public:
    using Command = SCommand;
    using Response = Reply;
    // 每次操作返回一个响应；LoadNext只暂存本次运输包，没有额外整矩阵缓冲。
    // 供数期间普通读写拒绝，未初始化LoadNext拒绝且不推进游标；响应元数据与数据同包返回。
    Response execute(const Command &c) {
        auto r = reply(c);
        switch (c.op) {
        // 停止供数，不清除存储内容与初始化诊断标记。
        case Command::Op::Reset:
            loading_ = false;
            break; // memory intentionally survives
        // 在非供数期间写一个128位字，响应回显写入值。
        case Command::Op::Write:
            if (c.address >= 1024 || loading_)
                return reply(c, true);
            memory_[c.address] = c.data;
            initialized_[c.address] = true;
            r.bits[0] = c.data[0];
            r.bits[1] = c.data[1];
            break;
        // 在非供数期间读一个已初始化的128位字。
        case Command::Op::Read:
            if (c.address >= 1024 || loading_ || !initialized_[c.address])
                return reply(c, true);
            r.bits[0] = memory_[c.address][0];
            r.bits[1] = memory_[c.address][1];
            r.count = 1;
            break;
        // 以宽行号读取连续4个已初始化字，低bank位于低128位。
        case Command::Op::ReadWide:
            if (c.address >= 256 || loading_)
                return reply(c, true);
            for (unsigned i = 0; i < 4; ++i)
                if (!initialized_[c.address * 4 + i])
                    return reply(c, true);
            for (unsigned i = 0; i < 4; ++i)
                for (unsigned l = 0; l < 2; ++l)
                    r.bits[i * 2 + l] = memory_[c.address * 4 + i][l];
            r.count = 4;
            break;
        // 校验有限布局并冻结供数描述符，不在此调用M。
        case Command::Op::LoadBegin:
            if (loading_ || c.bank > 1 || c.rows < 1 || c.rows > 8 || c.tiles < 1 || c.tiles > 4 ||
                c.a_base >= 1024 || c.b_base >= 1024 || c.a_base % 4 || c.b_base % 4 ||
                c.a_base + c.tiles * (c.rows > 4 ? 8 : 4) > 1024 ||
                (!c.reuse_b && c.b_base + c.tiles * (c.wide_b ? 8 : 4) > 1024))
                return reply(c, true);
            // A每tile占ceil(rows/4)个512位组，即4或8个窄字；S8 B每tile占4字，S16 B占8字。
            // 冻结描述符后先B再A；reuse_b=true时直接从A开始。
            loading_ = true;
            bank_ = c.bank;
            rows_ = c.rows;
            tiles_ = c.tiles;
            abase_ = c.a_base;
            bbase_ = c.b_base;
            aw_ = c.wide_a;
            bw_ = c.wide_b;
            reuse_ = c.reuse_b;
            phase_a_ = reuse_;
            tile_ = row_ = half_ = 0;
            break;
        // 返回一个可交给M的A128或B512包，再推进供数游标。
        case Command::Op::LoadNext: {
            if (!loading_)
                return reply(c, true);
            // One typed beat per transaction. Consumer drives next only after
            // accepting the previous beat: no hidden unbounded staging queue.
            // A地址=abase+tile*每tile预留字数+row；B地址=bbase+tile*B字数+half*4。
            // A的S8数据也占一个128位容器，其高64位不由M使用。
            unsigned address = phase_a_ ? abase_ + tile_ * (rows_ > 4 ? 8 : 4) + row_
                                        : bbase_ + tile_ * (bw_ ? 8 : 4) + half_ * 4;
            unsigned words = phase_a_ ? 1 : 4;
            for (unsigned i = 0; i < words; ++i)
                if (!initialized_[address + i])
                    return reply(c, true);
            for (unsigned i = 0; i < words; ++i)
                for (unsigned l = 0; l < 2; ++l)
                    r.bits[i * 2 + l] = memory_[address + i][l];
            // 供数响应lane[0..4]=类型(A0/B1)、目标bank、A行号/B半号、tile、宽格式。
            // bits为低位优先载荷，count为128位字数：A=1、B=4。last表示整个描述符已发完。
            r.lane[0] = phase_a_ ? 0 : 1;
            r.lane[1] = bank_;
            r.lane[2] = phase_a_ ? row_ : half_;
            r.lane[3] = tile_;
            r.lane[4] = phase_a_ ? aw_ : bw_;
            r.count = words;
            // B16先half0后half1，B8只有一包；随后逐行发A。每tile的A发完后再进入下一tile。
            if (!phase_a_) {
                if (bw_ && !half_)
                    half_ = 1;
                else {
                    half_ = 0;
                    phase_a_ = true;
                }
            } else if (++row_ == rows_) {
                row_ = 0;
                if (++tile_ == tiles_)
                    loading_ = false;
                else
                    phase_a_ = reuse_;
            }
            r.last = !loading_;
            break;
        }
        // lane0返回是否仍在供数；只读查询，不推进地址。
        case Command::Op::Status:
            r.lane[0] = loading_;
            r.count = 1;
            break;
        default:
            return reply(c, true);
        }
        return r;
    }
};
} // namespace blocks
