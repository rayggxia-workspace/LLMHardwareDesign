// Transaction-level consumer of the same MC/LC images as the P16 RTL test.
#include <systemc>
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using sc_core::SC_NS;
using sc_core::SC_ZERO_TIME;
using sc_core::sc_event;
using sc_core::sc_time;
using sc_core::wait;
using Word = std::uint32_t;

template <class T> std::vector<T> image(const std::string& file, std::size_t count) {
    std::ifstream stream(file);
    std::vector<T> result;
    std::string line;
    while (stream >> line) result.push_back(static_cast<T>(std::stoull(line, nullptr, 16)));
    if (result.size() != count) throw std::runtime_error("wrong word count: " + file);
    return result;
}

int byte(const std::array<std::uint64_t, 2>& word, int offset) {
    int v = (word[offset / 8] >> (8 * (offset % 8))) & 255;
    return v < 128 ? v : v - 256;
}

Word pack(int a, int b) {
    return (std::uint32_t(a) & 65535) | ((std::uint32_t(b) & 65535) << 16);
}

int lane(Word word, int i) {
    int v = (word >> (16 * i)) & 65535;
    return v < 32768 ? v : v - 65536;
}

int rne(std::int64_t value, int shift) {
    const std::int64_t scale = 1 << shift;
    const auto magnitude = value < 0 ? -value : value;
    const auto q = magnitude / scale;
    const auto r = magnitude % scale;
    const auto rounded = q + (2 * r > scale || (2 * r == scale && q % 2));
    return value < 0 ? -rounded : rounded;
}

Word projection(const std::string& path) {
    std::ifstream file(path);
    std::array<std::int64_t, 2> sums{};
    for (int k = 0; k < 80; ++k) {
        std::array<std::array<std::uint64_t, 2>, 32> scratch{};
        for (auto& word : scratch) {
            std::string line;
            if (!(file >> line) || line.size() != 32) throw std::runtime_error("invalid operand stream");
            word[0] = std::stoull(line.substr(16), nullptr, 16);
            word[1] = std::stoull(line.substr(0, 16), nullptr, 16);
        }
        for (int tile = 0; tile < 4; ++tile)
            for (int n = 0; n < 2; ++n)
                for (int i = 0; i < 8; ++i)
                    sums[n] += byte(scratch[4 * tile], i) * byte(scratch[16 + 4 * tile], 8 * n + i);
    }
    return pack(std::clamp(rne(sums[0], 2), -32768, 32767),
                std::clamp(rne(sums[1], 2), -32768, 32767));
}

int gate_lane(int x, int u) {
    auto table = [](int i) {
        double t = (i * 32 - 8192) / 1024.0;
        return int(std::nearbyint(1024 * t / (1 + std::exp(-t))));
    };
    int f = 0;
    if (x > 8192) f = x;
    else if (x >= -8192) {
        const int i = (x + 8192) / 32;
        const int low = table(i);
        f = low + rne((table(std::min(i + 1, 512)) - low) * ((x + 8192) % 32), 5);
    }
    return std::clamp(rne(std::int64_t(f) * u, 10), -32768, 32767);
}

struct Trial : sc_core::sc_module {
    SC_HAS_PROCESS(Trial);
    std::array<std::array<Word, 1024>, 2> s{};
    std::array<bool, 4> done{};
    std::array<int, 2> entry{-1, -1};
    std::array<std::vector<std::uint64_t>, 2> lc;
    std::vector<std::uint64_t> mc;
    std::vector<Word> expected;
    std::array<Word, 2> numeric;
    sc_event changed;
    bool reserved = false;
    bool passed = false;
    int stall;

    Trial(sc_core::sc_module_name name, const std::string& operands, const std::string& images, int stall)
        : sc_module(name), lc{image<std::uint64_t>(images+"/lc0.hex", 12),
                              image<std::uint64_t>(images+"/lc1.hex", 12)},
          mc(image<std::uint64_t>(images+"/mc.hex", 8)),
          expected(image<Word>(operands+"/expected.hex", 3)),
          numeric{projection(operands+"/gate.hex"), projection(operands+"/up.hex")},
          stall(stall) {
        SC_THREAD(mother);
        SC_THREAD(local0);
        SC_THREAD(local1);
    }

