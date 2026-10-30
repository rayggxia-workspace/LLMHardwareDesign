#pragma once
#include "common.hpp"
namespace blocks {
struct TCommand : Printable {
    enum class Op { Begin, Write, Commit, Revoke, Peek, Take, Release, Status, Reset };
    Op op = Op::Status;
    unsigned words = 0, index = 0, owner = 0;
    uint32_t generation = 0;
    Word data{};
};
class TEngine {
  public:
    enum class State { Empty, Fill, Sealed, Reading, Release };

  private:
    std::array<Word, 384> payload_{};
    Word held_{};
    State state_ = State::Empty;
    unsigned received_ = 0, cursor_ = 0, words_ = 0, owner_ = 0;
    uint32_t generation_ = 0;
    bool protocol_error_ = false;

  public:
    using Command = TCommand;
    using Response = Reply;
    Response execute(const Command &c) {
        auto r = reply(c);
        switch (c.op) {
        case Command::Op::Reset:
            state_ = State::Empty;
            received_ = cursor_ = words_ = owner_ = 0;
            held_ = {};
            generation_ = 0;
            protocol_error_ = false;
            break;
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
        case Command::Op::Commit:
            if (state_ != State::Sealed)
                return reply(c, true);
            held_ = payload_[0];
            cursor_ = 0;
            state_ = State::Reading;
            break;
        case Command::Op::Revoke:
            if (state_ != State::Fill && state_ != State::Sealed)
                return reply(c, true);
            received_ = cursor_ = 0;
            state_ = State::Empty;
            break;
        case Command::Op::Peek:
        case Command::Op::Take:
            if (state_ != State::Reading)
                return reply(c, true);
            r.bits[0] = held_[0];
            r.bits[1] = held_[1];
            r.index = cursor_;
            r.last = cursor_ + 1 == words_;
            r.count = 1;
            if (c.op == Command::Op::Take) {
                if (r.last)
                    state_ = State::Release;
                else
                    held_ = payload_[++cursor_];
            }
            break;
        case Command::Op::Release:
            if (state_ != State::Release)
                return reply(c, true);
            state_ = State::Empty;
            break;
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
