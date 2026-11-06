
"""Add per-token observers to the isolated PR #154 C/D build."""
import argparse
from pathlib import Path


def insert(path, anchor, addition):
    source = path.read_text()
    if source.count(anchor) != 1:
        raise ValueError("observer anchor changed: " + str(path))
    path.write_text(source.replace(anchor, anchor + addition))


PROFILE = r"""
    std::ofstream length_profile(output + "/length-steps.csv");
    if (!length_profile)
      throw std::runtime_error("cannot open length profile");
    length_profile << "context_tokens,phase,kv_token_entries,kv_values_bytes,"
                      "kv_scale_bytes,r_state_bytes,r_history_values_bytes,"
                      "r_history_scale_bytes,cd_windows,cd_words,cd_bursts,macs\n";
    auto tensor_bytes = [](const Tensor &tensor) {
      const uint64_t payload = uint64_t(tensor.v.size()) * sizeof(int16_t);
      const uint64_t scales = (tensor.lane_e.empty() ? 1 : tensor.lane_e.size())
          * sizeof(int32_t);
      return std::make_pair(payload, scales);
    };
"""

STEP = r"""
      uint64_t kv_tokens = 0, kv_values = 0, kv_scales = 0;
      uint64_t r_state = 0, r_history_values = 0, r_history_scales = 0;
      for (const auto &layer : cache) {
        if (layer.keys.size() != layer.values.size())
          throw std::runtime_error("KV cache length mismatch");
        kv_tokens += layer.keys.size();
        for (const auto &key : layer.keys) {
          const auto bytes = tensor_bytes(key);
          kv_values += bytes.first;
          kv_scales += bytes.second;
        }
        for (const auto &value : layer.values) {
          const auto bytes = tensor_bytes(value);
          kv_values += bytes.first;
          kv_scales += bytes.second;
        }
      }
      for (const auto &layer : recurrent_cache) {
        r_state += layer.state.size() * sizeof(int32_t);
        for (const auto &history : layer.history) {
          const auto bytes = tensor_bytes(history);
          r_history_values += bytes.first;
          r_history_scales += bytes.second;
        }
      }
      const auto activity = rt.link.cd_activity();
      length_profile << step + 1 << ','
                     << (step < cp.prompt.size() ? "prefill" : "decode") << ','
                     << kv_tokens << ',' << kv_values << ',' << kv_scales << ','
                     << r_state << ',' << r_history_values << ',' << r_history_scales
                     << ',' << activity[0] << ',' << activity[1] << ',' << activity[2]
                     << ',' << rt.macs << std::endl;
"""

CD = r"""
  std::array<uint64_t, 3> cd_activity() const {
    return {cd_.windows, cd_.words, cd_.burst_count};
  }
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("systemc", type=Path)
    args = parser.parse_args()
    driver = args.systemc / "llm/llm_bench.cpp"
    insert(driver, '    if (!logitfile || !hiddenfile)\n      throw std::runtime_error("output directory must exist");\n', PROFILE)
    insert(driver, '      if (step + 1 >= cp.prompt.size())\n        generated.push_back(next);\n', STEP)
    insert(args.systemc / "llm/tensor_link.hpp", "public:\n", CD)


if __name__ == "__main__":
    main()
