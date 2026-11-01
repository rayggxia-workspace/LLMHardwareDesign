// Finite, timed SystemC tensor bridge. Parameters are experimental assumptions.
#pragma once
#include "flow.hpp"
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <systemc>
namespace llm {
class TensorLink : public sc_core::sc_module {
  struct Packet {
    uint64_t id = 0;
    std::vector<uint8_t> bytes;
    friend std::ostream &operator<<(std::ostream &o, const Packet &p) {
      return o << p.id;
    }
  };
  static unsigned setting(const char *key, unsigned fallback, unsigned upper) {
    auto p = std::getenv(key);
    unsigned n = p ? unsigned(std::stoul(p)) : fallback;
    if (!n || n > upper)
      throw std::runtime_error(std::string("invalid link setting ") + key);
    return n;
  }
  unsigned width_, capacity_, mtu_, latency_, beat_;
  sc_core::sc_fifo<Packet> requests_, responses_;
  sc_core::sc_mutex mutex_;
  uint64_t next_ = 0;
  void route() {
    while (true) {
      auto p = requests_.read();
      if (p.bytes.size() > mtu_)
        throw std::runtime_error("link packet exceeds finite MTU");
      service_ns += latency_ + ((p.bytes.size() + width_ - 1) / width_) * beat_;
      sc_core::wait(sc_core::sc_time(
          latency_ + ((p.bytes.size() + width_ - 1) / width_) * beat_,
          sc_core::SC_NS));
      if (std::getenv("LLM_LINK_CORRUPT") && !p.bytes.empty())
        p.bytes[0] ^= 1;
      if (!std::getenv("LLM_LINK_DROP_RESPONSE"))
        responses_.write(p);
    }
  }
  template <class U> static void put(std::vector<uint8_t> &out, U value) {
    for (size_t i = 0; i < sizeof(U); ++i)
      out.push_back(uint8_t(uint64_t(value) >> (i * 8)));
  }
  template <class U> static U get(const std::vector<uint8_t> &in, size_t &at) {
    if (at + sizeof(U) > in.size())
      throw std::runtime_error("link truncated tensor");
    uint64_t v = 0;
    for (size_t i = 0; i < sizeof(U); ++i)
      v |= uint64_t(in[at++]) << (i * 8);
    return U(v);
  }

public:
  bool enabled = std::getenv("LLM_LINK") != nullptr;
  uint64_t packets = 0, bytes = 0, tensors = 0, service_ns = 0,
           max_request_slots = 0;
  double lock_wait_ns = 0, request_wait_ns = 0, response_wait_ns = 0;
  SC_HAS_PROCESS(TensorLink);
  explicit TensorLink(sc_core::sc_module_name name)
      : sc_module(name), width_(setting("LLM_LINK_WIDTH_BYTES", 64, 512)),
        capacity_(setting("LLM_LINK_QUEUE_PACKETS", 1, 64)),
        mtu_(setting("LLM_LINK_MTU_BYTES", 256, 4096)),
        latency_(setting("LLM_LINK_LATENCY_NS", 2, 10000)),
        beat_(setting("LLM_LINK_BEAT_NS", 1, 10000)), requests_(int(capacity_)),
        responses_(int(capacity_)) {
    SC_THREAD(route);
  }
  std::vector<uint8_t> exchange(const std::vector<uint8_t> &input) {
    if (!enabled)
      return input;
    auto t = sc_core::sc_time_stamp();
    mutex_.lock();
    lock_wait_ns += (sc_core::sc_time_stamp() - t).to_seconds() * 1e9;
    std::vector<uint8_t> output;
    output.reserve(input.size());
    size_t sent = 0, received = 0;
    std::vector<uint64_t> ids;
    size_t count = (input.size() + mtu_ - 1) / mtu_;
    ids.reserve(count);
    auto send = [&] {
      Packet p;
      p.id = ++next_;
      ids.push_back(p.id);
      auto n = std::min(size_t(mtu_), input.size() - sent);
      p.bytes.assign(input.begin() + sent, input.begin() + sent + n);
      auto start = sc_core::sc_time_stamp();
      requests_.write(p);
      request_wait_ns += (sc_core::sc_time_stamp() - start).to_seconds() * 1e9;
      max_request_slots = std::max(max_request_slots,
                                   uint64_t(capacity_ - requests_.num_free()));
      sent += n;
      ++packets;
      bytes += n;
    };
    // Bounded sliding window; never enqueue a whole tensor into the finite
    // FIFO.
    size_t window = std::min(count, size_t(capacity_) + 1);
    for (size_t i = 0; i < window; ++i)
      send();
    while (received < count) {
      auto start = sc_core::sc_time_stamp();
      auto p = responses_.read();
      response_wait_ns += (sc_core::sc_time_stamp() - start).to_seconds() * 1e9;
      if (p.id != ids.at(received))
        throw std::runtime_error("link packet reorder");
      output.insert(output.end(), p.bytes.begin(), p.bytes.end());
      ++received;
      if (sent < input.size())
        send();
    }
    mutex_.unlock();
    if (output != input)
      throw std::runtime_error("link payload mismatch");
    return output;
  }
  Tensor forward(const Tensor &x) {
    if (!enabled)
      return x;
    std::vector<uint8_t> raw;
    put<uint32_t>(raw, uint32_t(x.v.size()));
    put<int32_t>(raw, x.e);
    put<uint32_t>(raw, uint32_t(x.lane_e.size()));
    for (auto e : x.lane_e)
      put<int32_t>(raw, e);
    for (auto v : x.v)
      put<int16_t>(raw, v);
    auto data = exchange(raw);
    size_t at = 0;
    Tensor out;
    auto n = get<uint32_t>(data, at);
    out.e = get<int32_t>(data, at);
    auto ns = get<uint32_t>(data, at);
    if (ns && ns != n)
      throw std::runtime_error("link scale shape");
    for (size_t i = 0; i < ns; ++i)
      out.lane_e.push_back(get<int32_t>(data, at));
    for (size_t i = 0; i < n; ++i)
      out.v.push_back(get<int16_t>(data, at));
    if (at != data.size())
      throw std::runtime_error("link trailing bytes");
    out.flow_id = x.flow_id;
    out.flow_offset = x.flow_offset;
    ++tensors;
    return out;
  }
  void report(const std::string &directory) {
    std::ofstream f(directory + "/tensor-link.json");
    f << std::setprecision(17)
      << "{\"enabled\":" << (enabled ? "true" : "false")
      << ",\"scope\":\"software-mediated operator tensor boundaries; "
         "weights/raw R state excluded; assumed timing\","
      << "\"width_bytes\":" << width_
      << ",\"queue_packets_each_direction\":" << capacity_
      << ",\"mtu_bytes\":" << mtu_ << ",\"packet_latency_ns\":" << latency_
      << ",\"beat_ns\":" << beat_ << ",\"packets\":" << packets
      << ",\"bytes\":" << bytes << ",\"tensor_transfers\":" << tensors
      << ",\"service_ns\":" << service_ns
      << ",\"max_request_slots\":" << max_request_slots
      << ",\"lock_wait_ns\":" << lock_wait_ns
      << ",\"request_wait_ns\":" << request_wait_ns
      << ",\"response_wait_ns\":" << response_wait_ns
      << ",\"simulated_ns\":" << sc_core::sc_time_stamp().to_seconds() * 1e9
      << "}\n";
    if (!f)
      throw std::runtime_error("link report failed");
  }
};
} // namespace llm
