// R integration uses the unchanged finite R engine. External state is simulated
// DRAM.
#pragma once
#include "runtime.hpp"
namespace llm {
inline Tensor subvector(const Tensor &x, size_t first, size_t count) {
  if (first + count > x.v.size())
    throw std::runtime_error("recurrent slice");
  return {{x.v.begin() + first, x.v.begin() + first + count}, x.e};
}
struct RecurrentCache {
  std::vector<Tensor> history;
  std::vector<int32_t> state;
  int exponent = 0;
};
class Recurrent {
  Runtime &rt;

public:
  // Explicit software boundary format service: R S32 <-> E/M S16.
  // It does not compute dot products, state updates, normalization or
  // activation.
  uint64_t software_boundary_values = 0;
  explicit Recurrent(Runtime &runtime) : rt(runtime) {}
  Tensor narrow(const std::vector<int32_t> &values, int exponent) {
    uint64_t peak = 0;
    for (auto v : values)
      peak = std::max(peak, uint64_t(std::llabs(int64_t(v))));
    unsigned shift = Runtime::output_shift(peak);
    Tensor y;
    y.e = exponent + int(shift);
    for (auto v : values)
      y.v.push_back(int16_t(rne(Wide(v), shift)));
    software_boundary_values += values.size();
    return y;
  }
  static int32_t widen(int16_t value, int source, int destination) {
    int delta = source - destination;
    Wide v = value;
    if (delta >= 0) {
      if (delta > 31)
        throw std::runtime_error("R widening scale");
      v *= power(unsigned(delta));
    } else
      v = rne(v, unsigned(-delta));
    if (!fits(v, 32))
      throw std::runtime_error("R boundary S32 overflow");
    return int32_t(v);
  }
  Tensor convolution(const Tensor &x, const Checkpoint &cp,
                     const std::string &root, RecurrentCache &cache,
                     unsigned step) {
    auto w = cp.index.at(root + "conv1d.weight");
    if (w.cols != 4 || w.rows != x.v.size())
      throw std::runtime_error("conv4 shape");
    int xe = x.e;
    for (auto &h : cache.history)
      xe = std::max(xe, h.e);
    auto current = rt.scale(x, xe);
    std::vector<Tensor> past;
    for (auto &h : cache.history)
      past.push_back(rt.scale(h, xe));
    std::vector<int32_t> out(x.v.size());
    for (size_t base = 0; base < x.v.size(); base += 8) {
      RCommand c;
      c.op = RCommand::Op::Open;
      c.owner = uint32_t(base);
      c.position = step;
      rt.r.call(c);
      for (unsigned t = 0; t < 3; ++t) {
        c = RCommand{};
        c.op = RCommand::Op::History;
        c.index = t;
        for (unsigned j = 0; j < 8 && base + j < x.v.size(); ++j)
          c.values[j] = t < past.size() ? past[t].v[base + j] : 0;
        rt.r.call(c);
      }
      for (unsigned t = 0; t < 4; ++t) {
        c = RCommand{};
        c.op = RCommand::Op::Taps;
        c.index = t;
        for (unsigned j = 0; j < 8 && base + j < x.v.size(); ++j)
          c.coefficients[j] = cp.data(w)[(base + j) * 4 + 3 - t];
        rt.r.call(c);
      }
      c = RCommand{};
      c.op = RCommand::Op::X;
      for (unsigned j = 0; j < 8 && base + j < x.v.size(); ++j)
        c.values[j] = current.v[base + j];
      rt.r.call(c);
      c = RCommand{};
      c.op = RCommand::Op::Execute;
      c.mode = RCommand::Mode::Conv4;
      c.owner = uint32_t(base);
      c.position = step;
      rt.r.call(c);
      c.op = RCommand::Op::ReadOutput;
      auto response = rt.r.call(c);
      for (unsigned j = 0; j < 8 && base + j < x.v.size(); ++j)
        out[base + j] = int32_t(response.lane[j]);
      c.op = RCommand::Op::Commit;
      c.next_position = step + 1;
      rt.r.call(c);
    }
    cache.history.insert(cache.history.begin(), x);
    if (cache.history.size() > 3)
      cache.history.pop_back();
    auto result = narrow(out, xe + w.e + 14);
    if (cp.index.count(root + "conv1d.bias"))
      result = rt.add(result, cp.vector(root + "conv1d.bias"));
    return rt.silu(result);
  }
  std::vector<uint32_t> decay(const Tensor &negative) {
    auto fixed = rt.scale(negative, -10);
    std::vector<uint32_t> out;
    for (auto v : fixed.v) {
      if (v > 0)
        throw std::runtime_error("positive state log decay");
      NCommand c;
      c.op = NCommand::Op::Begin;
      rt.n.call(c);
      c.op = NCommand::Op::Stats;
      c.count = 2;
      c.data[0] = 0;
      c.data[1] = uint16_t(v);
      rt.n.call(c);
      c.op = NCommand::Op::Finalize;
      rt.n.call(c);
      c.op = NCommand::Op::Exp;
      auto response = rt.n.call(c);
      out.push_back(uint32_t(response.lane[1]) << 16);
    }
    return out;
  }
  void prepare_state(RecurrentCache &cache, unsigned heads, unsigned rows,
                     unsigned width, const Tensor &value) {
    int target = value.e - 8;
    if (cache.state.empty()) {
      cache.state.assign(size_t(heads) * rows * width, 0);
      cache.exponent = target;
    }
    if (cache.state.size() != size_t(heads) * rows * width)
      throw std::runtime_error("state extent");
    if (target > cache.exponent) {
      for (auto &v : cache.state)
        v = int32_t(rne(Wide(v), unsigned(target - cache.exponent)));
      software_boundary_values += cache.state.size();
      cache.exponent = target;
    }
  }
  Tensor update(RecurrentCache &cache, const Tensor &key, const Tensor &query,
                const Tensor &value, const Tensor &injection,
                const Tensor &skip, const std::vector<uint32_t> &alpha,
                const std::vector<uint32_t> &beta, unsigned heads,
                unsigned rows, unsigned width, unsigned step, bool ssm) {
    if (rows > 256 || width % 8 || key.v.size() != size_t(heads) * rows ||
        query.v.size() != key.v.size() ||
        value.v.size() != size_t(heads) * width)
      throw std::runtime_error("R matrix mapping");
    // GDN Q/K are normalized; SSM B/C are unbounded projections. Scale the
    // latter into Q1.14 and compensate injection/output/skip in real units.
    int bs =
        ssm ? std::max(0, Runtime::bits(Runtime::peak(key)) + key.e - 1) : 0;
    int cs =
        ssm ? std::max(0, Runtime::bits(Runtime::peak(query)) + query.e - 1)
            : 0;
    Tensor bounded_key = key, bounded_query = query, injected = injection;
    bounded_key.e -= bs;
    bounded_query.e -= cs;
    injected.e += bs;
    Tensor state_range = value;
    if (ssm && injected.e > state_range.e)
      state_range = injected;
    prepare_state(cache, heads, rows, width, state_range);
    auto kk = rt.scale(bounded_key, -14), qq = rt.scale(bounded_query, -14);
    std::vector<int32_t> output(size_t(heads) * width);
    for (unsigned h = 0; h < heads; ++h)
      for (unsigned base = 0; base < width; base += 8) {
        RCommand c;
        c.op = RCommand::Op::Open;
        c.length = rows;
        c.owner = h * width + base;
        c.position = step;
        rt.r.call(c);
        for (unsigned row = 0; row < rows; ++row) {
          c = RCommand{};
          c.op = RCommand::Op::StateRow;
          c.index = row;
          for (unsigned j = 0; j < 8; ++j)
            c.values[j] =
                cache.state[(size_t(h) * rows + row) * width + base + j];
          rt.r.call(c);
          if (ssm) {
            c.op = RCommand::Op::DecayRow;
            c.factors.fill(alpha.at(h));
            rt.r.call(c);
          }
          c = RCommand{};
          c.op = RCommand::Op::Key;
          c.index = row;
          c.coefficients[0] = kk.v[h * rows + row];
          rt.r.call(c);
          c.op = RCommand::Op::Query;
          c.coefficients[0] = qq.v[h * rows + row];
          rt.r.call(c);
        }
        c = RCommand{};
        c.op = RCommand::Op::Parameters;
        c.decay = alpha.at(h);
        c.beta = ssm ? 0 : beta.at(h);
        rt.r.call(c);
        c = RCommand{};
        c.op = RCommand::Op::X;
        for (unsigned j = 0; j < 8; ++j)
          c.values[j] =
              widen(value.v[h * width + base + j], value.e, cache.exponent);
        rt.r.call(c);
        if (ssm) {
          c = RCommand{};
          c.op = RCommand::Op::Inject;
          for (unsigned j = 0; j < 8; ++j)
            c.values[j] = widen(injected.v[h * width + base + j], injected.e,
                                cache.exponent);
          rt.r.call(c);
          c = RCommand{};
          c.op = RCommand::Op::Skip;
          for (unsigned j = 0; j < 8; ++j)
            c.values[j] = widen(skip.v[h * width + base + j], skip.e - cs, -16);
          rt.r.call(c);
        }
        c = RCommand{};
        c.op = RCommand::Op::Execute;
        c.mode = ssm ? RCommand::Mode::SSM : RCommand::Mode::GDN;
        c.owner = h * width + base;
        c.position = step;
        rt.r.call(c);
        c.op = RCommand::Op::ReadOutput;
        auto response = rt.r.call(c);
        for (unsigned j = 0; j < 8; ++j)
          output[h * width + base + j] = int32_t(response.lane[j]);
        c.op = RCommand::Op::Commit;
        c.next_position = step + 1;
        rt.r.call(c);
        for (unsigned row = 0; row < rows; ++row) {
          c = RCommand{};
          c.op = RCommand::Op::ReadState;
          c.index = row;
          response = rt.r.call(c);
          for (unsigned j = 0; j < 8; ++j)
            cache.state[(size_t(h) * rows + row) * width + base + j] =
                int32_t(response.lane[j]);
        }
      }
    software_boundary_values += value.v.size() + (ssm ? injection.v.size() : 0);
    return narrow(output, cache.exponent + cs);
  }
};
} // namespace llm
