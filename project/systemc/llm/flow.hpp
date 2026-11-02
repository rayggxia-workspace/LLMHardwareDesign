// Optional logical dataflow observer; no arithmetic or timing assumptions.
#pragma once
#include <array>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace llm {
struct Tensor {
  std::vector<int16_t> v;
  int e = -10;
  std::vector<int> lane_e{};
  mutable uint64_t flow_id = 0;
  size_t flow_offset = 0;
};
class FlowRecorder {
  struct Value {
    uint64_t producer, birth, last, uses = 0;
    size_t count, scales;
    int exponent;
    std::string label;
  };
  std::map<uint64_t, Value> values_;
  uint64_t next_ = 0;
  std::ofstream events_, controls_;
  std::string directory_;

public:
  unsigned depth = 0, step = 0, layer = 0;
  uint64_t sequence = 0;
  explicit FlowRecorder(const std::string &directory) : directory_(directory) {
    if (!directory.empty()) {
      events_.open(directory + "/flow-events.jsonl");
      controls_.open(directory + "/flow-controls.jsonl");
      if (!events_)
        throw std::runtime_error("flow output directory");
    }
  }
  bool enabled() const { return !directory_.empty(); }
  uint64_t identify(const Tensor &x, uint64_t producer = 0,
                    const std::string &label = "host.external") {
    if (!x.flow_id) {
      x.flow_id = ++next_;
      values_[x.flow_id] = {producer,
                            sequence,
                            sequence,
                            0,
                            x.flow_offset + x.v.size(),
                            x.lane_e.empty() ? 4 : 4 * x.lane_e.size(),
                            x.e,
                            label};
    }
    return x.flow_id;
  }
  uint64_t begin(const std::string &label,
                 const std::vector<const Tensor *> &inputs) {
    uint64_t op = ++sequence;
    events_ << "{\"op\":" << op << ",\"label\":" << std::quoted(label)
            << ",\"step\":" << step << ",\"layer\":" << layer
            << ",\"inputs\":[";
    bool first = true;
    for (const auto *x : inputs) {
      auto id = identify(*x);
      auto &v = values_.at(id);
      v.last = op;
      ++v.uses;
      if (!first)
        events_ << ',';
      first = false;
      events_ << "{\"value\":" << id << ",\"offset\":" << x->flow_offset
              << ",\"count\":" << x->v.size()
              << ",\"payload_bytes\":" << 2 * x->v.size() << ",\"scale_bytes\":"
              << (x->lane_e.empty() ? 4 : 4 * x->lane_e.size()) << '}';
    }
    events_ << ']';
    return op;
  }
  void end(uint64_t op, const std::string &label, Tensor *out,
           const std::array<uint64_t, 7> &delta, uint64_t weights,
           uint64_t state) {
    if (out) {
      out->flow_id = 0;
      out->flow_offset = 0;
      events_ << ",\"output\":" << identify(*out, op, label);
    }
    events_ << ",\"macro_transactions\":[";
    for (size_t i = 0; i < delta.size(); ++i) {
      if (i)
        events_ << ',';
      events_ << delta[i];
    }
    events_ << "],\"weight_logical_read_bytes\":" << weights
            << ",\"host_state_io_bytes\":" << state << "}\n";
    if (!events_)
      throw std::runtime_error("flow write failed");
  }
  void control(const std::string &name, const std::vector<unsigned> &ids) {
    if (!enabled())
      return;
    controls_ << "{\"after_op\":" << sequence << ",\"step\":" << step
              << ",\"layer\":" << layer << ",\"name\":" << std::quoted(name)
              << ",\"ids\":[";
    for (size_t i = 0; i < ids.size(); ++i) {
      if (i)
        controls_ << ',';
      controls_ << ids[i];
    }
    controls_ << "]}\n";
    if (!controls_)
      throw std::runtime_error("flow control write");
  }
  void finish() {
    if (!enabled())
      return;
    events_.flush();
    controls_.flush();
    std::ofstream f(directory_ + "/flow-values.csv");
    f << "id,producer,birth,last_use,uses,elements,payload_bytes,scale_bytes,"
         "exponent,label\n";
    for (const auto &entry : values_) {
      const auto &v = entry.second;
      f << entry.first << ',' << v.producer << ',' << v.birth << ',' << v.last
        << ',' << v.uses << ',' << v.count << ',' << v.count * 2 << ','
        << v.scales << ',' << v.exponent << ',' << v.label << '\n';
    }
    if (!f || !events_)
      throw std::runtime_error("flow finish failed");
  }
};
} // namespace llm
