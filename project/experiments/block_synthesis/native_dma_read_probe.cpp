#include "Vmc_dma_fabric_typed_p.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <tuple>
#include <vector>

struct Stall {
    int begin, end, mask;
};
struct Read {
    int release, client, bytes, length;
    uint64_t address;
};
struct Beat {
    int read, client;
    uint32_t local;
    uint64_t address;
    int reserved = -1, offer = -1, issue = -1, captured = -1, delivered = -1, entry = -1;
};
struct Response {
    uint64_t tag;
    int beat, due;
};

static void require(bool valid, const char* message) {
    if (!valid) throw std::runtime_error(message);
}

template<class Port>
static uint64_t get64(const Port& data, int lane) {
    return uint64_t(data[2 * lane]) | (uint64_t(data[2 * lane + 1]) << 32);
}

template<class Port>
static void put64(Port& data, int lane, uint64_t value) {
    data[2 * lane] = uint32_t(value);
    data[2 * lane + 1] = uint32_t(value >> 32);
}

static int ready(const std::vector<Stall>& intervals, int tick, int full) {
    for (const auto& range : intervals)
        if (range.begin <= tick && tick < range.end) return range.mask;
    return full;
}

static std::vector<Stall> intervals(std::istream& input) {
    size_t count;
    input >> count;
    std::vector<Stall> result(count);
    for (auto& row : result) input >> row.begin >> row.end >> row.mask;
    return result;
}

static void edge(Vmc_dma_fabric_typed_p& chip) {
    chip.clk = 1;
    chip.eval();
    chip.clk = 0;
    chip.eval();
}

