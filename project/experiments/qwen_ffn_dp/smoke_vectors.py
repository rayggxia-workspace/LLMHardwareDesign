"""Small local operand smoke for SystemC and image loaders, without checkpoint claims."""
from pathlib import Path
import random
import sys

from compile_slice import K
from vectors import mid, pack, rne, vectors

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
rng = random.Random(192)
a = [rng.randrange(-32, 33) for _ in range(K)]
values = []
for op in ("gate", "up"):
    w = [[rng.randrange(-16, 17) for _ in a] for _ in range(2)]
    values.append([rne(sum(x*y for x,y in zip(a, row, strict=True)), 2) for row in w])
    (out / f"{op}.hex").write_text(
        "".join(f"{word:032x}\n" for word in vectors(a, w)), encoding="ascii")
values.append(mid(*values))
(out / "expected.hex").write_text(
    "".join(f"{pack(row, 16):032x}\n" for row in values), encoding="ascii")
