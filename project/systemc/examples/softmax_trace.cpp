// Run this example to see 257 values pass through S -> N -> T.
// No full-vector array exists in N. S keeps inputs AND the EXP replay values.
#include "blocks/modules.hpp"
#include <iostream>
#include <stdexcept>
using namespace blocks;
struct Demo : sc_core::sc_module {
    S storage{"S"};
    N norm{"N"};
    T transfer{"T"};
    sc_core::sc_fifo<SCommand> si{"si", 1};
    sc_core::sc_fifo<NCommand> ni{"ni", 1};
    sc_core::sc_fifo<TCommand> ti{"ti", 1};
    sc_core::sc_fifo<Reply> so{"so", 1}, no{"no", 1}, to{"to", 1};
    uint64_t tag = 0;
    bool completed = false;
    SC_HAS_PROCESS(Demo);
    Demo(sc_core::sc_module_name name) : sc_module(name) {
        storage.commands(si);
        storage.responses(so);
        norm.commands(ni);
        norm.responses(no);
        transfer.commands(ti);
        transfer.responses(to);
        SC_THREAD(run);
    }
    template <class C> Reply send(sc_core::sc_fifo<C> &in, sc_core::sc_fifo<Reply> &out, C c) {
        c.tag = ++tag;
        in.write(c);
        auto r = out.read();
        if (r.error || r.tag != c.tag)
            throw std::runtime_error("transaction rejected or response reordered");
        return r;
    }
    static Word pack(const std::array<int64_t, 8> &lane) {
        Word w{};
        for (unsigned i = 0; i < 8; ++i)
            w[i / 4] |= uint64_t(uint16_t(lane[i])) << (16 * (i % 4));
        return w;
    }
    void run() {
        constexpr unsigned length = 257, words = (length + 7) / 8, exp_base = 128;
        for (unsigned word = 0; word < words; ++word) {
            SCommand c;
            c.op = SCommand::Op::Write;
            c.address = word;
            std::array<int64_t, 8> values{};
            for (unsigned i = 0; i < 8 && word * 8 + i < length; ++i) {
                unsigned index = word * 8 + i;
                values[i] = index == 256 ? 4096 : int64_t((int(index % 4) - 1) * 1024);
            }
            c.data = pack(values);
            send(si, so, c);
        }
        NCommand c;
        c.op = NCommand::Op::Begin;
        send(ni, no, c);
        for (unsigned word = 0; word < words; ++word) {
            SCommand read;
            read.op = SCommand::Op::Read;
            read.address = word;
            auto source = send(si, so, read);
            c.op = NCommand::Op::Stats;
            c.count = std::min(8U, length - word * 8);
            for (unsigned i = 0; i < c.count; ++i)
                c.data[i] = halfword(source.bits, i);
            send(ni, no, c);
            NCommand query;
            query.op = NCommand::Op::ReadStats;
            auto stats = send(ni, no, query);
            std::cout << "STATS chunk=" << word << " accepted=" << stats.lane[0]
                      << " running_max=" << stats.lane[1] << "\n";
        }
        c.op = NCommand::Op::Finalize;
        send(ni, no, c);
        for (unsigned word = 0; word < words; ++word) {
            SCommand read;
            read.op = SCommand::Op::Read;
            read.address = word;
            auto source = send(si, so, read);
            c.op = NCommand::Op::Exp;
            c.count = std::min(8U, length - word * 8);
            for (unsigned i = 0; i < c.count; ++i)
                c.data[i] = halfword(source.bits, i);
            auto ex = send(ni, no, c);
            SCommand write;
            write.op = SCommand::Op::Write;
            write.address = exp_base + word;
            write.data = pack(ex.lane);
            send(si, so, write);
            NCommand query;
            query.op = NCommand::Op::ReadStats;
            auto stats = send(ni, no, query);
            std::cout << "EXP   chunk=" << word << " exp_count=" << stats.lane[5]
                      << " denominator_UQ1.15=" << stats.lane[6] << " first_exp=" << ex.lane[0]
                      << "\n";
        }
        c.op = NCommand::Op::FinishExp;
        send(ni, no, c);
        c.op = NCommand::Op::ReadFactor;
        std::cout << "FACTOR floor(2^44/denominator)=" << send(ni, no, c).lane[0] << "\n";
        TCommand tc;
        tc.op = TCommand::Op::Begin;
        tc.words = words;
        tc.generation = 1;
        send(ti, to, tc);
        int64_t probability_sum = 0;
        for (unsigned word = 0; word < words; ++word) {
            SCommand read;
            read.op = SCommand::Op::Read;
            read.address = exp_base + word;
            auto source = send(si, so, read);
            c.op = NCommand::Op::SoftReplay;
            c.count = std::min(8U, length - word * 8);
            for (unsigned i = 0; i < c.count; ++i)
                c.data[i] = halfword(source.bits, i);
            auto y = send(ni, no, c);
            for (unsigned i = 0; i < c.count; ++i)
                probability_sum += y.lane[i];
            tc.op = TCommand::Op::Write;
            tc.index = word;
            tc.data = pack(y.lane);
            send(ti, to, tc);
            std::cout << "REPLAY chunk=" << word << " output_Q1.14=";
            for (unsigned i = 0; i < c.count; ++i)
                std::cout << (i ? " " : "") << y.lane[i];
            std::cout << "\n";
        }
        tc.op = TCommand::Op::Commit;
        send(ti, to, tc);
        for (unsigned word = 0; word < words; ++word) {
            tc.op = TCommand::Op::Take;
            auto result = send(ti, to, tc);
            if (result.index != word || result.last != (word + 1 == words))
                throw std::runtime_error("T result sequence");
        }
        tc.op = TCommand::Op::Release;
        send(ti, to, tc);
        std::cout << "DONE sum_of_quantized_probabilities=" << probability_sum
                  << "/16384 (independent rounding need not sum to exactly one)\n";
        completed = true;
        sc_core::sc_stop();
    }
};
int sc_main(int, char **) {
    try {
        Demo demo{"softmax_demo"};
        sc_core::sc_start();
        return demo.completed ? 0 : 1;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