    void need(bool valid, const char* why) {
        if (!valid) throw std::runtime_error(why);
    }

    void trace(const std::string& name, Word data) {
        std::cout << "TRACE " << name << ' ' << std::hex << std::setw(32)
                  << std::setfill('0') << data << std::dec << '\n';
    }

    void local0() { local(0); }
    void local1() { local(1); }

    void local(int block) {
        while (true) {
            while (entry[block] < 0) wait(changed);
            const int start = 4 * entry[block];
            bool end = false;
            for (int pc = start; pc < start + 4 && !end; ++pc) {
                const auto w = lc[block][pc];
                int a = (w >> 20) & 1023, b = (w >> 10) & 1023, c = w & 1023;
                switch (w >> 30) {
                case 0: end = true; break;
                case 4:
                    need(a <= 1 && c == a && b == 32+a && (block == 0 || a == 1), "bad project");
                    wait(sc_time(22600, SC_NS));
                    s[block][b] = numeric[a];
                    need(numeric[a] == expected[a], "projection mismatch");
                    trace("projection " + std::to_string(a), numeric[a]);
                    done[c] = true;
                    break;
                case 5: {
                    need(block == 1 && a == 33 && b == 33 && reserved && done[1], "bad copy");
                    const auto payload = s[1][a];
                    std::cout << "TRACE up_in_flight\n";
                    wait(sc_time(20 + stall, SC_NS));
                    s[0][b] = payload;
                    std::cout << "TRACE up_rx_stored\n";
                    done[2] = true;
                    reserved = false;
                    std::cout << "TRACE up_source_release\n";
                    break;
                }
                case 6:
                    need(block == 0 && a == 32 && b == 33 && c == 34 && done[0] && done[1]
                         && !reserved, "bad gate");
                    wait(sc_time(20, SC_NS));
                    s[0][c] = pack(gate_lane(lane(s[0][a], 0), lane(s[0][b], 0)),
                                   gate_lane(lane(s[0][a], 1), lane(s[0][b], 1)));
                    need(s[0][c] == expected[2], "mid mismatch");
                    trace("mid_stored", s[0][c]);
                    done[3] = true;
                    break;
                default: need(false, "unknown local opcode");
                }
                changed.notify(SC_ZERO_TIME);
            }
            need(end, "unterminated LC entry");
            entry[block] = -1;
            changed.notify(SC_ZERO_TIME);
        }
    }

    void mother() {
        for (const auto w : mc) {
            int a = (w >> 20) & 1023, b = (w >> 10) & 1023;
            switch (w >> 30) {
            case 0:
                need(done[3] && !reserved, "premature MC end");
                while (entry[0] >= 0 || entry[1] >= 0) wait(changed);
                passed = true;
                sc_core::sc_stop();
                return;
            case 1:
                need(a < 2 && b < 3, "invalid call");
                while (entry[a] >= 0) wait(changed);
                entry[a] = b;
                changed.notify(SC_ZERO_TIME);
                break;
            case 2:
                need(a < 4, "invalid event");
                while (!done[a]) wait(changed);
                break;
            case 3:
                need(a == 0 && b == 33 && !reserved, "invalid reservation");
                reserved = true;
                break;
            default: need(false, "unknown mother opcode");
            }
        }
        need(false, "unterminated MC image");
    }
};

int sc_main(int argc, char** argv) {
    if (argc != 4) return 2;
    Trial trial("ffn", argv[1], argv[2], std::stoi(argv[3]));
    sc_core::sc_start(sc_time(1000000, SC_NS));
    if (!trial.passed) return 1;
    std::cout << "PASS SystemC FFN image\n";
    return 0;
}
