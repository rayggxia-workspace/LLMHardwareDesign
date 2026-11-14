#include "Vp_scope_admission_probe.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>

using Record = std::array<unsigned char, 128>;

static uint32_t field(const Record& record, size_t i) {
    return uint32_t(record[i]) | (uint32_t(record[i+1]) << 8) |
           (uint32_t(record[i+2]) << 16) | (uint32_t(record[i+3]) << 24);
}

int main(int argc, char** argv) {
    if (argc != 4) throw std::runtime_error("expected descriptor file, topology, and starting offset");
    Vp_scope_admission_probe rtl;
    rtl.topology = std::stoul(argv[2]);
    std::ifstream stream(argv[1], std::ios::binary);
    if (!stream) throw std::runtime_error("cannot open descriptor file");
    const auto start = std::stoull(argv[3]);
    if (start % 128 || !stream.seekg(start)) throw std::runtime_error("invalid descriptor offset");
    using Key = std::tuple<uint32_t, bool, unsigned, unsigned>;
    struct Count { uint64_t calls=0, first=0; };
    std::map<Key, Count> counts;
    Record record;
    uint64_t offset = start;
    while (stream.read(reinterpret_cast<char*>(record.data()), record.size())) {
        if (field(record, 0) == 0x02505001 && field(record, 8) == 0x02504d02) {
            for (size_t i = 0; i < rtl.descriptor.size(); ++i) rtl.descriptor[i] = field(record, 4*i);
            rtl.eval();
            auto key = Key{field(record,4)>>16, record[83]==1, field(record,76)&0xffff, rtl.status};
            auto& counter = counts[key];
            if (counter.calls++ == 0) counter.first = offset;
        }
        offset += record.size();
    }
    if (!stream.eof() || stream.gcount()) throw std::runtime_error("truncated descriptor file");
    for (const auto& [key,count] : counts) {
        const auto [opcode,vocab,full_k,status] = key;
        std::cout << opcode << '\t' << vocab << '\t' << full_k << '\t' << status << '\t'
                  << count.calls << '\t' << count.first << '\n';
    }
}
