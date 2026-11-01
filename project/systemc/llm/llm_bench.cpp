// 真实七宏SystemC内核上的自回归dense LLM驱动。FP32只在离线验证程序中出现。
#include "recurrent.hpp"
#include <iomanip>
using namespace llm;
struct LayerCache {
  std::vector<Tensor> keys, values;
};
class Driver : public sc_core::sc_module {
  Runtime rt;
  Recurrent recurrence{rt};
  std::string directory, output;
  bool selftest;
  unsigned max_steps;
  static Tensor slice(const Tensor &x, size_t start, size_t count) {
    return tensor_slice(x, start, count);
  }
  static void binary(std::ofstream &f, const Tensor &x) {
    int32_t exponent = x.lane_e.empty() ? x.e : (-2147483647 - 1);
    uint32_t size = uint32_t(x.v.size());
    f.write(reinterpret_cast<const char *>(&exponent), 4);
    f.write(reinterpret_cast<const char *>(&size), 4);
    if (!x.lane_e.empty())
      for (auto e : x.lane_e) {
        int32_t lane = e;
        f.write(reinterpret_cast<const char *>(&lane), 4);
      }
    f.write(reinterpret_cast<const char *>(x.v.data()),
            std::streamsize(x.v.size() * 2));
  }
  void check(bool ok, const char *message) {
    if (!ok)
      throw std::runtime_error(message);
  }
  void tests() {
    // 非8/32整数倍的M尾块，正负输入，完整跨K累加；参考纯整数校验。
    Tensor a;
    a.e = -8;
    a.v.resize(37);
    std::vector<int16_t> w(11 * 37);
    for (unsigned i = 0; i < 37; ++i)
      a.v[i] = int16_t(int(i) % 9 - 4);
    for (unsigned i = 0; i < w.size(); ++i)
      w[i] = int16_t(int(i) % 7 - 3);
    auto y = rt.linear(a, w.data(), 11, 37, -7);
    for (unsigned i = 0; i < 11; ++i) {
      int dot = 0;
      for (unsigned k = 0; k < 37; ++k)
        dot += int(a.v[k]) * w[i * 37 + k];
      check(std::ldexp(double(y.v[i]), y.e) == std::ldexp(double(dot), -15),
            "M tail/scale mismatch");
    }
    Tensor logits;
    logits.e = -6;
    logits.v.resize(257);
    for (unsigned i = 0; i < 257; ++i)
      logits.v[i] = int16_t(int(i % 31) * 64 - 8000);
    logits.v[256] = 3000; // 最大值只在最后到达；不预先用后续数据。
    auto p = rt.softmax(logits);
    double sum = 0;
    for (auto v : p.v)
      sum += std::ldexp(double(v), p.e);
    check(std::abs(sum - 1) < 0.02 && p.v.back() > 16000,
          "long softmax replay");
    auto passed = rt.handoff(p);
    check(passed.v == p.v, "T handoff");
    Tensor gamma{{1024, 1024, 1024, 1024}, -10};
    Tensor xx{{1024, 2048, -1024, -2048}, -10};
    auto normalized = rt.norm(xx, gamma, 1e-6);
    check(std::abs(std::ldexp(double(normalized.v[0]), normalized.e) -
                   1 / std::sqrt(2.5)) < 0.004,
          "RMS scale");
    Tensor outlier, unit;
    outlier.e = unit.e = -10;
    outlier.v.assign(4096, 16);
    outlier.v[0] = 16384;
    unit.v.assign(4096, 1024);
    auto wide_norm = rt.norm(outlier, unit, 1e-9);
    check(std::abs(
              std::ldexp(double(wide_norm.v[0]), wide_norm.e) -
              16384 / std::sqrt((16384. * 16384 + 4095 * 256) / 4096 + 1)) < .1,
          "RMS outlier beyond unit Q5.10 must not saturate");
    Tensor wide{{-10000, -1000, 0, 1000, 10000}, -5};
    auto activation = rt.silu(wide);
    check(std::abs(std::ldexp(double(activation.v.back()), activation.e) -
                   312.5) < 0.1,
          "wide SiLU");
    Tensor many;
    many.v.resize(151936);
    many.v[150001] = 12000;
    check(rt.argmax(many) == 150001, "large vocabulary local IDs");
    // 两token的K尺度差15bit，不能固定到首token尺度而静默饱和。
    LayerCache cache;
    Tensor query;
    query.e = -10;
    query.v.assign(8, 1000);
    Tensor key;
    key.e = -20;
    key.v.assign(8, 1000);
    Tensor value;
    value.e = -10;
    value.v.assign(8, 1024);
    attention(query, key, value, cache, 1, 1, 8, 1 / std::sqrt(8.0));
    key.e = -5;
    value.v.assign(8, 2048);
    auto attended =
        attention(query, key, value, cache, 1, 1, 8, 1 / std::sqrt(8.0));
    check(std::abs(std::ldexp(double(attended.v[0]), attended.e) - 2) < 0.01,
          "K cache exponent alignment");
    auto l2 = rt.norm(Tensor{{3072, 4096}, -10}, Tensor{{16384, 16384}, -14},
                      1e-6, true);
    check(std::abs(std::ldexp(double(l2.v[0]), l2.e) - .6) < .002 &&
              std::abs(std::ldexp(double(l2.v[1]), l2.e) - .8) < .002,
          "N L2 adapter");
    auto gelu = rt.gelu(Tensor{{-12800, 12800}, -7});
    check(gelu.v[0] == 0 &&
              std::abs(std::ldexp(double(gelu.v[1]), gelu.e) - 100) < .01,
          "wide GELU identity tail");
    for (bool ssm_mode : {false, true}) {
      RecurrentCache rc;
      Tensor key, query, value, inject, skip;
      key.e = query.e = -14;
      key.v.assign(6, 8192);
      query.v.assign(6, 4096);
      value.e = inject.e = skip.e = -10;
      value.v.assign(16, 1024);
      inject.v.assign(16, 256);
      skip.v.assign(16, 128);
      for (unsigned step = 0; step < 2; ++step) {
        auto result = recurrence.update(
            rc, key, query, value, inject, skip, {0x40000000U, 0x40000000U},
            {0x40000000U, 0x40000000U}, 2, 3, 8, step, ssm_mode);
        double expected =
            ssm_mode ? (step ? .265625 : .21875) : (step ? .24609375 : .1875);
        for (auto v : result.v)
          check(std::abs(std::ldexp(double(v), result.e) - expected) < .0002,
                "R multi-head state turnover, GDN/SSM/skip");
      }
    }
    {
      RecurrentCache rc;
      Tensor b{{4096, -3072}, -10}, c{{8192, 4096}, -10};
      Tensor x, injection, skip;
      x.e = injection.e = skip.e = -10;
      x.v.assign(8, 1024);
      injection.v.assign(8, 256);
      skip.v.assign(8, 128);
      for (unsigned step = 0; step < 2; ++step) {
        auto y = recurrence.update(rc, b, c, x, injection, skip, {0x40000000U},
                                   {}, 1, 2, 8, step, true);
        double expected = step ? 7.625 : 5.125;
        for (auto v : y.v)
          check(std::abs(std::ldexp(double(v), y.e) - expected) < .002,
                "SSM unbounded B/C scale compensation including skip");
      }
    }
    if (Runtime::precise()) {
      std::vector<int16_t> grouped_weights(19 * 2, 64);
      std::vector<int> grouped_exponents{-8, -12, -16};
      auto grouped = rt.linear(Tensor{{2, 3}, 0}, grouped_weights.data(), 19, 2,
                               7, &grouped_exponents);
      for (unsigned row = 0; row < 19; ++row)
        check(std::ldexp(double(grouped.v[row]), grouped.e) ==
                  std::ldexp(320., grouped_exponents[row / 8]),
              "M N8 weight scales include partial output group");
      std::vector<int16_t> hi(19 * 2), lo(19 * 2);
      for (unsigned row = 0; row < 19; ++row) {
        hi[row * 2] = 16000;
        hi[row * 2 + 1] = -16000;
        lo[row * 2] = 1;
      }
      std::vector<int> he{0, -2, 1}, le{-15, -17, -14};
      auto residual = rt.linear(Tensor{{32767, 32767}, 0}, hi.data(), 19, 2, 0,
                                &he, 0, lo.data(), &le);
      for (unsigned row = 0; row < 19; ++row)
        check(std::abs(std::ldexp(double(residual.v[row]), residual.e) -
                       std::ldexp(32767., le[row / 8])) < .0002,
              "M high/low weight terms accumulate before final narrowing");
      auto mixed_dt =
          rt.function(Tensor{{-7680, -512}, -10}, GCommand::Function::Softplus);
      check(std::abs(std::ldexp(double(mixed_dt.v[0]), mixed_dt.e) /
                         std::log1p(std::exp(-7.5)) -
                     1) < .02,
            "mixed Softplus channels keep small time step precision");
      for (int raw = -10240; raw <= -1024; raw += 257) {
        auto y = rt.function(Tensor{{int16_t(raw)}, -10},
                             GCommand::Function::Softplus);
        double expected = std::log1p(std::exp(double(raw) / 1024));
        check(std::abs(std::ldexp(double(y.v[0]), y.e) / expected - 1) < .002,
              "small Softplus time step keeps relative precision");
      }
      auto rotated = rt.rope(Tensor{{30000, 30000}, -15}, 2, 1, 10000);
      check(std::abs(std::ldexp(double(rotated.v[1]), rotated.e) -
                     30000. / 32768 * (std::cos(1.) + std::sin(1.))) < .0001,
            "RoPE reserves range for sum of two products");
      auto p = rt.softmax(Tensor{{32760, -32760}, -15});
      check(std::abs(std::ldexp(double(p.v[0]), p.e) - .880746) < .001,
            "Softmax subtraction retains full S16 difference");
      auto y = rt.add(Tensor{{16384, 1}, -2}, Tensor{{-32767, -1}, -3});
      check(std::ldexp(double(y.v[0]), y.e) == .125 &&
                std::ldexp(double(y.v[1]), y.e) == .125,
            "M full accumulator cancellation before narrowing");
      auto z = rt.mul(Tensor{{16384, 1}, -10}, Tensor{{1, 16384}, -10});
      check(std::ldexp(double(z.v[0]), z.e) == .015625 &&
                std::ldexp(double(z.v[1]), z.e) == .015625,
            "paired product bound preserves disjoint extrema");
    }
    if (std::getenv("LLM_ACCURATE_SILU")) {
      for (int raw = -12288; raw <= 12288; raw += 197) {
        auto y = rt.silu(Tensor{{int16_t(raw)}, -10});
        double x = double(raw) / 1024, reference = x / (1 + std::exp(-x));
        check(std::abs(std::ldexp(double(y.v[0]), y.e) - reference) <
                  std::max(1e-7, std::abs(reference) * .001),
              "dynamic SiLU keeps small negative tail relative precision");
      }
    }
    if (std::getenv("LLM_BLOCK_SCALES")) {
      rt.block_mode = true;
      Tensor xx;
      xx.v.assign(19, 16000);
      xx.e = -2;
      xx.lane_e.assign(19, -20);
      std::fill(xx.lane_e.begin(), xx.lane_e.begin() + 8, -2);
      auto copied = rt.handoff(xx);
      check(copied.lane_e == xx.lane_e && copied.v == xx.v,
            "T preserves external scale metadata");
      auto sum = rt.add(xx, xx);
      for (size_t i = 0; i < 19; ++i)
        check(std::ldexp(double(sum.v[i]), sum.lane_e[i]) ==
                  std::ldexp(32000., xx.lane_e[i]),
              "N8 residual tails keep small channels");
      std::vector<int16_t> ww(11 * 19, 1);
      auto mm = rt.linear(xx, ww.data(), 11, 19, 0);
      double reference = 8 * 4000. + 11 * std::ldexp(16000., -20);
      for (size_t i = 0; i < 11; ++i)
        check(std::abs(std::ldexp(double(mm.v[i]), mm.lane_e[i]) - reference) <
                  2.,
              "M K8 exponents/tail align before accumulation");
      Tensor cancellation = xx;
      std::fill(cancellation.lane_e.begin() + 8,
                cancellation.lane_e.begin() + 16, -7);
      std::vector<int16_t> high(11 * 19), low(11 * 19);
      for (unsigned row = 0; row < 11; ++row) {
        for (unsigned k = 0; k < 8; ++k)
          high[row * 19 + k] = 1;
        for (unsigned k = 8; k < 16; ++k)
          high[row * 19 + k] = -32;
        low[row * 19] = 1;
      }
      std::vector<int> he(2, 0), le(2, -15);
      auto combined = rt.linear(cancellation, high.data(), 11, 19, 0, &he, 0,
                                low.data(), &le);
      for (unsigned row = 0; row < 11; ++row)
        check(
            std::abs(std::ldexp(double(combined.v[row]), combined.lane_e[row]) -
                     .1220703125) < .00001,
            "M combines input block scales and high/low weights before RNE");
      Tensor gamma;
      gamma.v.assign(19, 16384);
      gamma.e = -14;
      auto nn = rt.norm(xx, gamma, 1e-6);
      double rms = std::sqrt(
          (8 * 4000. * 4000. + 11 * std::pow(std::ldexp(16000., -20), 2)) / 19 +
          1e-6);
      check(std::abs(std::ldexp(double(nn.v[18]), nn.lane_e[18]) /
                         (std::ldexp(16000., -20) / rms) -
                     1) < .002,
            "N replay preserves small original channels");
      auto cut = slice(sum, 7, 5);
      auto aligned = rt.uniform(cut);
      check(aligned.lane_e.empty() && aligned.v.size() == 5,
            "unaligned scale slice explicitly converts");
      rt.block_mode = false;
    }
    std::cout << "LLM_ADAPTER_SELFTEST PASS M tails, scales, long Softmax, "
                 "RMS, wide SiLU, S/T, hierarchical vocabulary argmax\n";
  }
  Tensor headnorm(const Tensor &x, const Tensor &gamma, unsigned heads,
                  unsigned dim, double eps) {
    Tensor out = x;
    std::vector<Tensor> parts;
    int common = -1000;
    for (unsigned h = 0; h < heads; ++h) {
      auto part = rt.norm(slice(x, h * dim, dim), gamma, eps);
      common = std::max(common, part.e);
      parts.push_back(std::move(part));
    }
    if (rt.block_mode)
      return rt.join(parts);
    out.e = common;
    for (unsigned h = 0; h < heads; ++h) {
      auto part = rt.scale(parts[h], common);
      std::copy(part.v.begin(), part.v.end(), out.v.begin() + h * dim);
    }
    return out;
  }
  Tensor attention(const Tensor &q, const Tensor &k, const Tensor &v,
                   LayerCache &cache, unsigned heads, unsigned kvheads,
                   unsigned dim, double attention_scale, unsigned window = 0) {
    cache.keys.push_back(k);
    cache.values.push_back(v);
    if (window && cache.keys.size() > window) {
      cache.keys.erase(cache.keys.begin());
      cache.values.erase(cache.values.begin());
    }
    size_t length = cache.keys.size();
    int ke = -1000;
    for (const auto &key : cache.keys)
      ke = std::max(ke, key.e);
    Tensor output;
    output.v.resize(heads * dim);
    int common = -1000;
    std::vector<Tensor> pieces;
    // GQA按组共享KV头；QK和PV都经过M，host仅作转置/索引。
    for (unsigned h = 0; h < heads; ++h) {
      unsigned kh = h / (heads / kvheads);
      if (rt.block_mode) {
        ke = -1000;
        for (const auto &key : cache.keys)
          ke = std::max(ke, slice(key, kh * dim, dim).e);
      }
      std::vector<int16_t> keys(length * dim);
      for (size_t pos = 0; pos < length; ++pos) {
        auto aligned = rt.scale(slice(cache.keys[pos], kh * dim, dim), ke);
        std::copy(aligned.v.begin(), aligned.v.end(), keys.begin() + pos * dim);
      }
      auto score =
          rt.linear(slice(q, h * dim, dim), keys.data(), length, dim, ke);
      auto probability = rt.softmax(rt.constant(score, attention_scale));
      int ve = -1000;
      for (const auto &value : cache.values)
        ve = std::max(ve, value.e);
      if (rt.block_mode) {
        ve = -1000;
        for (const auto &value : cache.values)
          ve = std::max(ve, slice(value, kh * dim, dim).e);
      }
      std::vector<int16_t> values(dim * length);
      for (size_t pos = 0; pos < length; ++pos) {
        auto vv = rt.scale(slice(cache.values[pos], kh * dim, dim), ve);
        for (unsigned d = 0; d < dim; ++d)
          values[d * length + pos] = vv.v[d];
      }
      auto part = rt.linear(probability, values.data(), dim, length, ve);
      common = std::max(common, part.e);
      pieces.push_back(std::move(part));
    }
    if (rt.block_mode)
      return rt.join(pieces);
    output.e = common;
    for (unsigned h = 0; h < heads; ++h) {
      auto part = rt.scale(pieces[h], common);
      std::copy(part.v.begin(), part.v.end(), output.v.begin() + h * dim);
    }
    return rt.compact(output);
  }
  Tensor concatenate(const std::vector<Tensor> &parts) {
    if (rt.block_mode)
      return rt.join(parts);
    int common = -1000;
    for (auto &p : parts)
      common = std::max(common, p.e);
    Tensor out;
    out.e = common;
    for (auto &p : parts) {
      auto aligned = rt.scale(p, common);
      out.v.insert(out.v.end(), aligned.v.begin(), aligned.v.end());
    }
    return rt.compact(out);
  }
  Tensor repeat_heads(const Tensor &x, unsigned heads, unsigned rows,
                      unsigned repeat) {
    std::vector<Tensor> parts;
    for (unsigned h = 0; h < heads; ++h)
      for (unsigned r = 0; r < repeat; ++r)
        parts.push_back(slice(x, h * rows, rows));
    return concatenate(parts);
  }
  Tensor gdn(const Tensor &x, const Checkpoint &cp, const std::string &root,
             RecurrentCache &cache, unsigned step, double eps) {
    unsigned kh = cp.number("linear_num_key_heads"),
             vh = cp.number("linear_num_value_heads"),
             kd = cp.number("linear_key_head_dim"),
             vd = cp.number("linear_value_head_dim");
    auto mixed = rt.linear(x, cp, root + "in_proj_qkv.weight");
    mixed = recurrence.convolution(mixed, cp, root, cache, step);
    auto q = slice(mixed, 0, kh * kd), k = slice(mixed, kh * kd, kh * kd),
         v = slice(mixed, 2 * kh * kd, vh * vd);
    Tensor gamma;
    gamma.e = -14;
    gamma.v.assign(kd, 16384);
    std::vector<Tensor> qp, kp;
    for (unsigned h = 0; h < kh; ++h) {
      qp.push_back(rt.constant(rt.norm(slice(q, h * kd, kd), gamma, 1e-6, true),
                               1 / std::sqrt(double(kd))));
      kp.push_back(rt.norm(slice(k, h * kd, kd), gamma, 1e-6, true));
    }
    q = repeat_heads(concatenate(qp), kh, kd, vh / kh);
    k = repeat_heads(concatenate(kp), kh, kd, vh / kh);
    auto b = rt.function(rt.linear(x, cp, root + "in_proj_b.weight"),
                         GCommand::Function::Sigmoid);
    auto a = rt.function(rt.add(rt.linear(x, cp, root + "in_proj_a.weight"),
                                cp.vector(root + "dt_bias")),
                         GCommand::Function::Softplus);
    auto log_decay = rt.constant(rt.mul(a, cp.vector(root + "A_exp")), -1);
    auto alpha = recurrence.decay(log_decay);
    std::vector<uint32_t> beta;
    for (auto value : b.v)
      beta.push_back(uint32_t(uint16_t(value)) << 17);
    auto y = recurrence.update(cache, k, q, v, Tensor{}, Tensor{}, alpha, beta,
                               vh, kd, vd, step, false);
    auto z = rt.linear(x, cp, root + "in_proj_z.weight");
    std::vector<Tensor> normalized;
    for (unsigned h = 0; h < vh; ++h)
      normalized.push_back(rt.mul(
          rt.norm(slice(y, h * vd, vd), cp.vector(root + "norm.weight"), eps),
          rt.silu(slice(z, h * vd, vd))));
    return rt.linear(concatenate(normalized), cp, root + "out_proj.weight");
  }
  Tensor ssm(const Tensor &input, const Checkpoint &cp, const std::string &root,
             RecurrentCache &cache, unsigned step, double eps) {
    unsigned heads = cp.number("mamba_n_heads"),
             width = cp.number("mamba_d_head"),
             rows = cp.number("mamba_d_state"),
             groups = cp.number("mamba_n_groups");
    if (groups != 1)
      throw std::runtime_error("Falcon group mapping requires one group");
    auto x = rt.constant(input, std::stod(cp.meta.at("ssm_in_multiplier")));
    auto projected = rt.linear(x, cp, root + "in_proj.weight");
    unsigned inner = heads * width;
    auto multiplier = [&](unsigned i) {
      return std::stod(cp.meta.at("ssm_multiplier_" + std::to_string(i)));
    };
    auto gate = rt.constant(slice(projected, 0, inner), multiplier(0));
    auto conv = concatenate(
        {rt.constant(slice(projected, inner, inner), multiplier(1)),
         rt.constant(slice(projected, 2 * inner, rows), multiplier(2)),
         rt.constant(slice(projected, 2 * inner + rows, rows), multiplier(3))});
    auto dt = rt.constant(slice(projected, 2 * inner + 2 * rows, heads),
                          multiplier(4));
    dt = rt.function(rt.add(dt, cp.vector(root + "dt_bias")),
                     GCommand::Function::Softplus);
    conv = recurrence.convolution(conv, cp, root, cache, step);
    x = slice(conv, 0, inner);
    auto b = repeat_heads(slice(conv, inner, rows), 1, rows, heads),
         c = repeat_heads(slice(conv, inner + rows, rows), 1, rows, heads);
    if (step == 0 && std::getenv("LLM_TRACE_SSM") &&
        root == "model.layers.0.mamba.") {
      for (const auto &entry : std::vector<std::pair<std::string, Tensor>>{
               {"ssm-b", b}, {"ssm-c", c}, {"ssm-dt", dt}}) {
        std::ofstream f(output + "/stage-" + entry.first + ".bin",
                        std::ios::binary);
        binary(f, entry.second);
      }
    }
    auto alpha = recurrence.decay(
        rt.constant(rt.mul(dt, cp.vector(root + "A_exp")), -1));
    Tensor dt_channels, skip;
    dt_channels.e = dt.e;
    auto d = cp.vector(root + "D");
    skip.e = d.e;
    for (unsigned h = 0; h < heads; ++h) {
      dt_channels.v.insert(dt_channels.v.end(), width, dt.v[h]);
      skip.v.insert(skip.v.end(), width, d.v[h]);
    }
    auto inject = rt.mul(x, dt_channels);
    auto y = recurrence.update(cache, b, c, x, inject, skip, alpha, {}, heads,
                               rows, width, step, true);
    // Falcon gate first, then RMS across all4096 channels, unlike Qwen's
    // per-head norm first.
    y = rt.norm(rt.mul(y, rt.silu(gate)), cp.vector(root + "norm.weight"), eps);
    return rt.linear(y, cp, root + "out_proj.weight");
  }
  Tensor moe(const Tensor &x, const Checkpoint &cp, const std::string &root) {
    auto scores =
        rt.linear(x, cp, root + "block_sparse_moe.router.layer.weight");
    auto ids = rt.topk(scores, unsigned(cp.number("num_experts_per_tok")));
    scores = rt.uniform(scores);
    Tensor selected;
    selected.e = scores.e;
    for (auto id : ids)
      selected.v.push_back(scores.v[id]);
    auto probabilities = rt.softmax(selected);
    auto gu_name = root + "block_sparse_moe.input_linear.weight";
    auto down_name = root + "block_sparse_moe.output_linear.weight";
    auto gu = cp.index.at(gu_name);
    auto down = cp.index.at(down_name);
    auto low_data = [&](const std::string &name,
                        size_t offset) -> const int16_t * {
      auto it = cp.index.find(name + ".low");
      return it == cp.index.end() ? nullptr : cp.data(it->second) + offset;
    };
    unsigned hidden = cp.number("hidden"),
             intermediate = cp.number("intermediate");
    Tensor sum;
    if ((cp.scales(gu_name) || cp.scales(down_name)) &&
        (hidden % 8 || (2 * intermediate) % 8))
      throw std::runtime_error("expert group alignment");
    for (unsigned j = 0; j < ids.size(); ++j) {
      unsigned id = ids[j];
      auto fused =
          rt.linear(x, cp.data(gu) + size_t(id) * 2 * intermediate * hidden,
                    2 * intermediate, hidden, gu.e, cp.scales(gu_name),
                    size_t(id) * 2 * intermediate / 8,
                    low_data(gu_name, size_t(id) * 2 * intermediate * hidden),
                    cp.scales(gu_name + ".low"));
      auto product = rt.mul(rt.silu(slice(fused, 0, intermediate)),
                            slice(fused, intermediate, intermediate));
      auto result = rt.linear(
          product, cp.data(down) + size_t(id) * hidden * intermediate, hidden,
          intermediate, down.e, cp.scales(down_name), size_t(id) * hidden / 8,
          low_data(down_name, size_t(id) * hidden * intermediate),
          cp.scales(down_name + ".low"));
      Tensor weight;
      weight.e = probabilities.e;
      weight.v.assign(hidden, probabilities.v[j]);
      result = rt.mul(result, weight);
      sum = j ? rt.add(sum, result) : result;
    }
    return sum;
  }
  void infer() {
    Checkpoint cp(directory);
    auto family = cp.meta.at("family");
    if (family != "qwen3" && family != "qwen2" && family != "llama" &&
        family != "granitemoe" && family != "phi3" && family != "gemma3_text" &&
        family != "qwen3_5_text" && family != "falcon_h1")
      throw std::runtime_error("family not implemented by dense runtime");
    // R's present state/conv mapping retains its explicit uniform scale
    // contract. Dense and MoE use the opt-in N8 activation policy, independent
    // of answers.
    rt.block_mode = std::getenv("LLM_BLOCK_SCALES") &&
                    family != "qwen3_5_text" && family != "falcon_h1";
    unsigned heads = cp.number("heads"), kvheads = cp.number("kv_heads"),
             dim = cp.number("head_dim"), layers = cp.number("layers");
    unsigned vocab = cp.number("vocab"), hidden = cp.number("hidden");
    double eps = std::stod(cp.meta.at("eps")),
           theta = std::stod(cp.meta.at("theta"));
    auto number = [&](const std::string &key, double fallback) {
      auto it = cp.meta.find(key);
      return it == cp.meta.end() ? fallback : std::stod(it->second);
    };
    double attention_scale =
        number("attention_multiplier", 1 / std::sqrt(double(dim)));
    double residual_scale = number("residual_multiplier", 1),
           embedding_scale = number("embedding_multiplier", 1),
           logits_scale = number("logits_scaling", 1);
    std::vector<LayerCache> cache(layers);
    std::vector<RecurrentCache> recurrent_cache(layers);
    std::vector<unsigned> generated, inputs, predictions;
    unsigned steps = unsigned(cp.prompt.size()) + cp.number("new_tokens") - 1;
    if (max_steps)
      steps = std::min(steps, max_steps);
    std::ofstream logitfile(output + "/systemc_logits.bin", std::ios::binary);
    std::ofstream hiddenfile(output + "/systemc_hidden.bin", std::ios::binary);
    if (!logitfile || !hiddenfile)
      throw std::runtime_error("output directory must exist");
    unsigned trace_layer =
        std::getenv("LLM_TRACE_LAYER")
            ? unsigned(std::stoul(std::getenv("LLM_TRACE_LAYER")))
            : 0;
    if (trace_layer >= layers)
      throw std::runtime_error("trace layer range");
    auto start = std::chrono::steady_clock::now();
    auto trace = [&](const std::string &name, const Tensor &value) {
      std::ofstream f(output + "/stage-" + name + ".bin", std::ios::binary);
      binary(f, value);
    };
    for (unsigned step = 0; step < steps; ++step) {
      unsigned token = step < cp.prompt.size() ? unsigned(cp.prompt[step])
                                               : generated.back();
      inputs.push_back(token);
      if (token >= vocab)
        throw std::runtime_error("token range");
      const auto embedding = cp.index.at("model.embed_tokens.weight");
      Tensor x{{cp.data(embedding) + token * hidden,
                cp.data(embedding) + (token + 1) * hidden},
               cp.row_exponent("model.embed_tokens.weight", token)};
      if (embedding_scale != 1)
        x = rt.constant(x, embedding_scale);
      binary(hiddenfile, x);
      for (unsigned layer = 0; layer < layers; ++layer) {
        std::string root = "model.layers." + std::to_string(layer) + ".";
        if (step == 0 && layer == trace_layer)
          trace("input", x);
        auto normalized =
            rt.norm(x, cp.vector(root + "input_layernorm.weight"), eps);
        if (family == "qwen3_5_text" &&
            cp.meta.at("layer_type_" + std::to_string(layer)) ==
                "linear_attention") {
          x = rt.add(x, gdn(normalized, cp, root + "linear_attn.",
                            recurrent_cache[layer], step, eps));
          normalized = rt.norm(
              x, cp.vector(root + "post_attention_layernorm.weight"), eps);
          auto product = rt.mul(
              rt.silu(rt.linear(normalized, cp, root + "mlp.gate_proj.weight")),
              rt.linear(normalized, cp, root + "mlp.up_proj.weight"));
          x = rt.add(x, rt.linear(product, cp, root + "mlp.down_proj.weight"));
          if (layer + 1 < layers)
            binary(hiddenfile, x);
          std::cout << "LAYER " << step << " " << layer << " GDN" << std::endl;
          continue;
        }
        Tensor ssm_output;
        if (family == "falcon_h1") {
          ssm_output = rt.constant(ssm(normalized, cp, root + "mamba.",
                                       recurrent_cache[layer], step, eps),
                                   number("ssm_out_multiplier", 1));
          normalized =
              rt.constant(normalized, number("attention_in_multiplier", 1));
        }
        if (step == 0 && layer == trace_layer)
          trace("inputnorm", normalized);
        Tensor q, k, v, attention_gate;
        if (family == "phi3") {
          auto fused =
              rt.linear(normalized, cp, root + "self_attn.qkv_proj.weight");
          q = slice(fused, 0, heads * dim);
          k = slice(fused, heads * dim, kvheads * dim);
          v = slice(fused, (heads + kvheads) * dim, kvheads * dim);
        } else {
          q = rt.linear(normalized, cp, root + "self_attn.q_proj.weight");
          k = rt.linear(normalized, cp, root + "self_attn.k_proj.weight");
          v = rt.linear(normalized, cp, root + "self_attn.v_proj.weight");
          if (family == "qwen3_5_text") {
            std::vector<Tensor> queries, gates;
            for (unsigned h = 0; h < heads; ++h) {
              queries.push_back(slice(q, h * 2 * dim, dim));
              gates.push_back(slice(q, h * 2 * dim + dim, dim));
            }
            q = concatenate(queries);
            attention_gate = concatenate(gates);
          }
        }
        if (family == "falcon_h1")
          k = rt.constant(k, number("key_multiplier", 1));
        if (step == 0 && layer == trace_layer) {
          trace("q", q);
          trace("k", k);
          trace("v", v);
        }
        if (cp.number("qk_norm")) {
          q = headnorm(q, cp.vector(root + "self_attn.q_norm.weight"), heads,
                       dim, eps);
          k = headnorm(k, cp.vector(root + "self_attn.k_norm.weight"), kvheads,
                       dim, eps);
        }
        // 每个K保留原尺度；打分前对整个prefix动态对齐，不能固定首token尺度。
        if (cp.index.count("rope." + std::to_string(layer))) {
          q = rt.rope_table(q, dim, cp, layer, step);
          k = rt.rope_table(k, dim, cp, layer, step);
        } else {
          q = rt.rope(q, dim, step, theta);
          k = rt.rope(k, dim, step, theta);
        }
        unsigned window = 0;
        if (family == "gemma3_text" &&
            cp.meta.at("layer_type_" + std::to_string(layer)) ==
                "sliding_attention")
          window = unsigned(cp.number("sliding_window"));
        auto av = attention(q, k, v, cache[layer], heads, kvheads, dim,
                            attention_scale, window);
        if (family == "qwen3_5_text")
          av = rt.mul(av,
                      rt.function(attention_gate, GCommand::Function::Sigmoid));
        auto projection = rt.linear(av, cp, root + "self_attn.o_proj.weight");
        if (family == "gemma3_text")
          projection =
              rt.norm(projection,
                      cp.vector(root + "post_attention_layernorm.weight"), eps);
        if (family == "falcon_h1")
          projection = rt.add(
              rt.constant(projection, number("attention_out_multiplier", 1)),
              ssm_output);
        if (residual_scale != 1)
          projection = rt.constant(projection, residual_scale);
        if (step == 0 && layer == trace_layer) {
          trace("av", av);
          trace("o", projection);
        }
        x = rt.add(x, projection);
        if (step == 0 && layer == trace_layer)
          trace("residual", x);
        normalized =
            rt.norm(x,
                    cp.vector(root + (family == "gemma3_text"
                                          ? "pre_feedforward_layernorm.weight"
                                      : family == "falcon_h1"
                                          ? "pre_ff_layernorm.weight"
                                          : "post_attention_layernorm.weight")),
                    eps);
        if (family == "granitemoe") {
          x = rt.add(x, rt.constant(moe(normalized, cp, root), residual_scale));
          if (layer + 1 < layers)
            binary(hiddenfile, x);
          std::cout << "LAYER " << step << " " << layer << " MoE" << std::endl;
          continue;
        }
        std::string mlp =
            root + (family == "falcon_h1" ? "feed_forward." : "mlp.");
        Tensor gp, up;
        if (family == "phi3") {
          auto fused = rt.linear(normalized, cp, mlp + "gate_up_proj.weight");
          unsigned n = unsigned(fused.v.size() / 2);
          gp = slice(fused, 0, n);
          up = slice(fused, n, n);
        } else {
          gp = rt.linear(normalized, cp, mlp + "gate_proj.weight");
          up = rt.linear(normalized, cp, mlp + "up_proj.weight");
        }
        if (family == "falcon_h1")
          gp = rt.constant(gp, number("mlp_multiplier_0", 1));
        auto gate = family == "gemma3_text" ? rt.gelu(gp) : rt.silu(gp);
        auto product = rt.mul(gate, up);
        auto down = rt.linear(product, cp, mlp + "down_proj.weight");
        if (family == "gemma3_text")
          down = rt.norm(
              down, cp.vector(root + "post_feedforward_layernorm.weight"), eps);
        if (family == "falcon_h1")
          down = rt.constant(down, number("mlp_multiplier_1", 1));
        if (step == 0 && layer == trace_layer) {
          trace("postnorm", normalized);
          trace("gp", gp);
          trace("gate", gate);
          trace("up", up);
          trace("product", product);
          trace("down", down);
        }
        x = rt.add(x, down);
        if (step == 0 && layer == trace_layer)
          trace("layer-result", x);
        if (step == 0 && layer == 0 && std::getenv("LLM_FIRST_LAYER_ONLY")) {
          trace("layer", x);
          return;
        }
        // 与HF hidden_states一致：末层的最后一个记录在最终RMS之后。
        if (layer + 1 < layers)
          binary(hiddenfile, x);
        std::cout << "LAYER " << step << " " << layer << " exponent " << x.e
                  << std::endl;
      }
      if (step == 0)
        trace("final-pre-norm", x);
      x = rt.norm(x,
                  cp.vector(family == "falcon_h1"
                                ? "model.final_layernorm.weight"
                                : "model.norm.weight"),
                  eps);
      if (step == 0)
        trace("final-post-norm", x);
      binary(hiddenfile, x);
      auto logits = rt.linear(x, cp,
                              cp.index.count("lm_head.weight")
                                  ? "lm_head.weight"
                                  : "model.embed_tokens.weight");
      if (logits_scale != 1)
        logits = rt.constant(logits, 1 / logits_scale);
      if (family == "falcon_h1")
        logits = rt.constant(logits, number("lm_head_multiplier", 1));
      logits = rt.handoff(logits);
      binary(logitfile, logits);
      unsigned next = rt.argmax(logits);
      predictions.push_back(next);
      if (step + 1 >= cp.prompt.size())
        generated.push_back(next);
      std::cout << "TOKEN " << step << " input " << token << " next " << next
                << std::endl;
    }
    std::ofstream receipt(output + "/systemc_receipt.json");
    auto list = [&](const char *name, const std::vector<unsigned> &v) {
      receipt << "\"" << name << "\":[";
      for (size_t i = 0; i < v.size(); ++i) {
        if (i)
          receipt << ",";
        receipt << v[i];
      }
      receipt << "],\n";
    };
    receipt << "{\n\"family\":\"" << family
            << "\",\n\"transport\":\"real Accellera SC_THREAD, FIFO depth 1, "
               "untimed\",\n";
    receipt << "\"precision_adapter\":\""
            << (Runtime::precise() ? "candidate-v10" : "legacy") << "\",\n";
    receipt << "\"activation_scale_policy\":\""
            << (rt.block_mode ? "N8 core scales; per-lane host/trace metadata; "
                                "N stats common, replay local"
                              : "uniform")
            << "\",\n";
    receipt << "\"weight_scale_policy\":\""
            << (cp.group_scales.empty() ? "per-tensor" : "per-output-N8")
            << "\",\n";
    receipt << "\"weight_residual_terms\":"
            << (cp.meta.count("weight_residual_terms")
                    ? cp.number("weight_residual_terms")
                    : 1)
            << ",\n";
    receipt << "\"silu_adapter\":\""
            << (std::getenv("LLM_ACCURATE_SILU")
                    ? "range-reduced-N-exp, Newton reciprocal, M/E"
                    : "G-Q14-sigmoid times x")
            << "\",\n";
    receipt << "\"external_scale_values_materialized\":"
            << rt.external_scale_values_materialized
            << ",\"uniform_scale_conversions\":" << rt.uniform_scale_conversions
            << ",\n";
    receipt << "\"norm_adapter\":\""
            << (Runtime::precise() || std::getenv("LLM_NORM_FUSED")
                    ? "fused-scaled-gamma"
                    : "unit-N-then-E-gamma")
            << "\",\n";
    list("inputs", inputs);
    list("next_ids", predictions);
    list("generated", generated);
    receipt << "\"matmuls\":" << rt.matmuls << ",\"macs\":" << rt.macs
            << ",\"software_R_boundary_format_values\":"
            << recurrence.software_boundary_values
            << ",\"software_scale_decisions\":" << rt.scale_decisions << ",\n";
    receipt << "\"transactions\":{\"M\":" << rt.m.transactions
            << ",\"N\":" << rt.n.transactions << ",\"E\":" << rt.e.transactions
            << ",\"G\":" << rt.g.transactions << ",\"R\":" << rt.r.transactions
            << ",\"S\":" << rt.s.transactions << ",\"T\":" << rt.t.transactions
            << "},\n";
    receipt << "\"saturated_transactions\":{\"M\":" << rt.m.saturations
            << ",\"N\":" << rt.n.saturations << ",\"E\":" << rt.e.saturations
            << ",\"G\":" << rt.g.saturations << "},\n";
    receipt << "\"e_saturation_ops\":{";
    bool first_op = true;
    for (const auto &entry : rt.e.saturation_ops) {
      if (!first_op)
        receipt << ',';
      receipt << '\"' << entry.first << "\":" << entry.second;
      first_op = false;
    }
    receipt << "},\n";
    receipt << "\"host_seconds\":"
            << std::chrono::duration<double>(std::chrono::steady_clock::now() -
                                             start)
                   .count()
            << "}\n";
  }
  void run() {
    try {
      if (selftest)
        tests();
      else
        infer();
    } catch (const std::exception &ex) {
      error = ex.what();
      std::cerr << "LLM_FAILED " << error << std::endl;
    }
    sc_core::sc_stop();
  }

public:
  std::string error;
  SC_HAS_PROCESS(Driver);
  Driver(sc_core::sc_module_name name, std::string dir, std::string out,
         bool test, unsigned steps)
      : sc_module(name), directory(std::move(dir)), output(std::move(out)),
        selftest(test), max_steps(steps) {
    SC_THREAD(run);
  }
};
int sc_main(int argc, char **argv) {
  bool test = argc == 2 && std::string(argv[1]) == "--selftest";
  if (!test && argc < 3) {
    std::cerr
        << "llm_bench CHECKPOINT_DIR OUTPUT_DIR [MAX_STEPS] | --selftest\n";
    return 2;
  }
  Driver driver("llm", test ? "" : argv[1], test ? "" : argv[2], test,
                argc > 3 ? unsigned(std::stoul(argv[3])) : 0);
  sc_core::sc_start();
  return driver.error.empty() ? 0 : 1;
}
