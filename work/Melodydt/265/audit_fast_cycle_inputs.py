"""Recover three-P FFN control order independently of the RTL timing logs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
import zlib


ARCHIVES = {
    102603: "f1ef4555cb5dcbac48f79d65c8b5ebde4d1b59e44cae55af42b38dabae777b8f",
    102604: "bc072788c2648b6008c0c6c18000ec33df8147ed0ae38c545ad6f86ca1920712",
}
SEED = 25001
CONTROL_ABI = 0x02500002
EXPECTED_BURSTS = 1_123_200
EXPECTED_ON_CHIP_WRITES = 96_256


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uint(data, offset, size):
    return int.from_bytes(data[offset:offset + size], "little")


def decode_hex(data, width):
    for row in data.splitlines():
        require(len(row) == 2 * width and re.fullmatch(rb"[0-9a-fA-F]+", row),
                "invalid hexadecimal memory row")
        yield int(row, 16).to_bytes(width, "little")


def control_image(data, version, role):
    image = b"".join(decode_hex(data, 16))
    require(len(image) >= 128 and image[:8] == b"LBCISA01"
            and uint(image, 8, 2) == version and image[10:12] == bytes([role, 8]),
            "unsupported control image header")
    size, count, offset = (uint(image, at, 4) for at in (12, 20, 24))
    require(size == len(image) and offset == 128 and 0 < count <= (size - offset) // 8
            and uint(image, 64, 4) == SEED and uint(image, 68, 4) == CONTROL_ABI
            and uint(image, 72, 4) == 0, "unsupported control image layout or topology")
    words = [uint(image, offset + 8 * index, 8) for index in range(count)]
    return image, words


def expand_mother(words, max_steps):
    registers = [0] * 8
    live = {}
    calls, wait_masks = [], []
    pc = 0
    require(0 < max_steps <= 10_000, "unsupported MC step bound")
    for step in range(1, max_steps + 1):
        require(0 <= pc < len(words), "MC PC out of range")
        word = words[pc]
        op, a, b, c = ((word >> shift) & 0xFF for shift in (56, 48, 40, 32))
        imm = word & 0xFFFFFFFF
        next_pc = pc + 1
        if op == 0x13 and a < len(registers) and b == c == 0:  # MOVI
            registers[a] = imm
        elif op == 0x16 and (a, b, c, imm) == (0, 0, 0, 128):  # descriptor ADDI64
            value = (((registers[a + 1] << 32) | registers[a]) + imm) & ((1 << 64) - 1)
            registers[a], registers[a + 1] = value & 0xFFFFFFFF, value >> 32
        elif op == 0x10 and a < 3 and b < 3 and c == imm == 0:  # CALL
            require(b not in live and a not in live.values(), "MC reuses a live target or token")
            live[b] = a
            calls.append({"target": a, "token": b, "reference": (registers[1] << 32) | registers[0]})
        elif op == 0x11 and a == b == c == 0:  # WAIT
            require(imm and imm & ~sum(1 << token for token in live) == 0,
                    "MC WAIT references a token without a pending call")
            wait_masks.append(imm)
            # Retire statically for order recovery. No elapsed time is assigned.
            live = {token: target for token, target in live.items() if not imm & (1 << token)}
        elif op == 0x17 and a < len(registers) and b == c == 0 and imm < pc:  # LOOP
            require(registers[a] > 0, "MC LOOP counter is zero")
            registers[a] -= 1
            if registers[a]:
                next_pc = imm
        elif op == 0x1F and word == 0x1F00000000000000:  # END
            require(not live and next_pc == len(words), "MC END leaves live calls or trailing code")
            return calls, wait_masks, step
        else:
            raise ValueError("unsupported MC instruction at PC {}: {:016x}".format(pc, word))
        pc = next_pc
    raise ValueError("MC exceeded its step bound")


def check_descriptors(data, calls, oracle):
    rows = list(decode_hex(data, 128))
    bindings = oracle["first_descriptors"]
    require(len(rows) == len(calls) == len(bindings) == oracle["descriptor_count"],
            "descriptor count disagrees with calls or oracle")
    for index, (row, call, binding) in enumerate(zip(rows, calls, bindings)):
        require(uint(row, 0, 4) == 0x02505001 and uint(row, 4, 2) == 128
                and uint(row, 8, 4) == 0x02504D02 and uint(row, 12, 4) == SEED
                and uint(row, 124, 4) == zlib.crc32(row[:124])
                and hashlib.sha256(row).hexdigest() == binding["sha256"]
                and (index, call["reference"], call["target"])
                == (binding["index"], binding["address"], binding["p"]),
                "descriptor {} disagrees with ABI, integrity or call binding".format(index))
    return hashlib.sha256(b"".join(rows)).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_receipts(path):
    names = {"program.json", "oracle.json", "mother.hex", "local.hex", "scopes.hex"}
    names.update("mode-{}-initial-{}.log".format(mode, initial)
                 for mode in (0, 1) for initial in (0, 1, 2))
    expected = {"seed-{}/{}".format(SEED, name) for name in names}
    files = {}
    with tarfile.open(str(path), "r|gz") as archive:
        for entry in archive:
            if entry.name in expected:
                name = entry.name.split("/", 1)[1]
                require(entry.isfile() and name not in files, "invalid receipt entry: " + entry.name)
                files[name] = archive.extractfile(entry).read()
    require(set(files) == names, "missing receipt entries: " + ", ".join(sorted(names - set(files))))
    return files


def profile(log, program, mode):
    lines = log.decode("utf-8").splitlines()
    require(not any("%Fatal" in line or "%Error" in line for line in lines), "RTL log has an error")

    def fields(prefix):
        rows = [line[len(prefix):] for line in lines if line.startswith(prefix)]
        require(len(rows) == 1, "expected one RTL receipt: " + prefix)
        return {key: int(value) for key, value in (item.split("=", 1) for item in rows[0].split())}

    passed = fields("PASS ffn_three_p_native ")
    ffn = fields("FFN_PROFILE ")["cycles"]
    down = fields("DOWN_PROFILE ")["cycles"]
    dma = fields("DMA_PROFILE ")
    observed = fields("PROGRAM_PROFILE ")
    require(passed["mode"] == mode and passed["real_P_M"] == 3
            and passed["real_S_banks"] == 16 and ffn > 0 and down > 0,
            "unexpected RTL configuration or phase interval")
    require(dma["backend_requests"] == dma["backend_returns"] == EXPECTED_BURSTS
            and observed["calls"] == program["calls"]
            and observed["confirmed_reads"] == program["expected_terminal_read_bytes"] == EXPECTED_BURSTS * 64
            and observed["confirmed_writes"] == program["expected_terminal_write_bytes"] == EXPECTED_ON_CHIP_WRITES,
            "RTL terminal transaction counts disagree")
    return {"early_exec": passed.get("early_exec", 0),
            "ffn_cycles": ffn, "down_cycles": down, "phase_cycle_sum": ffn + down,
            "backend_requests": dma["backend_requests"], "backend_returns": dma["backend_returns"],
            **observed}


def audit_job(path, expected_hash):
    archive_hash = file_sha256(path)
    require(archive_hash == expected_hash, "receipt SHA-256 mismatch: " + str(path))
    files = read_receipts(path)
    program, oracle = (json.loads(files[name]) for name in ("program.json", "oracle.json"))
    require(program["schema"] == "issue250-three-P-ffn-program/1" and program["topology"] == SEED
            and oracle["seed"] == SEED and oracle["synthetic_DDR_provider"] is True,
            "unexpected FFN manifest or provider scope")
    mother, mc_words = control_image(files["mother.hex"], 3, 0)
    local, lc_words = control_image(files["local.hex"], 2, 1)
    require(lc_words == [0x4100000000000000, 0x4400000000000001, 0x4F00000000000000],
            "unsupported LC kernel; expected EXEC, WAIT, END")
    calls, waits, steps = expand_mother(mc_words, uint(mother, 52, 4))
    mother_sha, local_sha = (hashlib.sha256(image).hexdigest() for image in (mother, local))
    require(mother_sha == program["mother_sha256"] and local_sha == program["local_sha256"]
            and "{:08x}".format(zlib.crc32(local)) == program["local_crc32"]
            and len(mother) == program["mother_bytes"] and len(local) == program["local_bytes_each"]
            and len(mc_words) == program["static_instructions"] and steps == program["dynamic_instructions"]
            and len(calls) == program["calls"] and calls == program["calls_in_order"]
            and waits == [program["wait_mask"]] * program["loop_iterations"],
            "decoded control or image integrity disagrees with the archived manifest")
    descriptor_sha = check_descriptors(files["scopes.hex"], calls, oracle)
    observed = [dict(mode=mode, initial=initial,
                     **profile(files["mode-{}-initial-{}.log".format(mode, initial)], program, mode))
                for mode in (0, 1) for initial in (0, 1, 2)]
    return {"archive_sha256": archive_hash, "mother_sha256": mother_sha, "local_sha256": local_sha,
            "descriptor_image_sha256": descriptor_sha, "mc_static_instructions": len(mc_words),
            "mc_dynamic_instructions": steps, "calls": len(calls), "waits": len(waits),
            "lc_opcodes": ["EXEC", "WAIT", "END"], "synthetic_ddr_provider": True,
            "observed_rtl_profiles": observed}


def audit(directory):
    jobs = {str(job): audit_job(directory / "{}-receipts.tar.gz".format(job), digest)
            for job, digest in ARCHIVES.items()}
    first, second = jobs["102603"], jobs["102604"]
    for key in ("mother_sha256", "local_sha256", "descriptor_image_sha256"):
        require(first[key] == second[key], "paired jobs have different " + key)
    differences = []
    for left, right in zip(first["observed_rtl_profiles"], second["observed_rtl_profiles"]):
        require(left["early_exec"] == 1 and right["early_exec"] == 0,
                "paired jobs disagree with the expected early EXEC and baseline configurations")
        for key in ("mode", "initial", "backend_requests", "backend_returns", "calls",
                    "confirmed_reads", "confirmed_writes"):
            require(left[key] == right[key], "paired jobs disagree on " + key)
        differences.append({"mode": left["mode"], "initial": left["initial"],
                            "phase_cycles_102604_minus_102603": right["phase_cycle_sum"] - left["phase_cycle_sum"]})
    return {"schema": "issue265-ffn-control-input-audit/1", "seed": SEED, "jobs": jobs,
            "paired_rtl_differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        rendered = json.dumps(audit(args.receipts_dir), ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            with args.output.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered)
    except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
        parser.exit(1, "audit failed: {}\n".format(exc))


if __name__ == "__main__":
    main()
