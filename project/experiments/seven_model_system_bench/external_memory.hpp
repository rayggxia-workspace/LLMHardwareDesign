#pragma once

#include "flow.hpp"
#include <systemc>
#include <tlm>
#include <tlm_utils/simple_initiator_socket.h>
#include <tlm_utils/simple_target_socket.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <utility>

namespace llm {
enum class MemoryKind : unsigned { Weight, KV, RState, RHistory };
constexpr std::array<const char *, 4> memory_names{"weights", "kv", "r_state", "r_history"};
constexpr uint64_t gib = 1ULL << 30;
constexpr std::array<uint64_t, 4> memory_base{0, 16 * gib, 17 * gib, 18 * gib};
constexpr std::array<uint64_t, 4> memory_capacity{16 * gib, gib, gib, gib};
constexpr unsigned bus_word = 16, burst_bytes = 256, page_bytes = 4096;

inline unsigned memory_index(MemoryKind kind) { return static_cast<unsigned>(kind); }

struct Traffic {
  uint64_t payload = 0, bus = 0, bursts = 0;
};

class BehavioralDram : public sc_core::sc_module {
  std::vector<int16_t> checkpoint_;
  std::array<std::vector<unsigned char>, 3> mutable_regions_;

  void transport(tlm::tlm_generic_payload &packet, sc_core::sc_time &) {
    const uint64_t address = packet.get_address();
    const unsigned count = packet.get_data_length();
    if ((!packet.is_read() && !packet.is_write()) || !packet.get_data_ptr() ||
        !count || address >= 19 * gib || packet.get_byte_enable_ptr() ||
        packet.get_streaming_width() != count ||
        count > burst_bytes - address % bus_word ||
        count > page_bytes - address % page_bytes) {
      packet.set_response_status(tlm::TLM_BURST_ERROR_RESPONSE);
      return;
    }
    const unsigned index = address < memory_base[1] ? 0 : 1 + unsigned((address - memory_base[1]) / gib);
    const uint64_t offset = address - memory_base[index];
    unsigned char *storage;
    uint64_t extent;
    if (index == 0) {
      if (packet.is_write()) {
        packet.set_response_status(tlm::TLM_COMMAND_ERROR_RESPONSE);
        return;
      }
      storage = reinterpret_cast<unsigned char *>(checkpoint_.data());
      extent = checkpoint_.size() * sizeof(int16_t);
    } else {
      auto &region = mutable_regions_[index - 1];
      storage = region.data();
      extent = region.size();
    }
    if (offset > extent || count > extent - offset) {
      packet.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
      return;
    }
    if (packet.is_write())
      std::memcpy(storage + offset, packet.get_data_ptr(), count);
    else
      std::memcpy(packet.get_data_ptr(), storage + offset, count);

    // Count only accepted and completed data. Bus bytes include leading/trailing
    // partial beats; payload bytes count only requested/valid byte lanes.
    auto &counter = completed[index][packet.is_write()];
    counter.payload += count;
    counter.bus += (address % bus_word + count + bus_word - 1) / bus_word * bus_word;
    ++counter.bursts;
    packet.set_response_status(tlm::TLM_OK_RESPONSE);
  }

public:
  tlm_utils::simple_target_socket<BehavioralDram, 128> socket{"socket"};
  std::array<std::array<Traffic, 2>, 4> completed{};

  explicit BehavioralDram(sc_core::sc_module_name name) : sc_module(name) {
    socket.register_b_transport(this, &BehavioralDram::transport);
  }

  void boot(std::vector<int16_t> checkpoint) {
    if (checkpoint.size() > memory_capacity[0] / sizeof(int16_t))
      throw std::runtime_error("checkpoint exceeds memory region");
    checkpoint_ = std::move(checkpoint);
  }

  uint64_t reserve(MemoryKind kind, uint64_t bytes) {
    const unsigned index = memory_index(kind);
    if (!index || !bytes)
      throw std::runtime_error("invalid mutable allocation");
    auto &region = mutable_regions_[index - 1];
    const uint64_t offset = (region.size() + bus_word - 1) / bus_word * bus_word;
    if (offset > memory_capacity[index] || bytes > memory_capacity[index] - offset)
      throw std::runtime_error("mutable memory region full");
    region.resize(offset + bytes);
    return offset;
  }
};

class Offchip : public sc_core::sc_module {
  tlm_utils::simple_initiator_socket<Offchip, 128> socket_{"controller"};
  BehavioralDram dram_{"dram"};
  std::array<std::array<uint64_t, 2>, 4> requested_{}, calls_{};

