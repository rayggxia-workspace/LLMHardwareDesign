/**
 * T：6KiB有限结果交接模型，384个128位载荷字加一个当前保持字。
 * Empty --Begin--> Fill --写满--> Sealed --Commit--> Reading --消费末字--> Release --Release--> Empty。
 * 只有Fill/Sealed允许Revoke；提交后消费者必须完整消费再Release，不允许另开一批覆盖。
 * Peek不推进游标，Take消费一个字；同步读请求/返回的拍间等待在本层折叠。
 * owner/generation是保存的标签，不代表每条Commit/Revoke命令都执行了跨主体身份认证。
 */
#pragma once
#include "common.hpp"
namespace blocks {
struct TCommand : Printable {
    // 事务命令名称不等于RTL的逐拍握手信号；未到相应阶段的尝试在此返回error。
    enum class Op { Begin, Write, Commit, Revoke, Peek, Take, Release, Status, Reset };
    Op op = Op::Status;
    // words仅Begin使用，1..384；index仅Write使用，必须从0顺序增加；owner仅Begin使用，0..3。
    unsigned words = 0, index = 0, owner = 0;
    // 调用方给出的批次版本标签，Begin记录，Status读回，不自动递增。
    uint32_t generation = 0;
    // Write的一份128位结果；Peek/Take在响应bits[0..1]中返回同一布局。
    Word data{};
};
class TEngine {
  public:
    // Empty无批次；Fill正在填充；Sealed完整但未交付；Reading可消费；Release已耗尽待释放。
    // 这些是事务层可见状态，不包含RTL同步存储的READ_REQ等待拍。
    enum class State { Empty, Fill, Sealed, Reading, Release };

  private:
    // 唯一一份6KiB批次载荷；不能把已提交和下一批都同时放入此数组。
    std::array<Word, 384> payload_{};
    // 当前对外保持字。Peek/下游停顿不改变它，Take后才补下一字。
    Word held_{};
    // received_=已顺序写入字数，cursor_=当前消费序号，words_=批次总字数，owner_=批次标签。
    State state_ = State::Empty;
    unsigned received_ = 0, cursor_ = 0, words_ = 0, owner_ = 0;
    // 本批次版本；保留到下一次Begin或Reset，Release不专门擦标签。
    uint32_t generation_ = 0;
    // 粘滞诊断位：Empty中非法Begin长度、Fill中错误Write序号置位；仅Reset清除。
    // 并非所有error响应都置此位；模型拒绝操作与RTL的sticky协议错误条件需区分。
    bool protocol_error_ = false;

  public:
    using Command = TCommand;
    using Response = Reply;
    // 载荷读取只能在Commit之后发生；最后一次Take后，Release之前仍不可复用存储。
    // Peek和Take响应含bits[0..1]、当前index、末字last和count=1；其他无载荷操作仅确认状态更新。
    Response execute(const Command &c) {
        auto r = reply(c);
        switch (c.op) {
        // 清除控制、保持字和sticky错误；payload不清零，旧载荷因状态门控而不可读。
        case Command::Op::Reset:
            state_ = State::Empty;
            received_ = cursor_ = words_ = owner_ = 0;
            held_ = {};
            generation_ = 0;
            protocol_error_ = false;
            break;
        // Empty中申请1..384字批次并记录owner/generation。
        case Command::Op::Begin:
            if (state_ != State::Empty)
                return reply(c, true);
            if (!c.words || c.words > 384) {
                protocol_error_ = true;
                return reply(c, true);
            }
            if (c.owner > 3)
                return reply(c, true);
            words_ = c.words;
            owner_ = c.owner;
            generation_ = c.generation;
            received_ = cursor_ = 0;
            state_ = State::Fill;
            break;
        // Fill中只接收index==received的顺序写，最后一个字自动封口。
        case Command::Op::Write:
            if (state_ != State::Fill)
                return reply(c, true);
            if (c.index != received_) {
                protocol_error_ = true;
                return reply(c, true);
            }
            payload_[received_++] = c.data;
            if (received_ == words_)
                state_ = State::Sealed;
            break;
        // 仅Sealed允许，锁定完整载荷并把首字装入held。
        case Command::Op::Commit:
            if (state_ != State::Sealed)
                return reply(c, true);
            // 这里折叠了RTL同步读的等待状态；数据在事务上立即可见，不据此推断硬件零读延迟。
            held_ = payload_[0];
            cursor_ = 0;
            state_ = State::Reading;
            break;
        // 仅Fill/Sealed允许撤销，丢弃批次但不擦除旧字节。
        case Command::Op::Revoke:
            if (state_ != State::Fill && state_ != State::Sealed)
                return reply(c, true);
            received_ = cursor_ = 0;
            state_ = State::Empty;
            break;
        // 只查看当前held字，重复读取返回同样的数据和index。
        case Command::Op::Peek:
        // 返回当前held字并消费；非末字补下一字，末字进入Release。
        case Command::Op::Take:
            if (state_ != State::Reading)
                return reply(c, true);
            r.bits[0] = held_[0];
            r.bits[1] = held_[1];
            r.index = cursor_;
            r.last = cursor_ + 1 == words_;
            r.count = 1;
            // 仅Take推动消费。即使是末字也先返回原held，再进入Release；绝不越界预读第384项之后。
            if (c.op == Command::Op::Take) {
                if (r.last)
                    state_ = State::Release;
                else
                    held_ = payload_[++cursor_];
            }
            break;
        // 仅全部消费后允许，结束本批存储租用并回到Empty。
        case Command::Op::Release:
            if (state_ != State::Release)
                return reply(c, true);
            state_ = State::Empty;
            break;
        // lane[0..5]返回state/owner/generation/words/received/protocol_error。
        case Command::Op::Status:
            r.lane[0] = int(state_);
            r.lane[1] = owner_;
            r.lane[2] = generation_;
            r.lane[3] = words_;
            r.lane[4] = received_;
            r.lane[5] = protocol_error_;
            r.count = 6;
            break;
        default:
            return reply(c, true);
        }
        return r;
    }
};
} // namespace blocks
