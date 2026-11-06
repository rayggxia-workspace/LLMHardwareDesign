
#include "Vblock_v2_m.h"
#include "verilated.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

constexpr unsigned lanes = 8;
constexpr unsigned tile_k = 8;
constexpr unsigned segment_k = 32;

void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

struct Fixture {
    unsigned k = 0, a_bits = 0, b_bits = 0;
    std::vector<int> a;
    std::array<std::vector<int>, lanes> b;
    std::array<int64_t, lanes> expected{};

    explicit Fixture(const char* path) {
        std::ifstream in(path);
        in >> k >> a_bits >> b_bits;
        check(in.good() && k > 0 && k <= 32768, "invalid K");
        check((a_bits == 8 || a_bits == 16) && (b_bits == 8 || b_bits == 16), "invalid format");
        auto read_vector = [&](std::vector<int>& vector, unsigned bits) {
            vector.resize(k);
            const int bound = 1 << (bits - 1);
            for (int& value : vector) {
                check(bool(in >> value) && value >= -bound && value < bound, "invalid operand");
            }
        };
        read_vector(a, a_bits);
        for (auto& row : b) read_vector(row, b_bits);
        for (auto& value : expected) check(bool(in >> value), "missing dot product");
    }
};

struct Metrics {
    uint64_t cycles = 0, a_beats = 0, b_beats = 0, commands = 0, responses = 0;
    uint64_t load_cycles = 0, execution_cycles = 0, overlap_cycles = 0, held_cycles = 0;
    uint64_t a_transitions = 0, b_transitions = 0, response_transitions = 0;
};

class Bench {
public:
    Metrics metrics;

    explicit Bench(const Fixture& fixture) : f(fixture) {
        dut.reset = 1;
        dut.a_valid = dut.b_valid = dut.cmd_valid = dut.rsp_ready = 0;
        for (unsigned i = 0; i < 4; ++i) dut.a_data[i] = 0;
        for (unsigned i = 0; i < 16; ++i) dut.b_data[i] = 0;
        dut.a_wide = f.a_bits == 16;
        dut.b_wide = f.b_bits == 16;
        dut.a_row = 0;
        dut.b_half = 0;
        edge();
        edge();
        dut.reset = 0;
        dut.eval();
    }

    void run(bool prefetch, unsigned hold) {
        const unsigned segments = (f.k + segment_k - 1) / segment_k;
        for (unsigned segment = 0; segment < segments; ++segment) {
            if (!prefetch || segment == 0) {
                for (unsigned i = 0; i < load_steps(segment); ++i) load(segment, i, false);
            }
            const unsigned count = std::min(segment_k, f.k - segment * segment_k);
            const unsigned tiles = (count + tile_k - 1) / tile_k;
            const uint64_t descriptor = uint64_t(dut.a_wide) | (uint64_t(dut.b_wide) << 1)
                | (uint64_t(segment == 0) << 2) | (uint64_t((count - 1) % tile_k + 1) << 4)
                | (uint64_t(lanes) << 8) | (uint64_t(tiles) << 12) | (1ULL << 15);
            const int next = prefetch && segment + 1 < segments ? int(segment + 1) : -1;
            command(10, (segment % 2) * 32, descriptor, next, hold);
        }
        for (unsigned i = 0; i < lanes / 2; ++i) {
            const auto data = command(3, i, 0, -1, 0);
            for (unsigned j = 0; j < 2; ++j) {
                const uint64_t bits = uint64_t(data[j * 2]) | (uint64_t(data[j * 2 + 1]) << 32);
                int64_t value;
                std::memcpy(&value, &bits, sizeof(value));
                check(value == f.expected[2 * i + j], "integer dot product mismatch");
            }
        }
        const unsigned tiles = (f.k + tile_k - 1) / tile_k;
        check(metrics.a_beats == tiles && metrics.b_beats == tiles * b_halves(), "beat count mismatch");
        check(metrics.commands == segments + lanes / 2 && metrics.responses == metrics.commands,
              "command/response accounting mismatch");
        check(metrics.held_cycles == uint64_t(hold) * segments, "hold accounting mismatch");
        dut.final();
    }

private:
    const Fixture& f;
    Vblock_v2_m dut;
    std::array<uint32_t, 4> prior_a{}, prior_response{};
    std::array<uint32_t, 16> prior_b{};

    unsigned b_halves() const { return f.b_bits / 8; }

    unsigned load_steps(unsigned segment) const {
        const unsigned count = std::min(segment_k, f.k - segment * segment_k);
        return ((count + tile_k - 1) / tile_k) * b_halves();
    }

    template <size_t N, typename Port>
    static uint64_t toggles(const Port& port, std::array<uint32_t, N>& prior) {
        uint64_t count = 0;
        for (size_t i = 0; i < N; ++i) {
            count += __builtin_popcount(port[i] ^ prior[i]);
            prior[i] = port[i];
        }
        return count;
    }

    void edge() {
        dut.clk = 0;
        dut.eval();
        dut.clk = 1;
        dut.eval();
        dut.clk = 0;
        dut.eval();
    }