  void access(MemoryKind kind, uint64_t offset, void *data, size_t bytes, bool write) {
    const unsigned index = memory_index(kind);
    if (!bytes || offset > memory_capacity[index] || bytes > memory_capacity[index] - offset)
      throw std::runtime_error("external request outside region");
    requested_[index][write] += bytes;
    ++calls_[index][write];
    auto *cursor = static_cast<unsigned char *>(data);
    uint64_t address = memory_base[index] + offset;
    tlm::tlm_generic_payload packet;
    packet.set_command(write ? tlm::TLM_WRITE_COMMAND : tlm::TLM_READ_COMMAND);
    auto delay = sc_core::SC_ZERO_TIME;
    while (bytes) {
      const unsigned n = unsigned(std::min({uint64_t(bytes),
                                             burst_bytes - address % bus_word,
                                             page_bytes - address % page_bytes}));
      packet.set_address(address);
      packet.set_data_ptr(cursor);
      packet.set_data_length(n);
      packet.set_streaming_width(n);
      packet.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
      socket_->b_transport(packet, delay);
      if (packet.get_response_status() != tlm::TLM_OK_RESPONSE)
        throw std::runtime_error("external burst failed");
      address += n;
      cursor += n;
      bytes -= n;
    }
  }

public:
  explicit Offchip(sc_core::sc_module_name name) : sc_module(name) {
    socket_.bind(dram_.socket);
  }

  void boot(std::vector<int16_t> checkpoint) { dram_.boot(std::move(checkpoint)); }
  uint64_t reserve(MemoryKind kind, uint64_t bytes) { return dram_.reserve(kind, bytes); }

  void read(MemoryKind kind, uint64_t offset, void *data, size_t bytes) {
    access(kind, offset, data, bytes, false);
  }
  void write(MemoryKind kind, uint64_t offset, const void *data, size_t bytes) {
    // TLM generic payload uses a mutable pointer for both commands.
    access(kind, offset, const_cast<void *>(data), bytes, true);
  }

  void report(std::ostream &out, unsigned position, const char *phase) const {
    for (unsigned index = 0; index < memory_names.size(); ++index) {
      for (unsigned write = 0; write < 2; ++write) {
        const auto &retired = dram_.completed[index][write];
        if (retired.payload != requested_[index][write])
          throw std::runtime_error("external request/completion byte mismatch");
        out << position << ',' << phase << ',' << memory_names[index] << ','
            << (write ? "write" : "read") << ',' << calls_[index][write] << ','
            << retired.bursts << ',' << retired.payload << ',' << retired.bus << '\n';
      }
    }
    if (!out)
      throw std::runtime_error("cannot write external memory receipt");
  }
};

// A mutable tensor slot stores the exponent, S16 elements and optional per-lane
// exponents in the device. Shape and allocation metadata live in the controller.
class TensorSlot {
  uint64_t offset_ = 0;
  size_t count_ = 0;
  bool lanes_ = false;

public:
  void write(Offchip &memory, MemoryKind kind, const Tensor &value) {
    static_assert(sizeof(int) == sizeof(int32_t), "tensor exponent width");
    const size_t count = value.v.size();
    if (!count || (count_ && count != count_) ||
        (!value.lane_e.empty() && value.lane_e.size() != count))
      throw std::runtime_error("external tensor shape");
    if (!count_)
      offset_ = memory.reserve(kind, sizeof(int32_t) + count * 6);
    count_ = count;
    lanes_ = !value.lane_e.empty();
    // Contiguous serialized record; use a single logical request for the append.
    std::vector<unsigned char> bytes(sizeof(int32_t) + count * (lanes_ ? 6 : 2));
    std::memcpy(bytes.data(), &value.e, sizeof(int32_t));
    std::memcpy(bytes.data() + sizeof(int32_t), value.v.data(), count * 2);
    if (lanes_)
      std::memcpy(bytes.data() + sizeof(int32_t) + count * 2, value.lane_e.data(), count * 4);
    memory.write(kind, offset_, bytes.data(), bytes.size());
  }

  Tensor read(Offchip &memory, MemoryKind kind, size_t first, size_t count) const {
    if (!count || first > count_ || count > count_ - first)
      throw std::runtime_error("external tensor slice");
    Tensor result;
    result.v.resize(count);
    if (first == 0 && count == count_) {
      std::vector<unsigned char> bytes(sizeof(int32_t) + count * (lanes_ ? 6 : 2));
      memory.read(kind, offset_, bytes.data(), bytes.size());
      std::memcpy(&result.e, bytes.data(), sizeof(int32_t));
      std::memcpy(result.v.data(), bytes.data() + sizeof(int32_t), count * 2);
      if (lanes_) {
        result.lane_e.resize(count);
        std::memcpy(result.lane_e.data(), bytes.data() + sizeof(int32_t) + count * 2, count * 4);
      }
    } else {
      memory.read(kind, offset_, &result.e, sizeof(int32_t));
      memory.read(kind, offset_ + sizeof(int32_t) + first * 2, result.v.data(), count * 2);
      if (lanes_) {
        result.lane_e.resize(count);
        memory.read(kind, offset_ + sizeof(int32_t) + count_ * 2 + first * 4,
                    result.lane_e.data(), count * 4);
      }
    }
    return result;
  }

  Tensor read(Offchip &memory, MemoryKind kind) const { return read(memory, kind, 0, count_); }
};
} // namespace llm
