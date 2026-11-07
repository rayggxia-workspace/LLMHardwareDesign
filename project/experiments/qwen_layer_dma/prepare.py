"""Create isolated two-layer SystemC and native-RTL drivers from frozen replay source."""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import sys

root, baseline, original = map(Path, sys.argv[1:])
source = root / "source"
source.mkdir()
for name in ("include", "llm"):
    shutil.copytree(original / name, source / name)
shutil.copyfile(root / "native_engines.hpp", source / "include/blocks/native_engines.hpp")
shutil.copyfile(root / "native_memory.hpp", source / "include/blocks/native_memory.hpp")

def edit(path, before, after, count=1):
    text = path.read_text()
    if text.count(before) != count:
        raise ValueError((str(path), before, text.count(before)))
    path.write_text(text.replace(before, after))

header = source / "llm/external_memory.hpp"
# A 16-byte header and zero tail lanes give the native word DMA an explicit ABI.
edit(header, "sizeof(int32_t) + count * 6", "16 + count * 6")
edit(header, "sizeof(int32_t) + count * (lanes_ ? 6 : 2)", "(16 + count * (lanes_ ? 6 : 2) + 15) / 16 * 16", 2)
edit(header, "+ sizeof(int32_t)", "+ 16", 6)
# Full tensor record transfer has a padded tail. Slice reads retain valid bytes.
edit(header, "#include <algorithm>", '#include <algorithm>\n#ifdef USE_NATIVE_RTL\n#include "native_memory.hpp"\n#endif')
edit(header, """    if (packet.is_write())
      std::memcpy(storage + offset, packet.get_data_ptr(), count);
    else
      std::memcpy(packet.get_data_ptr(), storage + offset, count);""", """#ifdef USE_NATIVE_RTL
    layer::memory().transfer(index, address, storage, extent, packet.get_data_ptr(), count, packet.is_write());
#else
    if (packet.is_write())
      std::memcpy(storage + offset, packet.get_data_ptr(), count);
    else
      std::memcpy(packet.get_data_ptr(), storage + offset, count);
#endif""")

recurrence = source / "llm/recurrent.hpp"
edit(recurrence, "rt.offchip.write(MemoryKind::RState, cache.external_state, &cache.exponent, sizeof(int32_t));",
"""{
        const std::array<int32_t, 4> metadata{cache.exponent, 0, 0, 0};
        rt.offchip.write(MemoryKind::RState, cache.external_state, metadata.data(), 16);
      }""")

modules = source / "include/blocks/modules.hpp"
edit(modules, "#include <systemc>", '#include <systemc>\n#ifdef USE_NATIVE_RTL\n#include "native_engines.hpp"\n#endif')
edit(modules, "    Engine engine_;", """#ifdef USE_NATIVE_RTL
    typename NativeEngine<Engine>::type engine_;
#else
    Engine engine_;
#endif""")

driver = source / "llm/llm_bench.cpp"
edit(driver, "  void infer() {", """
  std::array<std::array<Tensor, 4>, 2> fixture;
  std::ofstream layer_outputs, layer_counts, rtl_counts;
  void finish_layer(unsigned step, unsigned id, const Tensor &x) {
    const auto &expected = fixture.at(step).at(id == 0 ? 1 : 3);
    check(x.v == expected.v && x.e == expected.e && x.lane_e == expected.lane_e,
          "selected full layer differs from frozen output");
    binary(layer_outputs, x);
    rt.offchip.report(layer_counts, step * 32 + id, id == 0 ? "gdn" : "attention");
#ifdef USE_NATIVE_RTL
    layer::memory().report(rtl_counts, step, id);
#endif
    std::cout << "SELECTED_LAYER_PASS step=" << step << " layer=" << id << std::endl;
  }
  void infer() {""")
edit(driver, "    auto family = cp.meta.at(\"family\");", """    std::ifstream input_fixture(directory + "/layer-fixture.bin", std::ios::binary);
    for (auto &step : fixture)
      for (auto &tensor : step) {
        uint32_t count;
        input_fixture.read(reinterpret_cast<char *>(&tensor.e), 4);
        input_fixture.read(reinterpret_cast<char *>(&count), 4);
        check(bool(input_fixture) && count == 2560, "selected layer fixture header");
        tensor.v.resize(count);
        input_fixture.read(reinterpret_cast<char *>(tensor.v.data()), count * 2);
        check(bool(input_fixture), "selected layer fixture payload");
      }
    layer_outputs.open(output + "/layer-outputs.bin", std::ios::binary);
    layer_counts.open(output + "/layer-traffic.csv");
    rtl_counts.open(output + "/rtl-memory.csv");
    layer_counts << "position,phase,kind,direction,requests,bursts,payload_bytes,bus_bytes\\n";
    rtl_counts << "step,layer,kind,read_requests,write_requests,read_bytes,write_bytes,cycles,descriptors\\n";
    auto family = cp.meta.at("family");""")
edit(driver, '    unsigned steps = unsigned(cp.prompt.size()) + cp.number("new_tokens") - 1;', "    unsigned steps = 2;")
edit(driver, "    double residual_scale =", "    [[maybe_unused]] double residual_scale =")
edit(driver, "    unsigned vocab =", "    [[maybe_unused]] unsigned vocab =")
text = driver.read_text()
a = text.index('      const auto embedding = cp.index.at("model.embed_tokens.weight");')
b = text.index("      for (unsigned layer = 0; layer < layers; ++layer) {", a)
text = text[:a] + "      Tensor x;\n" + text[b:]
driver.write_text(text)
edit(driver, "      for (unsigned layer = 0; layer < layers; ++layer) {", """      for (unsigned layer = 0; layer < layers; ++layer) {
        if (layer != 0 && layer != 3)
          continue;
        x = fixture.at(step).at(layer == 0 ? 0 : 2);""")
edit(driver, '          std::cout << "LAYER " << step << " " << layer << " GDN"', '          finish_layer(step, layer, x);\n          std::cout << "LAYER " << step << " " << layer << " GDN"')
edit(driver, "        x = rt.add(x, down);", "        x = rt.add(x, down);\n        finish_layer(step, layer, x);")
text = driver.read_text()
a = text.index('      if (step == 0)\n        trace("final-pre-norm", x);')
b = text.index("    rt.flow.finish();", a)
text = text[:a] + "    }\n" + text[b:]
driver.write_text(text)

case = root / "case"
case.mkdir()
for path in (baseline / "case-qwen35").iterdir():
    if path.is_file():
        (case / path.name).symlink_to(path.resolve())
hidden = baseline / "long-qwen35/systemc_hidden.bin"
frozen = json.loads((root / "long-systemc-results.json").read_text())["models"]["qwen35"]
if hashlib.sha256(hidden.read_bytes()).hexdigest() != frozen["output_sha256"]["systemc_hidden.bin"]:
    raise ValueError("frozen hidden hash mismatch")
raw = hidden.read_bytes()
record = 8 + 2560 * 2
assert len(raw) == 24 * 33 * record
selected = bytearray()
for step in range(2):
    for layer_boundary in (0, 1, 3, 4):
        start = (step * 33 + layer_boundary) * record
        selected.extend(raw[start:start + record])
(case / "layer-fixture.bin").write_bytes(selected)
manifest = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(source.rglob("*")) if path.is_file()}
manifest["case/layer-fixture.bin"] = hashlib.sha256(selected).hexdigest()
(root / "generated-inputs.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
