"""Independent W8/A16 Gate/Up and G32/Mid numeric oracle for the native test."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from ffn_scope_emit import descriptors, layout


def pack(values, width):
    return sum((v % (1 << width)) << (width*i) for i,v in enumerate(values))


def write(path, values, bytes_per_line):
    path.write_text("".join(f"{v:0{bytes_per_line*2}x}\n" for v in values), encoding="ascii")


def vectors(root, out, columns, seed, down, split_up_channel=False):
    sys.path.insert(0, str(root/"project/experiments/w8a16_g"))
    from reference import packet, rne
    assert columns in (384, 11008)
    out.mkdir(parents=True, exist_ok=False)
    spec = dict(topology=25001, scope_generation_job_epoch=[1,1,9], first_local_sequence_by_p=[1]*3,
        x_tensor_version=[8,7], mid_tensor_version=[9,1], rf_object_bases=dict(gate=4096,up=8192,down=12288),
        output_version=4, record_sequence_base=1, descriptor_base=4096)
    spec["packed_weights"] = {name:dict(base=(i+1)*0x2000000+(2048 if name=="up" and split_up_channel else 0), bytes=layout(2048,11008),
        format="W8A16_n8_k128_ordinary_1088_v1",
        sha256=hashlib.sha256(f"synthetic fixture {name}, seed {seed}".encode()).hexdigest())
        for i,name in enumerate(("gate","up","down"))}
    raw, meta = descriptors(spec)
    assert not down or columns == 11008
    count = 192 if down else 3*((columns+191)//192)
    write(out/"scopes.hex", (int.from_bytes(raw[i*128:(i+1)*128],"little") for i in range(count)),128)
    a = [(((i*13+(i//128)*11)%19)-9)*256 for i in range(2048)]
    write(out/"X.hex",(pack(a[i:i+4],32) for i in range(0,2048,4)),16)
    # The weight polynomial is evaluated with scalar integer arithmetic,
    # separately from the SV 64-byte frame packing and M datapath.
    projected = []
    for way in range(2):
        result = []
        for c in range(15):
            # FP16 scale 0x1c00 is 2^-8 and the real source shift is zero.
            # Each A16 is divisible by 256, so every per-K128 RNE is exact.
            result.append(sum((x//256)*((((c+7)*(i%31+3)+(i//128)*13+way*17+seed)%15)-7)
                              for i,x in enumerate(a)))
        projected.append([result[c%15] for c in range(columns)])
    mid = []
    for c in range(0,columns,2):
        pair,bad = packet(projected[0][c:c+2],projected[1][c:c+2],True,3)
        assert not bad
        mid.extend(pair)
    words = []
    source = []
    for i in range(0,columns,128):
        tile = mid[i:i+128]
        maximum = max(map(abs,tile))
        shift = next(s for s in range(18) if maximum <= (32767 << s))
        tile = [rne(v,shift) for v in tile]
        words.extend([shift]+[pack(tile[j:j+8],16) for j in range(0,128,8)])
        source.extend(v << shift for v in tile)
    write(out/"Mid.hex",words,16)
    if down:
        # Down's W scale is one (FP16 0x3c00). Restore the true, per-K
        # A16 shift before accumulating the independent scalar terms.
        down_period = [sum(v*((((c+7)*(i%31+3)+(i//128)*13+34+seed)%15)-7)
                        for i,v in enumerate(source)) for c in range(15)]
        assert any(down_period) and all(-2**31 <= v < 2**31 for v in down_period)
        for_p = [[],[],[]]
        for c in range(0,2048,8):
            p = c//8%3
            for_p[p].extend(pack((down_period[(c+half+j)%15] for j in range(4)),32) for half in (0,4))
        assert [len(x) for x in for_p] == [172,170,170]
        write(out/"Down.hex",(w for xs in for_p for w in xs+[0]*(172-len(xs))),16)
    note = dict(seed=seed, columns=columns, descriptor_count=count, original_four_bank_S=True,
        synthetic_DDR_provider=True, deployment_weight_images_verified=False, down=down, split_up_channel=split_up_channel,
        first_descriptors=meta["scopes"][:count], mid_tiles=len(words)//17,
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    (out/"oracle.json").write_text(json.dumps(note,indent=2)+"\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--columns", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--down", action="store_true")
    p.add_argument("--split-up-channel", action="store_true")
    a = p.parse_args()
    vectors(a.root,a.out,a.columns,a.seed,a.down,a.split_up_channel)


if __name__ == "__main__":
    main()