int main(int argc, char** argv) try {
    require(argc == 2, "usage: native DMA probe scenario");
    std::ifstream input(argv[1]);
    require(input.good(), "missing scenario");
    std::array<int, 2> latency;
    input >> latency[0] >> latency[1];
    auto ddr_stalls = intervals(input);
    auto client_stalls = intervals(input);
    size_t read_count;
    input >> read_count;
    std::vector<Read> reads(read_count);
    for (auto& read : reads) input >> read.release >> read.client >> read.address >> read.bytes >> read.length;
    require(bool(input), "invalid scenario");

    Verilated::randReset(0);
    Vmc_dma_fabric_typed_p chip;
    chip.clk = 0;
    chip.reset = 1;
    chip.c_req_valid = chip.c_close_valid = chip.c_cancel_valid = chip.c_fence_valid = 0;
    chip.p_mode_valid = chip.p_mode_native64 = chip.p_mode_client_drained = 0;
    chip.c_cancel_ack_ready = chip.c_fence_done_ready = 4095;
    chip.d_req_ready = chip.d_rsp_valid = chip.d_fence_done_valid = 0;
    chip.fault_ready = chip.d_fence_ready = 1;
    chip.eval();
    for (int i = 0; i < 4; ++i) edge(chip);
    chip.reset = 0;
    for (int i = 0; i < 8 && chip.debug_generation != 2; ++i) {
        chip.eval();
        bool request = chip.d_fence_valid;
        auto generation = chip.d_fence_generation;
        edge(chip);
        chip.d_fence_done_valid = request;
        chip.d_fence_done_generation = generation;
    }
    chip.d_fence_done_valid = 0;
    require(chip.debug_generation == 2, "startup DDR purge did not finish");

    std::vector<Beat> beats;
    std::vector<std::vector<int>> read_beats(read_count);
    int serial = 0;
    for (size_t i = 0; i < reads.size(); ++i) {
        const auto& read = reads[i];
        const int shift = read.client < 9 ? 1 : 5;
        for (int b = 0; b < read.bytes / 64; ++b) {
            if (b % read.length == 0) ++serial;
            const uint32_t tag = (uint32_t(serial) << shift) | uint32_t(b % read.length);
            read_beats[i].push_back(int(beats.size()));
            beats.push_back({int(i), read.client, tag, read.address + 64 * uint64_t(b)});
        }
    }
    std::array<std::deque<int>, 12> source;
    std::map<std::pair<int, uint64_t>, int> by_address;
    std::map<std::pair<int, uint32_t>, int> by_local;
    std::array<std::deque<Response>, 2> returns;
    std::array<Response, 4> return_lane{};
    std::array<bool, 4> return_valid{};
    size_t delivered = 0;
    for (int tick = 0; tick < 4096 && delivered < beats.size(); ++tick) {
        for (size_t i = 0; i < reads.size(); ++i)
            if (reads[i].release == tick)
                source[reads[i].client].insert(source[reads[i].client].end(), read_beats[i].begin(), read_beats[i].end());
        chip.c_req_valid = chip.c_req_channel = 0;
        chip.c_req_record_beats = 0;
        chip.c_rsp_ready = ready(client_stalls, tick, 4095);
        chip.d_req_ready = ready(ddr_stalls, tick, 15);
        for (int c = 0; c < 12; ++c) {
            if (source[c].empty()) continue;
            const auto& beat = beats[source[c].front()];
            int local_beat = beat.local & (c < 9 ? 1 : 31);
            uint64_t base = beat.address - 64 * uint64_t(local_beat);
            chip.c_req_valid |= 1U << c;
            chip.c_req_channel |= ((base >> 11) & 1U) << c;
            chip.c_req_record_beats |= uint64_t(reads[beat.read].length) << (5 * c);
            chip.c_req_tag[c] = beat.local;
            put64(chip.c_req_address, c, beat.address);
        }
        chip.d_rsp_valid = 0;
        for (int lane = 0; lane < 4; ++lane) {
            auto& queue = returns[lane / 2];
            if (!return_valid[lane] && !queue.empty() && queue.front().due <= tick) {
                return_lane[lane] = queue.front();
                queue.pop_front();
                return_valid[lane] = true;
            }
            if (!return_valid[lane]) continue;
            const auto& response = return_lane[lane];
            chip.d_rsp_valid |= 1U << lane;
            put64(chip.d_rsp_tag, lane, response.tag);
            for (int word = 0; word < 16; ++word)
                chip.d_rsp_data[16 * lane + word] = uint32_t(beats[response.beat].address) ^ uint32_t(word);
        }
        chip.eval();
        require(!chip.fault_valid && !chip.p_req_rejected, "typed DMA fault");
        for (int lane = 0; lane < 4; ++lane) {
            if ((chip.d_req_valid >> lane) & 1) {
                const auto tag = get64(chip.d_req_tag, lane);
                const int client = (tag >> 6) & 15;
                const int b = by_address.at({client, get64(chip.d_req_address, lane)});
                auto& beat = beats[b];
                if (beat.offer < 0) beat.offer = tick;
                beat.entry = (tag >> 10) & 63;
                if ((chip.d_req_ready >> lane) & 1) {
                    require(beat.issue < 0, "duplicate DDR issue");
                    beat.issue = tick;
                    returns[lane / 2].push_back({tag, b, tick + latency[lane / 2]});
                }
            }
            if (((chip.d_rsp_ready & chip.d_rsp_valid) >> lane) & 1) {
                auto& beat = beats[return_lane[lane].beat];
                require(beat.captured < 0, "duplicate DDR response capture");
                beat.captured = tick;
                return_valid[lane] = false;
            }
        }
        for (int c = 0; c < 12; ++c) {
            if (((chip.c_rsp_valid & chip.c_rsp_ready) >> c) & 1) {
                auto& beat = beats[by_local.at({c, chip.c_rsp_tag[c]})];
                require(beat.delivered < 0 && beat.captured < tick, "invalid client delivery");
                for (int word = 0; word < 16; ++word)
                    require(chip.c_rsp_data[16 * c + word] == (uint32_t(beat.address) ^ uint32_t(word)),
                            "client received a different physical word");
                beat.delivered = tick;
                ++delivered;
                by_address.erase({c, beat.address});
                by_local.erase({c, beat.local});
            }
            if (((chip.c_req_valid & chip.c_req_ready) >> c) & 1) {
                const int b = source[c].front();
                source[c].pop_front();
                auto& beat = beats[b];
                beat.reserved = tick;
                require(by_address.emplace(std::make_pair(c, beat.address), b).second, "overlapping probe addresses");
                require(by_local.emplace(std::make_pair(c, beat.local), b).second, "duplicate client tag");
            }
        }
        edge(chip);
    }
    require(delivered == beats.size(), "probe timed out");
    for (const auto& b : beats)
        std::cout << b.read << ',' << b.address << ',' << b.entry / 32 << ',' << b.entry % 32 << ','
                  << b.reserved << ',' << b.offer << ',' << b.issue << ',' << b.captured << ',' << b.delivered << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << "FAIL " << error.what() << '\n';
    return 1;
}
