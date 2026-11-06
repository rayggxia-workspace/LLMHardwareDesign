"""Materialize only the checkpoint rows needed for the FFN experiment."""
import argparse
import json
from pathlib import Path
import struct
import urllib.request

REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
BASE = f"https://huggingface.co/Qwen/Qwen3.5-4B/resolve/{REVISION}"


def get(name, region=None):
    url = f"{BASE}/{name}"
    headers = {}
    if region:
        start, end = region
        headers["Range"] = f"bytes={start}-{end}"
        url += f"?download=true&ffn_range={start}-{end}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=35) as response:
        if region:
            content_range = response.headers.get("Content-Range", "")
            if response.status != 206 or not content_range.startswith(f"bytes {start}-{end}/"):
                raise ValueError(f"server did not honor requested range: {response.status}, {content_range}")
            result = response.read(end-start+2)
            if len(result) != end-start+1:
                raise ValueError("truncated range")
            return result
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--rows", type=int, default=12)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "model.safetensors.index.json"):
        (out / name).write_bytes(get(name))
    index = json.loads((out / "model.safetensors.index.json").read_bytes())["weight_map"]
    selected = {}
    for op in ("gate_proj", "up_proj"):
        key, = [k for k in index if k.startswith("model.") and k.endswith(f".layers.{args.layer}.mlp.{op}.weight")]
        selected.setdefault(index[key], []).append(key)
    for name, keys in selected.items():
        prefix = get(name, (0, 7))
        length, = struct.unpack("<Q", prefix)
        if not 1 <= length <= 4_000_000:
            raise ValueError("unexpected safetensors header size")
        header = get(name, (8, length + 7))
        entries = json.loads(header)
        with (out / name).open("wb") as file:
            file.write(prefix + header)
            for key in keys:
                entry = entries[key]
                rows, width = entry["shape"]
                if entry["dtype"] != "BF16" or not 1 <= args.rows <= rows:
                    raise ValueError(f"bad tensor {key}")
                start = 8 + length + entry["data_offsets"][0]
                end = start + 2 * width * args.rows - 1
                file.seek(start)
                file.write(get(name, (start, end)))
                print(f"{key} {args.rows} rows", flush=True)
    (out / "ffn-sparse-range.json").write_text(
        json.dumps({"revision": REVISION, "layer": args.layer, "rows": args.rows}, indent=2) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
