// LLM事务级控制器。仅模拟外存、寻址和尺度调度；算术由既有宏命令完成。
#pragma once
#include "blocks/modules.hpp"
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace llm {
using namespace blocks;
inline void put_halfword(Line &w, unsigned i, uint16_t value) {
  w[i / 4] |= uint64_t(value) << (16 * (i % 4));
}
struct Tensor {
  std::vector<int16_t> v;
  int e = -10;
}; // value = raw * 2^e
struct Weight {
  size_t rows = 0, cols = 0, offset = 0;
  int e = 0;
};
// 外存检查点；不是把权重装进16KiB S。文件导出为little endian S16。
struct Checkpoint {
  std::map<std::string, Weight> index;
  std::map<std::string, std::vector<int>> group_scales;
  std::vector<int16_t> memory;
  std::map<std::string, std::string> meta;
  std::vector<int> prompt;
  explicit Checkpoint(const std::string &dir) {
    std::ifstream f(dir + "/weights.index");
    std::string name;
    Weight w;
    if (!f)
      throw std::runtime_error("missing weight index");
    while (f >> name >> w.rows >> w.cols >> w.e >> w.offset)
      index[name] = w;
    std::ifstream sf(dir + "/weights.scales");
    std::string line;
    while (std::getline(sf, line)) {
      if (line.empty())
        continue;
      std::istringstream row(line);
      size_t count;
      if (!(row >> name >> count) || !index.count(name) ||
          count != (index.at(name).rows + 7) / 8 || group_scales.count(name))
        throw std::runtime_error("weight group scale shape");
      std::vector<int> exponents(count);
      for (auto &e : exponents)
        if (!(row >> e) || e < -128 || e > 128)
          throw std::runtime_error("weight group exponent");
      std::string extra;
      if (row >> extra)
        throw std::runtime_error("weight group scale trailing fields");
      group_scales.emplace(name, std::move(exponents));
    }
    std::ifstream b(dir + "/weights.bin", std::ios::binary | std::ios::ate);
    if (!b)
      throw std::runtime_error("missing weight bytes");
    auto bytes = b.tellg();
    memory.resize(size_t(bytes) / 2);
    b.seekg(0);
    b.read(reinterpret_cast<char *>(memory.data()), bytes);
    for (const auto &p : index)
      if (p.second.offset / 2 + p.second.rows * p.second.cols > memory.size())
        throw std::runtime_error("weight extent");
    std::ifstream m(dir + "/metadata.txt");
    std::string value;
    while (m >> name >> value)
      meta[name] = value;
    if (meta.count("weight_group_rows") &&
        (meta.at("weight_group_rows") != "8" || group_scales.empty()))
      throw std::runtime_error("missing or unsupported weight group scales");
    std::ifstream t(dir + "/prompt.txt");
    int id;
    while (t >> id)
      prompt.push_back(id);
    if (prompt.empty() || index.empty())
      throw std::runtime_error("empty checkpoint");
  }
  int number(const std::string &k) const { return std::stoi(meta.at(k)); }
  const int16_t *data(const Weight &w) const {
    return memory.data() + w.offset / 2;
  }
  const std::vector<int> *scales(const std::string &name) const {
    auto it = group_scales.find(name);
    return it == group_scales.end() ? nullptr : &it->second;
  }
  int row_exponent(const std::string &name, size_t row) const {
    if (row >= index.at(name).rows)
      throw std::runtime_error("weight row");
    auto s = scales(name);
    return s ? s->at(row / 8) : index.at(name).e;
  }
  Tensor vector(const std::string &name) const {
    if (scales(name))
      throw std::runtime_error("grouped matrix requires row or M access");
    const auto &w = index.at(name);
    return {{data(w), data(w) + w.rows * w.cols}, w.e};
  }
};
// 每个端口连接真实SC_THREAD模块，深度1的双向FIFO。没有直接访问引擎状态。
template <class Engine> struct Port {
  Module<Engine> module;
  sc_core::sc_fifo<typename Engine::Command> commands;
  sc_core::sc_fifo<Reply> replies;
  uint64_t transactions = 0, saturations = 0;
  std::map<int, uint64_t> saturation_ops;
  explicit Port(const char *name) : module(name), commands(1), replies(1) {
    module.commands(commands);
    module.responses(replies);
  }
  Reply call(const typename Engine::Command &c) {
    commands.write(c);
    auto r = replies.read();
    ++transactions;
    saturations += r.saturated;
    if (r.saturated)
      ++saturation_ops[int(c.op)];
    if (r.error)
      throw std::runtime_error(
          std::string(module.name()) +
          " command rejected op=" + std::to_string(int(c.op)));
    return r;
  }
};
// GCommand采用function命名，不具有op；专用端口保留同样的FIFO合同。
template <> inline Reply Port<GEngine>::call(const GCommand &c) {
  commands.write(c);
  auto r = replies.read();
  ++transactions;
  saturations += r.saturated;
  if (r.error)
    throw std::runtime_error("G rejected");
  return r;
}
class Runtime {
public:
  Port<MEngine> m{"M"};
  Port<NEngine> n{"N"};
  Port<EEngine> e{"E"};
  Port<GEngine> g{"G"};
  Port<REngine> r{"R"};
  Port<SEngine> s{"S"};
  Port<TEngine> t{"T"};
  uint64_t scale_decisions = 0, matmuls = 0, macs = 0;
  // 这些abs/max/bit_length是显式软件数值控制，尚未映射为硬件控制器。
  static uint64_t peak(const Tensor &x) {
    uint64_t p = 0;
    for (auto a : x.v)
      p = std::max(p, uint64_t(std::abs(int(a))));
    return p;
  }
  static int bits(uint64_t x) {
    int b = 0;
    while (x) {
      ++b;
      x >>= 1;
    }
    return b;
  }
  static bool precise() {
    return std::getenv("LLM_PRECISE_ADAPTER") != nullptr;
  }
  static unsigned output_shift(uint64_t p) {
    unsigned shift = unsigned(std::max(0, bits(p) - (precise() ? 15 : 14)));
    while (precise() && rne(Wide(p), shift) > 32767)
      ++shift;
    return shift;
  }
  Tensor scale(const Tensor &x, int exponent) {
    Tensor out = x;
    out.e = exponent;
    int d = exponent - x.e;
    for (size_t i = 0; i < x.v.size(); i += 8) {
      ECommand c;
      c.op = d >= 0 ? ECommand::Op::RoundRight : ECommand::Op::Left;
      c.shift = unsigned(std::min(31, std::abs(d)));
      for (size_t j = 0; j < 8 && i + j < x.v.size(); ++j)
        c.a[j] = x.v[i + j];
      auto q = e.call(c);
      for (size_t j = 0; j < 8 && i + j < x.v.size(); ++j)
        out.v[i + j] = int16_t(q.lane[j]);
    }
    return out;
  }
  Tensor compact(const Tensor &x) {
    ++scale_decisions;
    auto p = peak(x);
    if (!p)
      return x;
    int left = std::max(0, (precise() ? 15 : 14) - bits(p));
    return left ? scale(x, x.e - left) : x;
  }
  Tensor add(const Tensor &a, const Tensor &b) {
    if (a.v.size() != b.v.size())
      throw std::runtime_error("add shape");
    if (precise())
      return add_full(a, b);
    int exponent = std::max(a.e, b.e) + 1;
    auto aa = scale(a, exponent), bb = scale(b, exponent);
    Tensor out = aa;
    for (size_t i = 0; i < a.v.size(); i += 8) {
      ECommand c;
      c.op = ECommand::Op::Add;
      for (size_t j = 0; j < 8 && i + j < a.v.size(); ++j) {
        c.a[j] = aa.v[i + j];
        c.b[j] = bb.v[i + j];
      }
      auto q = e.call(c);
      for (size_t j = 0; j < 8 && i + j < a.v.size(); ++j)
        out.v[i + j] = int16_t(q.lane[j]);
    }
    return compact(out);
  }
  Tensor add_full(const Tensor &a, const Tensor &b, bool subtract = false) {
    // Use M's existing shifted S64 accumulator to align and add before RNE.
    // E's S16 ADD would require rounding both operands before cancellation.
    int base = std::max(std::min(a.e, b.e), std::max(a.e, b.e) - 31);
    Tensor aa = a.e < base ? scale(a, base) : a;
    Tensor bb = b.e < base ? scale(b, base) : b;
    Tensor out = a;
    std::vector<int> exponents((a.v.size() + 7) / 8);
    int common = -1000;
    for (size_t i = 0; i < a.v.size(); i += 8) {
      unsigned cols = unsigned(std::min(size_t(8), a.v.size() - i));
      for (unsigned pass = 0; pass < 2; ++pass) {
        const auto &v = pass ? bb : aa;
        MCommand c;
        c.op = MCommand::Op::Scale;
        c.shift = unsigned(v.e - base);
        c.coefficient = pass && subtract ? -1 : 1;
        m.call(c);
        c = MCommand{};
        c.op = MCommand::Op::LoadA;
        c.wide_a = true;
        put_halfword(c.data, 0, 1);
        m.call(c);
        for (unsigned half = 0; half < 2; ++half) {
          c = MCommand{};
          c.op = MCommand::Op::LoadB;
          c.wide_b = true;
          c.half = half;
          for (unsigned j = 0; j < 4; ++j)
            if (half * 4 + j < cols)
              put_halfword(c.data, j * 8, uint16_t(v.v[i + half * 4 + j]));
          m.call(c);
        }
        c = MCommand{};
        c.op = MCommand::Op::Execute;
        c.last_k = 1;
        c.columns = cols;
        c.clear = pass == 0;
        c.wide_a = c.wide_b = true;
        m.call(c);
      }
      uint64_t p = 0;
      for (unsigned pair = 0; pair < (cols + 1) / 2; ++pair) {
        MCommand c;
        c.op = MCommand::Op::ReadFull;
        c.pair = pair;
        auto q = m.call(c);
        for (unsigned j = 0; j < 2 && pair * 2 + j < cols; ++j)
          p = std::max(p, uint64_t(std::llabs(q.lane[j])));
      }
      unsigned shift = output_shift(p);
      exponents[i / 8] = base + int(shift);
      common = std::max(common, exponents[i / 8]);
      for (unsigned half = 0; half < (cols + 3) / 4; ++half) {
        MCommand c;
        c.op = MCommand::Op::ReadFinal;
        c.half = half;
        c.shift = shift;
        auto q = m.call(c);
        for (unsigned j = 0; j < 4 && half * 4 + j < cols; ++j)
          out.v[i + half * 4 + j] = int16_t(q.lane[j]);
      }
    }
    MCommand reset_scale;
    reset_scale.op = MCommand::Op::Scale;
    m.call(reset_scale);
    for (size_t i = 0; i < a.v.size(); i += 8) {
      Tensor part{
          {out.v.begin() + i, out.v.begin() + std::min(a.v.size(), i + 8)},
          exponents[i / 8]};
      auto aligned = scale(part, common);
      std::copy(aligned.v.begin(), aligned.v.end(), out.v.begin() + i);
    }
    out.e = common;
    scale_decisions += exponents.size();
    macs += 2 * a.v.size();
    return compact(out);
  }
  Tensor mul(const Tensor &a, const Tensor &b) {
    if (a.v.size() != b.v.size())
      throw std::runtime_error("mul shape");
    ++scale_decisions;
    uint64_t p = peak(a) * peak(b);
    if (precise()) {
      p = 0;
      for (size_t i = 0; i < a.v.size(); ++i)
        p = std::max(p, uint64_t(std::llabs(int64_t(a.v[i]) * b.v[i])));
    }
    unsigned shift = output_shift(p);
    Tensor out = a;
    out.e = a.e + b.e + int(shift);
    for (size_t i = 0; i < a.v.size(); i += 8) {
      ECommand c;
      c.op = ECommand::Op::Mul;
      c.shift = shift;
      for (size_t j = 0; j < 8 && i + j < a.v.size(); ++j) {
        c.a[j] = a.v[i + j];
        c.b[j] = b.v[i + j];
      }
      auto q = e.call(c);
      for (size_t j = 0; j < 8 && i + j < a.v.size(); ++j)
        out.v[i + j] = int16_t(q.lane[j]);
    }
    return compact(out);
  }
  // 静态模型配置系数由host编码为输入参数，实际逐元素乘法仍在E。
  Tensor constant(const Tensor &x, double value) {
    int exponent =
        value == 0 ? -14 : int(std::ceil(std::log2(std::abs(value) / 16383)));
    Tensor parameter;
    parameter.e = exponent;
    parameter.v.assign(x.v.size(),
                       int16_t(std::lround(std::ldexp(value, -exponent))));
    return mul(x, parameter);
  }
  std::vector<unsigned> topk(const Tensor &x, unsigned k) {
    if (x.v.empty() || x.v.size() > 40 || k < 1 || k > 8)
      throw std::runtime_error("local topk shape");
    NCommand c;
    c.op = NCommand::Op::TopBegin;
    c.k = k;
    n.call(c);
    for (unsigned i = 0; i < x.v.size(); i += 4) {
      c = NCommand{};
      c.op = NCommand::Op::TopLoad;
      c.count = std::min(4U, unsigned(x.v.size()) - i);
      for (unsigned j = 0; j < c.count; ++j) {
        c.data[j] = uint16_t(x.v[i + j]);
        c.ids[j] = uint16_t(i + j);
      }
      n.call(c);
    }
    c = NCommand{};
    c.op = NCommand::Op::TopSelect;
    auto q = n.call(c);
    std::vector<unsigned> ids;
    for (unsigned i = 0; i < k; ++i)
      ids.push_back(unsigned(q.lane[i]));
    return ids;
  }
  // 一行向量乘转置权重。K32/N8事务，跨K累加S64，最后才窄化；无主机点积。
  Tensor linear(const Tensor &x, const int16_t *weights, size_t outputs,
                size_t inputs, int we,
                const std::vector<int> *group_scales = nullptr,
                size_t scale_start = 0) {
    if (x.v.size() != inputs || !outputs)
      throw std::runtime_error("linear shape");
    ++matmuls;
    macs += outputs * inputs;
    Tensor out;
    out.v.resize(outputs);
    std::vector<int> exp((outputs + 7) / 8);
    int common = -1000;
    for (size_t col = 0; col < outputs; col += 8) {
      unsigned cols = unsigned(std::min(size_t(8), outputs - col));
      for (size_t kb = 0; kb < inputs; kb += 32) {
        unsigned nk = unsigned(std::min(size_t(32), inputs - kb)),
                 tiles = (nk + 7) / 8;
        for (unsigned tile = 0; tile < tiles; ++tile) {
          MCommand a;
          a.op = MCommand::Op::LoadA;
          a.tile = tile;
          a.wide_a = true;
          for (unsigned j = 0; j < 8; ++j)
            if (kb + tile * 8 + j < inputs)
              put_halfword(a.data, j, uint16_t(x.v[kb + tile * 8 + j]));
          m.call(a);
          for (unsigned half = 0; half < 2; ++half) {
            MCommand b;
            b.op = MCommand::Op::LoadB;
            b.tile = tile;
            b.half = half;
            b.wide_b = true;
            for (unsigned j = 0; j < 32; ++j) {
              unsigned ncol = half * 4 + j / 8, k = j % 8;
              size_t ki = kb + tile * 8 + k;
              if (ncol < cols && ki < inputs)
                put_halfword(b.data, j,
                             uint16_t(weights[(col + ncol) * inputs + ki]));
            }
            m.call(b);
          }
        }
        MCommand c;
        c.op = MCommand::Op::Execute;
        c.tiles = tiles;
        c.last_k = (nk - 1) % 8 + 1;
        c.columns = cols;
        c.wide_a = c.wide_b = true;
        c.clear = (kb == 0);
        m.call(c);
      }
      uint64_t p = 0;
      for (unsigned pair = 0; pair < (cols + 1) / 2; ++pair) {
        MCommand c;
        c.op = MCommand::Op::ReadFull;
        c.pair = pair;
        auto q = m.call(c);
        for (unsigned j = 0; j < 2 && pair * 2 + j < cols; ++j)
          p = std::max(p, uint64_t(std::llabs(q.lane[j])));
      }
      ++scale_decisions;
      unsigned shift = output_shift(p);
      int group_we =
          group_scales ? group_scales->at(scale_start + col / 8) : we;
      exp[col / 8] = x.e + group_we + int(shift);
      for (unsigned half = 0; half < (cols + 3) / 4; ++half) {
        MCommand c;
        c.op = MCommand::Op::ReadFinal;
        c.half = half;
        c.shift = shift;
        auto q = m.call(c);
        for (unsigned j = 0; j < 4 && half * 4 + j < cols; ++j)
          out.v[col + half * 4 + j] = int16_t(q.lane[j]);
      }
      if (precise()) {
        Tensor group{{out.v.begin() + col, out.v.begin() + col + cols},
                     exp[col / 8]};
        group = compact(group);
        std::copy(group.v.begin(), group.v.end(), out.v.begin() + col);
        exp[col / 8] = group.e;
      }
      common = std::max(common, exp[col / 8]);
    }
    out.e = common;
    for (size_t i = 0; i < outputs; i += 8) {
      Tensor group{
          {out.v.begin() + i, out.v.begin() + std::min(outputs, i + 8)},
          exp[i / 8]};
      auto aligned = scale(group, common);
      std::copy(aligned.v.begin(), aligned.v.end(), out.v.begin() + i);
    }
    return compact(out);
  }
  Tensor linear(const Tensor &x, const Checkpoint &cp,
                const std::string &name) {
    auto w = cp.index.at(name);
    auto y = linear(x, cp.data(w), w.rows, w.cols, w.e, cp.scales(name));
    std::string bias = name.substr(0, name.size() - 6) + "bias";
    if (cp.index.count(bias))
      y = add(y, cp.vector(bias));
    return y;
  }
  // S按窗口保存/读回真实数据；外部更长的向量由主机DRAM持有。无无限S假设。
  Tensor replay_s(const Tensor &x) {
    Tensor out = x;
    for (size_t base = 0; base < x.v.size(); base += 8192) {
      size_t end = std::min(x.v.size(), base + 8192);
      for (size_t i = base; i < end; i += 8) {
        SCommand c;
        c.op = SCommand::Op::Write;
        c.address = unsigned((i - base) / 8);
        for (unsigned j = 0; j < 8 && i + j < end; ++j)
          c.data[j / 4] |= uint64_t(uint16_t(x.v[i + j])) << (16 * (j % 4));
        s.call(c);
      }
      for (size_t i = base; i < end; i += 8) {
        SCommand c;
        c.op = SCommand::Op::Read;
        c.address = unsigned((i - base) / 8);
        auto q = s.call(c);
        for (unsigned j = 0; j < 8 && i + j < end; ++j)
          out.v[i + j] = signed16(uint16_t(q.bits[j / 4] >> (16 * (j % 4))));
      }
    }
    return out;
  }
  Tensor norm(Tensor x, const Tensor &gamma, double epsilon, bool l2 = false) {
    double raw = std::ldexp(epsilon, -2 * x.e);
    while (raw > 4294967295.0) {
      x = scale(x, x.e + 1);
      raw = std::ldexp(epsilon, -2 * x.e);
    }
    NCommand begin;
    begin.op = NCommand::Op::Begin;
    begin.mode = l2 ? NCommand::Mode::L2 : NCommand::Mode::RMS;
    begin.epsilon = uint32_t(std::max(1.0, std::round(raw)));
    n.call(begin);
    for (size_t i = 0; i < x.v.size(); i += 8) {
      NCommand c;
      c.op = NCommand::Op::Stats;
      c.count = unsigned(std::min(size_t(8), x.v.size() - i));
      for (unsigned j = 0; j < c.count; ++j)
        c.data[j] = uint16_t(x.v[i + j]);
      n.call(c);
    }
    NCommand done;
    done.op = NCommand::Op::Finalize;
    n.call(done);
    done.op = NCommand::Op::ReadFactor;
    uint64_t factor = uint64_t(n.call(done).lane[0]);
    // 只生成一个尺度控制标量，不在host生成归一化向量。
    // 分别取max|x|和max|gamma|会错把不同通道的极值配对，严重浪费动态范围。
    uint64_t weighted_peak = 0;
    for (size_t i = 0; i < x.v.size(); ++i)
      weighted_peak = std::max(
          weighted_peak, uint64_t(std::llabs(int64_t(x.v[i]) * gamma.v[i])));
    uint64_t normalized_bound =
        (weighted_peak * factor + ((uint64_t(1) << 30) - 1)) >> 30;
    ++scale_decisions;
    int gamma_shift = int(output_shift(normalized_bound));
    auto adjusted_gamma = scale(gamma, gamma.e + gamma_shift);
    bool fused = precise() || l2 || std::getenv("LLM_NORM_FUSED") != nullptr;
    if (!fused) {
      uint64_t unit_bound =
          (peak(x) * factor * 1024 + ((uint64_t(1) << 30) - 1)) >> 30;
      // NormReplay has no further accumulator addition: use the full positive
      // S16 range, keeping the old Q10 precision whenever it already fits.
      unsigned unit_shift = unsigned(std::max(0, bits(unit_bound) - 15));
      if (unit_shift > 10)
        throw std::runtime_error("unit norm scaling extent");
      adjusted_gamma.e = -10 + int(unit_shift);
      adjusted_gamma.v.assign(gamma.v.size(), int16_t(1024U >> unit_shift));
    }
    auto original = replay_s(x);
    Tensor out = x;
    // N仍执行原有RNE30(x*factor*gamma_raw)，仅外部解释的二进制指数改变。
    // 可避免先把单位归一化结果舍入到Q10，再放大gamma造成精度丢失。
    out.e = adjusted_gamma.e;
    for (size_t i = 0; i < x.v.size(); i += 8) {
      NCommand c;
      c.op = NCommand::Op::NormReplay;
      c.count = unsigned(std::min(size_t(8), x.v.size() - i));
      for (unsigned j = 0; j < c.count; ++j) {
        c.data[j] = uint16_t(original.v[i + j]);
        c.gamma[j] = adjusted_gamma.v[i + j];
      }
      auto q = n.call(c);
      for (unsigned j = 0; j < c.count; ++j)
        out.v[i + j] = int16_t(q.lane[j]);
    }
    return fused ? compact(out) : mul(out, gamma);
  }
  Tensor function(const Tensor &x, GCommand::Function fn) {
    if (precise() && fn == GCommand::Function::Softplus)
      return softplus_precise(x);
    auto fixed = scale(x, -10);
    Tensor out = x;
    out.e = fn == GCommand::Function::Sigmoid ? -14 : -10;
    for (size_t i = 0; i < x.v.size(); i += 2) {
      GCommand c;
      c.function = fn;
      for (unsigned j = 0; j < 2 && i + j < x.v.size(); ++j)
        c.x[j] = fixed.v[i + j];
      auto q = g.call(c);
      for (unsigned j = 0; j < 2 && i + j < x.v.size(); ++j)
        out.v[i + j] = int16_t(q.lane[j]);
    }
    return out;
  }
  Tensor softplus_precise(const Tensor &x) {
    // Q10 Softplus output erases small time steps. For x<-1 use a bounded
    // log1p series with range-reduced N EXP; all vector arithmetic uses M/E.
    // Host chooses only scalar range/exponent parameters, never exp/log values.
    std::vector<Tensor> parts;
    int common = -1000;
    for (auto raw : x.v) {
      Tensor part{{raw}, x.e}, y;
      double control = std::ldexp(double(raw), x.e);
      if (control > 8)
        y = part; // Declared positive identity tail, error < exp(-8).
      else if (control >= -1) {
        GCommand c;
        c.function = GCommand::Function::Softplus;
        c.x[0] = scale(part, -10).v[0];
        y = Tensor{{int16_t(g.call(c).lane[0])}, -10};
      } else {
        int k = int(std::min(31.0, std::floor(-control / std::log(2.0))));
        if (k > 30)
          y = Tensor{{0}, -30}; // Absolute Softplus tail below 2^-30.
        else {
          Tensor offset{
              {int16_t(std::lround(std::ldexp(k * std::log(2.0), 10)))}, -10};
          auto reduced = scale(add(part, offset), -10);
          // Rounded range reduction can reach +1 Q10 at a power boundary;
          // choose one lower power then, keeping N's EXP argument nonpositive.
          if (reduced.v[0] > 0) {
            --k;
            offset.v[0] =
                int16_t(std::lround(std::ldexp(k * std::log(2.0), 10)));
            reduced = scale(add(part, offset), -10);
          }
          NCommand c;
          c.op = NCommand::Op::Begin;
          n.call(c);
          c.op = NCommand::Op::Stats;
          c.count = 2;
          c.data[1] = uint16_t(reduced.v[0]);
          n.call(c);
          c.op = NCommand::Op::Finalize;
          n.call(c);
          c.op = NCommand::Op::Exp;
          auto q = n.call(c);
          Tensor t{{int16_t(q.lane[1] == 32768 ? 16384 : q.lane[1])},
                   (q.lane[1] == 32768 ? -14 : -15) - k};
          Tensor term = t;
          y = t;
          for (unsigned power = 2; power <= 12; ++power) {
            term = mul(term, t);
            if (y.e - term.e > 20)
              break; // Remaining tail is below this S16 result's resolution.
            y = add(y, constant(term, (power % 2 ? 1. : -1.) / power));
          }
        }
      }
      y = compact(y);
      common = std::max(common, y.e);
      parts.push_back(std::move(y));
    }
    Tensor out;
    out.e = common;
    for (const auto &part : parts)
      out.v.push_back(scale(part, common).v[0]);
    return compact(out);
  }
  Tensor gelu(const Tensor &x) {
    auto y = function(x, GCommand::Function::GELU);
    // G's declared positive tail is identity. Preserve the original wide x
    // there.
    int exponent = std::max(x.e, y.e);
    auto xx = scale(x, exponent);
    y = scale(y, exponent);
    auto fixed = scale(x, -10);
    for (size_t i = 0; i < x.v.size(); i += 8) {
      ECommand c;
      c.op = ECommand::Op::Select;
      for (unsigned j = 0; j < 8 && i + j < x.v.size(); ++j) {
        c.a[j] = xx.v[i + j];
        c.b[j] = y.v[i + j];
        c.c[j] = fixed.v[i + j] > 8192;
      }
      auto q = e.call(c);
      for (unsigned j = 0; j < 8 && i + j < x.v.size(); ++j)
        y.v[i + j] = int16_t(q.lane[j]);
    }
    return compact(y);
  }
  // cos/sin are explicit static parameters exported from the official model.
  Tensor rope_table(const Tensor &x, unsigned head_dim, const Checkpoint &cp,
                    unsigned layer, unsigned pos) {
    auto w = cp.index.at("rope." + std::to_string(layer));
    unsigned dim = unsigned(w.cols);
    if (pos >= w.rows || dim > head_dim || dim % 2 || w.e > 0 || w.e < -31)
      throw std::runtime_error("RoPE table shape/scale");
    auto p = cp.data(w) + pos * dim;
    return rope_apply(x, head_dim, p, dim, w.e);
  }
  Tensor rope_apply(Tensor x, unsigned head_dim, const int16_t *p, unsigned dim,
                    int parameter_exponent) {
    if (precise()) {
      uint64_t bound = 0;
      for (size_t h = 0; h < x.v.size(); h += head_dim)
        for (unsigned k = 0; k < dim / 2; ++k) {
          uint64_t a = uint64_t(std::abs(int(x.v[h + k]))),
                   b = uint64_t(std::abs(int(x.v[h + dim / 2 + k]))),
                   c = uint64_t(std::abs(int(p[k]))),
                   s = uint64_t(std::abs(int(p[dim / 2 + k])));
          bound = std::max(bound, std::max(a * c + b * s, a * s + b * c));
        }
      unsigned shift = output_shift(
          uint64_t(rne(Wide(bound), unsigned(-parameter_exponent))));
      if (shift)
        x = scale(x, x.e + int(shift));
    }
    Tensor out = x;
    for (size_t h = 0; h < x.v.size(); h += head_dim)
      for (unsigned k = 0; k < dim / 2; k += 4) {
        ECommand c;
        c.op = ECommand::Op::RoPE;
        c.shift = unsigned(-parameter_exponent);
        for (unsigned j = 0; j < 4 && k + j < dim / 2; ++j) {
          c.a[2 * j] = x.v[h + k + j];
          c.a[2 * j + 1] = x.v[h + dim / 2 + k + j];
          c.b[2 * j] = p[k + j];
          c.b[2 * j + 1] = p[dim / 2 + k + j];
        }
        auto q = e.call(c);
        for (unsigned j = 0; j < 4 && k + j < dim / 2; ++j) {
          out.v[h + k + j] = int16_t(q.lane[2 * j]);
          out.v[h + dim / 2 + k + j] = int16_t(q.lane[2 * j + 1]);
        }
      }
    return out;
  }
  Tensor silu(const Tensor &x) {
    // 只把Sigmoid的自变量转Q10；保留原x尺度，避免大SiLU输出被Q5.10裁剪。
    auto fixed = scale(x, -10);
    Tensor sigmoid = x;
    sigmoid.e = -14;
    for (size_t i = 0; i < x.v.size(); i += 2) {
      GCommand c;
      c.function = GCommand::Function::Sigmoid;
      for (unsigned j = 0; j < 2 && i + j < x.v.size(); ++j)
        c.x[j] = fixed.v[i + j];
      auto q = g.call(c);
      for (unsigned j = 0; j < 2 && i + j < x.v.size(); ++j)
        sigmoid.v[i + j] = int16_t(q.lane[j]);
    }
    return mul(x, sigmoid);
  }
  Tensor rope(const Tensor &x, unsigned head_dim, unsigned position,
              double theta) {
    std::vector<int16_t> parameters(head_dim);
    for (unsigned k = 0; k < head_dim / 2; ++k) {
      double angle =
          double(position) / std::pow(theta, double(2 * k) / head_dim);
      parameters[k] = int16_t(std::lround(std::cos(angle) * 16384));
      parameters[head_dim / 2 + k] =
          int16_t(std::lround(std::sin(angle) * 16384));
    }
    return rope_apply(x, head_dim, parameters.data(), head_dim, -14);
  }
  Tensor softmax(const Tensor &x) {
    if (x.v.empty() || x.v.size() > 65535)
      throw std::runtime_error("softmax length");
    NCommand c;
    c.op = NCommand::Op::Begin;
    n.call(c);
    for (size_t i = 0; i < x.v.size(); i += 8) {
      c = NCommand{};
      c.op = NCommand::Op::Stats;
      c.count = unsigned(std::min(size_t(8), x.v.size() - i));
      for (unsigned j = 0; j < c.count; ++j)
        c.data[j] = uint16_t(x.v[i + j]);
      n.call(c);
    }
    c = NCommand{};
    c.op = NCommand::Op::ReadStats;
    int16_t mx = int16_t(n.call(c).lane[1]);
    Tensor shifted = x;
    if (precise()) {
      Tensor maximum = x;
      maximum.v.assign(x.v.size(), mx);
      shifted = add_full(x, maximum, true);
    } else
      for (size_t i = 0; i < x.v.size(); i += 8) {
        ECommand d;
        d.op = ECommand::Op::Sub;
        for (unsigned j = 0; j < 8 && i + j < x.v.size(); ++j) {
          d.a[j] = x.v[i + j];
          d.b[j] = mx;
        }
        auto q = e.call(d);
        for (unsigned j = 0; j < 8 && i + j < x.v.size(); ++j)
          shifted.v[i + j] = int16_t(q.lane[j]);
      }
    shifted = scale(shifted, -10);
    c = NCommand{};
    c.op = NCommand::Op::Begin;
    n.call(c);
    for (size_t i = 0; i < x.v.size(); i += 8) {
      c = NCommand{};
      c.op = NCommand::Op::Stats;
      c.count = unsigned(std::min(size_t(8), x.v.size() - i));
      for (unsigned j = 0; j < c.count; ++j)
        c.data[j] = uint16_t(shifted.v[i + j]);
      n.call(c);
    }
    c = NCommand{};
    c.op = NCommand::Op::Finalize;
    n.call(c);
    Tensor exp = shifted;
    for (size_t i = 0; i < x.v.size(); i += 8) {
      c = NCommand{};
      c.op = NCommand::Op::Exp;
      c.count = unsigned(std::min(size_t(8), x.v.size() - i));
      for (unsigned j = 0; j < c.count; ++j)
        c.data[j] = uint16_t(shifted.v[i + j]);
      auto q = n.call(c);
      for (unsigned j = 0; j < c.count; ++j)
        exp.v[i + j] = signed16(uint16_t(q.lane[j]));
    }
    exp = replay_s(exp);
    c = NCommand{};
    c.op = NCommand::Op::FinishExp;
    n.call(c);
    Tensor out = exp;
    out.e = -14;
    for (size_t i = 0; i < x.v.size(); i += 8) {
      c = NCommand{};
      c.op = NCommand::Op::SoftReplay;
      c.count = unsigned(std::min(size_t(8), x.v.size() - i));
      for (unsigned j = 0; j < c.count; ++j)
        c.data[j] = uint16_t(exp.v[i + j]);
      auto q = n.call(c);
      for (unsigned j = 0; j < c.count; ++j)
        out.v[i + j] = int16_t(q.lane[j]);
    }
    return out;
  }
  // 有限T逐批交付最终词表；不把151936词当成6KiB一次存下。
  Tensor handoff(const Tensor &x) {
    Tensor out = x;
    for (size_t base = 0; base < x.v.size(); base += 3072) {
      size_t count = std::min(size_t(3072), x.v.size() - base);
      unsigned words = unsigned((count + 7) / 8);
      TCommand c;
      c.op = TCommand::Op::Begin;
      c.words = words;
      t.call(c);
      for (unsigned i = 0; i < words; ++i) {
        c = TCommand{};
        c.op = TCommand::Op::Write;
        c.index = i;
        for (unsigned j = 0; j < 8 && i * 8 + j < count; ++j)
          c.data[j / 4] |= uint64_t(uint16_t(x.v[base + i * 8 + j]))
                           << (16 * (j % 4));
        t.call(c);
      }
      c = TCommand{};
      c.op = TCommand::Op::Commit;
      t.call(c);
      for (unsigned i = 0; i < words; ++i) {
        c = TCommand{};
        c.op = TCommand::Op::Take;
        auto q = t.call(c);
        for (unsigned j = 0; j < 8 && i * 8 + j < count; ++j)
          out.v[base + i * 8 + j] =
              signed16(uint16_t(q.bits[j / 4] >> (16 * (j % 4))));
      }
      c = TCommand{};
      c.op = TCommand::Op::Release;
      t.call(c);
    }
    return out;
  }
  unsigned argmax(const Tensor &x) {
    // TopK的ID只有U16。分组局部ID+外部地址映射，逐层归并，比较仍在N内。
    std::vector<unsigned> candidates(x.v.size());
    for (unsigned i = 0; i < candidates.size(); ++i)
      candidates[i] = i;
    while (candidates.size() > 1) {
      std::vector<unsigned> winners;
      for (size_t base = 0; base < candidates.size(); base += 40) {
        unsigned count =
            unsigned(std::min(size_t(40), candidates.size() - base));
        NCommand c;
        c.op = NCommand::Op::TopBegin;
        c.k = 1;
        n.call(c);
        for (unsigned i = 0; i < count; i += 4) {
          c = NCommand{};
          c.op = NCommand::Op::TopLoad;
          c.count = std::min(4U, count - i);
          for (unsigned j = 0; j < c.count; ++j) {
            c.data[j] = uint16_t(x.v[candidates[base + i + j]]);
            c.ids[j] = uint16_t(i + j);
          }
          n.call(c);
        }
        c = NCommand{};
        c.op = NCommand::Op::TopSelect;
        auto q = n.call(c);
        winners.push_back(candidates[base + unsigned(q.lane[0])]);
      }
      candidates.swap(winners);
    }
    return candidates.at(0);
  }
};
} // namespace llm
