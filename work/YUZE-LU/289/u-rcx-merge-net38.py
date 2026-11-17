"""Replace two overlapping collinear M10 segments with their exact union."""
from pathlib import Path
import re
import sys

source, target = map(Path, sys.argv[1:])
contents = source.read_text()
name = re.escape(r"datapath.legacy_rsp_data\[38\]")
match = re.search(r"^\s*- " + name + r" .*?;", contents, re.M | re.S)
assert match
net = match[0]
outer = "      NEW metal10 ( 570000 120140 0 ) ( 572990 * )\n"
inner = "      NEW metal10 ( 569790 120140 0 ) ( 570000 * )\n"
assert net.count(outer) == net.count(inner) == 1
# The two rectangles are [570000,573790] and [569790,570800]
# with the same Y interval, hence this single rectangle has the same union.
merged = "      NEW metal10 ( 569790 120140 0 ) ( 572990 * )\n"
target.write_text(contents[:match.start()] + net.replace(outer, merged).replace(inner, "")
                  + contents[match.end():])
