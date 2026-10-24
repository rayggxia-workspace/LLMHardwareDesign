"""Issue74 independent receipt primitives; no producer imports.

Only small synthetic inputs are used in local tests.  Artifact and numerical
receivers run against actual captures on the authorized server.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re


def need(condition, label):
    if not condition:
        raise ValueError(label)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def descriptor(path):
    return {"bytes": Path(path).stat().st_size, "sha256": sha(path)}


def child(root, relative):
    need(isinstance(relative, str) and relative and "\\" not in relative
         and ":" not in relative and not Path(relative).is_absolute(), "artifact path")
    root = Path(root).resolve()
    result = (root / relative).resolve()
    need(result != root and result.is_relative_to(root), "artifact escape")
    return result


def verify_manifest(folder, *, kind=None, statuses=()):
    root = Path(folder)
    manifest = load_json(root / "manifest.json")
    if kind is not None:
        need(manifest.get("kind", manifest.get("schema")) == kind, "manifest kind")
    if statuses:
        need(manifest.get("status") in statuses, "manifest execution status")
    entries = manifest.get("artifacts")
    if isinstance(entries, list):
        names = [entry["path"] for entry in entries]
        need(len(names) == len(set(names)), "duplicate artifact")
        entries = dict(zip(names, entries))
    need(isinstance(entries, dict) and bool(entries), "artifact index")
    checked = {}
    for name, wanted in entries.items():
        need(re.fullmatch("[0-9a-f]{64}", wanted.get("sha256", "")) is not None,
             "artifact SHA format")
        actual = descriptor(child(root, name))
        need(actual == {key: wanted[key] for key in ("bytes", "sha256")},
             "artifact hash/size " + name)
        checked[name] = actual
    return manifest, checked


def replace_artifact_hash(folder, name):
    """For explicit negative tests after an actual artifact mutation only."""
    root = Path(folder)
    manifest = load_json(root / "manifest.json")
    entries = manifest["artifacts"]
    if isinstance(entries, list):
        found = [entry for entry in entries if entry["path"] == name]
        need(len(found) == 1, "negative artifact membership")
        found[0].update(descriptor(child(root, name)))
    else:
        need(name in entries, "negative artifact membership")
        entries[name].update(descriptor(child(root, name)))
    save_json(root / "manifest.json", manifest)


def source_binding(manifest, sources):
    """Check the actual source bytes, not merely a producer-reported commit."""
    binding = manifest.get("source", {})
    need(re.fullmatch("[0-9a-f]{40}", binding.get("commit", "")) is not None,
         "source commit")
    hashes = {}
    for field, path in sources.items():
        hashes[field] = sha(path)
        need(binding.get(field) == hashes[field], "source SHA " + field)
    return hashes


def integer(value):
    need(type(value) is int, "Python integer required")
    return value


def checked(value, bits):
    value, bits = integer(value), integer(bits)
    need(2 <= bits <= 256, "signed width")
    need(-(1 << (bits - 1)) <= value < 1 << (bits - 1), "signed overflow")
    return value


def rational_rne(numerator, denominator):
    """Signed nearest/even defined through floor and exact rational distance."""
    n, d = integer(numerator), integer(denominator)
    need(d > 0, "positive denominator")
    value = Fraction(n, d)
    lo = value.numerator // value.denominator
    distance = value - lo
    return lo + int(distance > Fraction(1, 2) or
                    (distance == Fraction(1, 2) and lo % 2 != 0))


def shift_rne(value, shift):
    value, shift = integer(value), integer(shift)
    need(-256 <= shift <= 256, "bounded shift")
    return rational_rne(value, 1 << shift) if shift >= 0 else value << -shift


def restoring_division(numerator, denominator, bits=128):
    """Unsigned division with one explicitly declared iteration per bit."""
    n, d, bits = integer(numerator), integer(denominator), integer(bits)
    need(1 <= bits <= 256 and 0 <= n < 1 << bits and d > 0, "division domain")
    q = r = 0
    for bit in range(bits - 1, -1, -1):
        r = (r << 1) | ((n >> bit) & 1)
        q <<= 1
        if r >= d:
            r -= d
            q |= 1
    need(q * d + r == n and 0 <= r < d, "division identity")
    return q, r


def divided_rne(numerator, denominator, bits=128):
    n, d = integer(numerator), integer(denominator)
    q, r = restoring_division(abs(n), d, bits)
    q += int(2 * r > d or (2 * r == d and q & 1))
    return -q if n < 0 else q


def square_root(radicand, bits=128):
    """Fixed digit-pair restoring integer square root, no float bridge."""
    n, bits = integer(radicand), integer(bits)
    need(1 <= bits <= 256 and 0 <= n < 1 << bits, "sqrt domain")
    q = r = 0
    for pair in range((bits + 1) // 2 - 1, -1, -1):
        r = (r << 2) | ((n >> (2 * pair)) & 3)
        trial = (q << 2) | 1
        q <<= 1
        if r >= trial:
            r -= trial
            q |= 1
    need(q * q <= n < (q + 1) * (q + 1), "sqrt bracket")
    return q


def s8_digits(value, bits):
    """Native signed-high radix128: widths8/16/32/64 use1/3/5/9 digits."""
    value = checked(integer(value), integer(bits))
    count = 1 if bits <= 8 else 1 + (bits - 8 + 6) // 7
    remain, digits = value, []
    for _ in range(count - 1):
        digits.append(remain & 127)
        remain >>= 7
    digits.append(remain)
    need(all(-128 <= x <= 127 for x in digits), "S8 digit domain")
    need(sum(x << (7 * i) for i, x in enumerate(digits)) == value, "digit reconstruction")
    return digits


def lowered_product(a, b, a_bits, b_bits, result_bits=128):
    left, right = s8_digits(a, a_bits), s8_digits(b, b_bits)
    result = 0
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            result = checked(result + ((x * y) << (7 * (i + j))), result_bits)
    need(result == a * b, "digit multiplication")
    return result, len(left) * len(right)


def wire_packets(source, destination, length, payload=1984):
    """Finite 128-bit BUS,32-byte header,padded payload and leading bank beat."""
    source, destination, length = integer(source), integer(destination), integer(length)
    need(source >= 0 and destination >= 0 and length > 0 and payload == 1984,
         "packet domain")
    total = {"payload_bytes": length, "wire_bytes": 0, "packets": 0,
             "src_beats": 0, "dst_beats": 0, "bus_beats": 0, "max_fifo_bytes": 0}
    offset = 0
    while offset < length:
        n = min(payload, length - offset)
        wire = 32 + ((n + 15) // 16) * 16
        need(wire <= 2048, "finite packet FIFO")
        total["wire_bytes"] += wire
        total["packets"] += 1
        total["src_beats"] += ((source + offset) % 16 + n + 15) // 16
        total["dst_beats"] += ((destination + offset) % 16 + n + 15) // 16
        total["bus_beats"] += wire // 16
        total["max_fifo_bytes"] = max(total["max_fifo_bytes"], wire)
        offset += n
    return total
