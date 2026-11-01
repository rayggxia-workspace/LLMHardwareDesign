// Issue162 control ABI v1. These transport fields are physical bit budgets;
// the C++ arrays themselves are not a claim about standard-cell area.
#pragma once
#include <array>
#include <cstdint>
#include <ostream>
namespace control {
constexpr unsigned ProgramWords=256, DescriptorCount=16, EventCount=32, EndpointCount=16;
enum class Op : uint8_t { Nop, Movi, Add, Sub, And, Or, Shift, SetAddr, AddAddr,
    Loop, EndLoop, Branch, DescWrite, Submit, Wait, WaitAll, LoadMeta, Fence, End };
enum class Status : uint8_t { Ok, Illegal, Bounds, Protocol, Remote, Unavailable };
struct Instruction {
    uint64_t bits=0;
    Op op() const { return Op(bits>>56); }
    unsigned rd() const { return (bits>>52)&15; }
    unsigned ra() const { return (bits>>48)&15; }
    unsigned rb() const { return (bits>>44)&15; }
    unsigned flags() const { return (bits>>40)&15; }
    unsigned aux() const { return (bits>>32)&255; }
    uint32_t imm() const { return uint32_t(bits); }
};
inline uint64_t encode(Op op,unsigned rd=0,unsigned ra=0,unsigned rb=0,
                       unsigned flags=0,unsigned aux=0,uint32_t imm=0) {
    return (uint64_t(op)<<56)|(uint64_t(rd&15)<<52)|(uint64_t(ra&15)<<48)|
           (uint64_t(rb&15)<<44)|(uint64_t(flags&15)<<40)|(uint64_t(aux&255)<<32)|imm;
}
struct Task {
    std::array<uint32_t,8> words{};
    unsigned endpoint() const { return (words[0]>>8)&15; }
    unsigned opcode() const { return words[0]&255; }
    uint16_t tag() const { return words[0]>>16; }
    void tag(uint16_t value) { words[0]=(words[0]&65535)|(uint32_t(value)<<16); }
};
inline std::ostream &operator<<(std::ostream& s,const Task& t) {
    return s<<"task(ep="<<t.endpoint()<<",tag="<<t.tag()<<")";
}
struct Completion {
    uint16_t tag=0;
    uint8_t endpoint=0;
    Status status=Status::Ok;
    uint8_t flags=0;
    uint32_t result=0;
    uint64_t pack() const { return uint64_t(tag)|(uint64_t(endpoint&15)<<16)|
        (uint64_t(status)<<20)|(uint64_t(flags)<<24)|(uint64_t(result)<<32); }
};
inline std::ostream &operator<<(std::ostream& s,const Completion& c) { return s<<"done("<<c.tag<<")"; }
enum Endpoint : unsigned { D=0, M=1, N=2, E=3, G=4, S=5, T=6, R=7 };
// DMA descriptor is a separately typed 256-bit payload (not simultaneously a
// compute descriptor). All strides are unsigned positive byte quantities.
struct DmaDescriptor {
    uint64_t external=0; // low40 only
    uint8_t s_instance=0;
    uint16_t s_offset=0; //14 bits, byte address within 16KiB
    uint32_t row_bytes=0; //24 bits
    uint16_t rows=0;
    uint32_t external_stride=0;
    uint16_t s_stride=0;
    bool write=false;
    Status validate() const {
        if (s_instance>=16 || !rows || !row_bytes || row_bytes>=1u<<24 ||
            external>=1ULL<<40 || s_offset>=16384 || (external&15) || (s_offset&15) ||
            external_stride%16 || s_stride%16) return Status::Bounds;
        const uint64_t padded=(uint64_t(row_bytes)+15)&~uint64_t(15);
        if (rows>1 && (external_stride<padded || s_stride<padded)) return Status::Bounds;
        if (external+uint64_t(rows-1)*external_stride+padded>(1ULL<<40) ||
            s_offset+uint64_t(rows-1)*s_stride+padded>16384) return Status::Bounds;
        return Status::Ok;
    }
};
} // namespace control
