
#include "blocks/modules.hpp"

#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

using blocks::MCommand;

struct Projection : sc_core::sc_module {
    blocks::M matrix{"M"};
    sc_core::sc_fifo<MCommand> commands{"commands", 1};
    sc_core::sc_fifo<blocks::Reply> responses{"responses", 1};
    const char* fixture;
    unsigned transactions = 0;
    bool passed = false;

    Projection(sc_core::sc_module_name name, const char* path) : sc_module(name), fixture(path) {
        matrix.commands(commands);
        matrix.responses(responses);
        SC_THREAD(run);
    }

    blocks::Reply send(MCommand command) {
        command.tag = ++transactions;
        commands.write(command);
        const auto reply = responses.read();
        if (reply.error || reply.saturated || reply.tag != command.tag)
            throw std::runtime_error("projection transaction rejected");
        return reply;
    }

    void run() {
        std::ifstream input(fixture);
        unsigned k = 0, a_bits = 0, b_bits = 0;
        input >> k >> a_bits >> b_bits;
        if (!input || !k || k > 32768 || (a_bits != 8 && a_bits != 16)
            || (b_bits != 8 && b_bits != 16))
            throw std::runtime_error("invalid projection fixture");
        auto read = [&](unsigned count) {
            std::vector<int> data(count);
            for (auto& value : data)
                if (!(input >> value)) throw std::runtime_error("short operand");
            return data;
        };
        const auto a = read(k);
        const auto b = read(8 * k);
        auto pack = [](blocks::Line& data, unsigned index, int value, unsigned bits) {
            const unsigned per_word = 64 / bits;
            data[index / per_word] |= (uint64_t(value) & ((1ULL << bits) - 1))
                << (index % per_word * bits);
        };
        for (unsigned base = 0; base < k; base += 32) {
            const unsigned count = std::min(32u, k - base);
            const unsigned tiles = (count + 7) / 8;
            for (unsigned tile = 0; tile < tiles; ++tile) {
                const unsigned start = base + tile * 8;
                MCommand command;
                command.tile = tile;
                command.op = MCommand::Op::LoadA;
                command.wide_a = a_bits == 16;
                for (unsigned j = 0; j < 8 && start + j < k; ++j)
                    pack(command.data, j, a[start + j], a_bits);
                send(command);
                command.op = MCommand::Op::LoadB;
                command.wide_b = b_bits == 16;
                const unsigned per_beat = 512 / b_bits;
                for (unsigned j = 0; j < 64; j += per_beat) {
                    command.half = j / per_beat;
                    command.data = {};
                    for (unsigned i = 0; i < per_beat; ++i) {
                        const unsigned column = (j + i) / 8;
                        const unsigned pos = start + (j + i) % 8;
                        if (pos < k) pack(command.data, i, b[column * k + pos], b_bits);
                    }
                    send(command);
                }
            }
            MCommand execute;
            execute.op = MCommand::Op::Execute;
            execute.wide_a = a_bits == 16;
            execute.wide_b = b_bits == 16;
            execute.clear = base == 0;
            execute.tiles = tiles;
            execute.last_k = (count - 1) % 8 + 1;
            send(execute);
        }
        for (unsigned pair = 0; pair < 4; ++pair) {
            MCommand read_full;
            read_full.op = MCommand::Op::ReadFull;
            read_full.pair = pair;
            const auto reply = send(read_full);
            for (unsigned j = 0; j < 2; ++j) {
                int64_t expected;
                if (!(input >> expected) || reply.lane[j] != expected)
                    throw std::runtime_error("SystemC dot product mismatch");
            }
        }
        passed = true;
    }
};

int sc_main(int argc, char** argv) {
    if (argc != 2) return 2;
    Projection model("projection", argv[1]);
    sc_core::sc_start();
    if (!model.passed) return 1;
    std::cout << "{\"passed\":true,\"transactions\":" << model.transactions
              << ",\"checked_values\":8}\n";
    return 0;
}
