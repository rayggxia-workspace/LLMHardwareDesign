"""Compare original elaborated ports with generated LEF, Liberty and wrapper."""
import json
import os
from pathlib import Path
import re

root = Path.cwd()
block = Path(os.environ["LLHD_BLOCK"])
result = block / "flow/results/nangate45/llhd_vec_original/base"
ports = json.loads((block / "vec-elab.json").read_text())["modules"]["vec_engine"]["ports"]
expected = set()
expected_directions = {}
for name, port in ports.items():
    width = len(port["bits"])
    names = [name] if width == 1 else [f"{name}[{i}]" for i in range(width)]
    expected.update(names)
    expected_directions.update({bit: port["direction"].lower() for bit in names})
lef_text = (result / "vec_engine.lef").read_text()
lib_text = (result / "vec_engine_typ.lib").read_text()
lef_pins = {name.replace("\\", "") for name in re.findall(r"(?m)^\s*PIN\s+(\S+)", lef_text)}
lib_pins = set(re.findall(r'\bpin\s*\(\s*"?([^\s"()]+)"?\s*\)', lib_text))
assert expected <= lef_pins, sorted(expected - lef_pins)
assert expected <= lib_pins, sorted(expected - lib_pins)
lef_directions = {}
for pin in re.finditer(r"(?m)^\s*PIN\s+(\S+)", lef_text):
    name = pin.group(1)
    end = lef_text.find("END " + name, pin.end())
    direction = re.search(r"\bDIRECTION\s+(INPUT|OUTPUT|INOUT)\s*;", lef_text[pin.end():end])
    if direction:
        lef_directions[name.replace("\\", "")] = direction.group(1).lower()
lib_directions = {}
matches = list(re.finditer(r'\bpin\s*\(\s*"?([^\s"()]+)"?\s*\)', lib_text))
for i, pin in enumerate(matches):
    end = matches[i + 1].start() if i + 1 < len(matches) else len(lib_text)
    direction = re.search(r"\bdirection\s*:\s*(input|output|inout)\s*;", lib_text[pin.end():end])
    if direction:
        lib_directions[pin.group(1)] = direction.group(1)
for name, direction in expected_directions.items():
    assert lef_directions.get(name) == direction, ("LEF", name, lef_directions.get(name), direction)
    assert lib_directions.get(name) == direction, ("Liberty", name, lib_directions.get(name), direction)
assert "OBS" in lef_text, "macro abstract must describe route obstruction geometry"
wrapper = (root / "top.v").read_text()
for name, port in ports.items():
    assert f".{name}({name})" in wrapper
report = {
    "pass": True,
    "rtl_port_count": len(ports), "rtl_signal_bits": len(expected),
    "lef_pin_count": len(lef_pins), "liberty_pin_count": len(lib_pins),
    "extra_lef_pins": sorted(lef_pins - expected),
    "extra_liberty_pins": sorted(lib_pins - expected),
    "lef_obstructions_present": True,
    "wrapper_is_direct": True,
    "lef_and_liberty_signal_directions_match_rtl": True,
}
(root / "port-validation.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
