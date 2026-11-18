"""Remove spacing-only instructions from a DEF copy, retaining every routing coordinate."""
from pathlib import Path
import re
import sys

source, target = map(Path, sys.argv[1:])
contents = source.read_text()
section = re.search(r"^NONDEFAULTRULES 2 ;\n.*?^END NONDEFAULTRULES\n", contents, re.M | re.S)
assert section
names = set(re.findall(r"^\s*- (i289_upper_v2_(?:m9|m9m10)_1200)$", section[0], re.M))
assert len(names) == 2
native = dict(zip(range(1, 11), [140, 140, 140, 280, 280, 280, 800, 800, 1600, 1600]))
widths = re.findall(r"\+ LAYER metal(\d+) WIDTH (\d+) SPACING \d+", section[0])
assert len(widths) == 20 and all(native[int(layer)] == int(width) for layer, width in widths)
contents = contents[:section.start()] + contents[section.end():]
net_section = re.search(r"^NETS \d+ ;\n.*?^END NETS\n", contents, re.M | re.S)
assert net_section
count = 0

def normalize(match):
    global count
    net = match[0]
    rule = re.search(r" \+ NONDEFAULTRULE (\S+)", net)
    if not rule:
        return net
    assert rule[1] in names
    count += 1
    net = net[:rule.start()] + net[rule.end():]
    return re.sub(r"((?:\+ ROUTED|\bNEW) metal\d+) TAPER\b", r"\1", net)

nets = re.sub(r"^\s*- \S+ .*?;", normalize, net_section[0], flags=re.M | re.S)
assert count == 8 and 'NONDEFAULTRULE' not in nets
target.write_text(contents[:net_section.start()] + nets + contents[net_section.end():])