    void tick(bool executing = false) {
        dut.eval();
        const bool load = dut.a_valid || dut.b_valid;
        check(!dut.a_valid || dut.a_ready, "A bank not ready");
        check(!dut.b_valid || dut.b_ready, "B bank not ready");
        check(!dut.cmd_valid || dut.cmd_ready, "command not accepted");
        ++metrics.cycles;
        metrics.a_beats += dut.a_valid;
        metrics.b_beats += dut.b_valid;
        metrics.commands += dut.cmd_valid;
        metrics.responses += dut.rsp_valid && dut.rsp_ready;
        metrics.load_cycles += load;
        metrics.execution_cycles += executing;
        metrics.overlap_cycles += load && executing;
        metrics.held_cycles += dut.rsp_valid && !dut.rsp_ready;
        metrics.a_transitions += toggles(dut.a_data, prior_a);
        metrics.b_transitions += toggles(dut.b_data, prior_b);
        metrics.response_transitions += toggles(dut.rsp_data, prior_response);
        edge();
    }

    void load(unsigned segment, unsigned beat, bool executing) {
        const unsigned tile = beat / b_halves();
        const unsigned half = beat % b_halves();
        const unsigned base = segment * segment_k + tile * tile_k;
        dut.a_valid = half == 0;
        dut.a_bank = dut.b_bank = segment % 2;
        dut.a_tile = dut.b_tile = tile;
        dut.b_valid = 1;
        dut.b_half = half;
        if (dut.a_valid) {
            for (unsigned i = 0; i < 4; ++i) dut.a_data[i] = 0;
            const unsigned elements_per_word = 32 / f.a_bits;
            for (unsigned i = 0; i < tile_k && base + i < f.k; ++i) {
                const uint32_t bits = uint32_t(f.a[base + i]) & ((1u << f.a_bits) - 1);
                dut.a_data[i / elements_per_word] |= bits << (i % elements_per_word * f.a_bits);
            }
        }
        for (unsigned i = 0; i < 16; ++i) dut.b_data[i] = 0;
        const unsigned elements_per_word = 32 / f.b_bits;
        const unsigned elements_per_beat = 16 * elements_per_word;
        for (unsigned i = 0; i < elements_per_beat; ++i) {
            const unsigned index = i + half * elements_per_beat;
            const unsigned k = base + index % tile_k;
            if (k < f.k) {
                const uint32_t bits = uint32_t(f.b[index / tile_k][k]) & ((1u << f.b_bits) - 1);
                dut.b_data[i / elements_per_word] |= bits << (i % elements_per_word * f.b_bits);
            }
        }
        tick(executing);
        dut.a_valid = dut.b_valid = 0;
    }

    std::array<uint32_t, 4> command(unsigned op, unsigned index, uint64_t data,
                                    int next, unsigned hold) {
        dut.cmd_valid = 1;
        dut.cmd_op = op;
        dut.cmd_index = index;
        dut.cmd_data = data;
        tick(op == 10);
        dut.cmd_valid = 0;
        const unsigned next_beats = next < 0 ? 0 : load_steps(unsigned(next));
        unsigned loaded = 0, waited = 0;
        while (!dut.rsp_valid) {
            check(++waited < 1000, "response timeout");
            if (loaded < next_beats) load(unsigned(next), loaded++, true);
            else tick(op == 10);
        }
        check(loaded == next_beats, "compute interval too short to prefetch");
        check(!dut.rsp_error && !dut.rsp_saturated, "unexpected response flags");
        const std::array<uint32_t, 4> value{
            dut.rsp_data[0], dut.rsp_data[1], dut.rsp_data[2], dut.rsp_data[3]};
        for (unsigned i = 0; i < hold; ++i) {
            tick();
            check(dut.rsp_valid && std::equal(value.begin(), value.end(), &dut.rsp_data[0]),
                  "held response changed");
        }
        dut.rsp_ready = 1;
        tick();
        dut.rsp_ready = 0;
        dut.eval();
        return value;
    }
};

int main(int argc, char** argv) {
    try {
        check(argc == 4, "usage: Vblock_v2_m FIXTURE serial|prefetch HOLD");
        Verilated::commandArgs(argc, argv);
        const std::string schedule = argv[2];
        check(schedule == "serial" || schedule == "prefetch", "unknown schedule");
        const unsigned hold = std::stoul(argv[3]);
        const Fixture fixture(argv[1]);
        Bench bench(fixture);
        bench.run(schedule == "prefetch", hold);
        const auto& m = bench.metrics;
        std::cout << "{\"passed\":true,\"k\":" << fixture.k
                  << ",\"a_bits\":" << fixture.a_bits << ",\"b_bits\":" << fixture.b_bits
                  << ",\"schedule\":\"" << schedule << "\",\"hold_per_segment\":" << hold
                  << ",\"cycles\":" << m.cycles << ",\"execution_command_cycles\":" << m.execution_cycles
                  << ",\"operand_load_cycles\":" << m.load_cycles << ",\"overlapped_load_cycles\":" << m.overlap_cycles
                  << ",\"response_hold_cycles\":" << m.held_cycles << ",\"a_beats\":" << m.a_beats
                  << ",\"b_beats\":" << m.b_beats << ",\"commands\":" << m.commands
                  << ",\"responses\":" << m.responses << ",\"a_data_toggles\":" << m.a_transitions
                  << ",\"b_data_toggles\":" << m.b_transitions
                  << ",\"response_data_toggles\":" << m.response_transitions << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
