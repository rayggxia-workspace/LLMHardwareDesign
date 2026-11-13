"""Create an isolated DRAMsim3 copy with a WR-command observer and unified queue."""

import argparse
import hashlib
from pathlib import Path
import shutil


PINS = {
    "CMakeLists.txt": "931fc4bb59d6811c25f9d9f3c33786260ff40ca61512649b43c1f53286d272ae",
    "src/configuration.cc": "e221b33ea803734e2925f0e92ad093a2cb8918f3b831d68a2f0f40a2f45cad79",
    "src/controller.cc": "576d9ef0771a752b1c4012bb43243f7e2bb12138c7940cbe1212e2d945e24ca0",
    "src/dram_system.cc": "57faec614499a6502da69c610e0b58eb7b0e425e604f683e2fd7676678a3797a",
    "src/dramsim3.h": "1727137ebfc02836855f0efe91ac6accaa089711d2124e0d0720704527787d3b",
}
CONFIG_SHA256 = "748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766"

OBSERVER = b"""
#include <stdexcept>

namespace {
using WriteObserver = void (*)(void *, uint64_t, uint64_t, uint64_t);
WriteObserver issue265_observer = nullptr;
void *issue265_observer_context = nullptr;
}

extern "C" void issue265_observe_writes(WriteObserver observer, void *context) {
    if (!observer || !context || issue265_observer) {
        throw std::runtime_error("invalid or duplicate DRAM write observer");
    }
    issue265_observer = observer;
    issue265_observer_context = context;
}

namespace dramsim3 {
"""


def check_hash(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("unrecognized frozen DRAMsim3 file: {}".format(path))
    return data


def replace_once(data, old, new):
    if b"\r\n" in data:
        old = old.replace(b"\n", b"\r\n")
        new = new.replace(b"\n", b"\r\n")
    if data.count(old) != 1:
        raise ValueError("DRAMsim3 patch anchor missing or ambiguous")
    return data.replace(old, new, 1)


def prepare(stock, dest, stock_config, dest_config):
    stock, dest, stock_config, dest_config = (path.resolve() for path in (stock, dest, stock_config, dest_config))
    if dest == stock or stock in dest.parents or dest.exists():
        raise ValueError("expected a fresh DRAMsim3 directory outside the frozen source")
    if (dest_config == stock or stock in dest_config.parents or dest_config == stock_config
            or dest_config == dest or dest_config.exists()):
        raise ValueError("expected a fresh configuration path outside the frozen source")
    if not dest_config.parent.is_dir() and dest_config.parent != dest:
        raise ValueError("configuration destination parent does not exist")
    for filename, digest in PINS.items():
        check_hash(stock / filename, digest)
    original = check_hash(stock / "src/controller.cc", PINS["src/controller.cc"])
    config = check_hash(stock_config, CONFIG_SHA256)
    patched = replace_once(original, b"\nnamespace dramsim3 {\n", OBSERVER)
    patched = replace_once(patched, b"      write_draining_(0) {\n",
                           b"      write_draining_(0) {\n"
                           b"    if (issue265_observer && !is_unified_queue_) {\n"
                           b"        throw std::runtime_error(\"WR completion requires a unified transaction queue\");\n"
                           b"    }\n")
    patched = replace_once(patched, b"        pending_wr_q_.erase(it);\n",
                           b"        pending_wr_q_.erase(it);\n"
                           b"        if (issue265_observer) {\n"
                           b"            issue265_observer(issue265_observer_context, cmd.hex_addr, clk_, config_.write_delay);\n"
                           b"        }\n")
    config = replace_once(config, b"[system]\n", b"[system]\nunified_queue = true\n")
    shutil.copytree(str(stock), str(dest), ignore=shutil.ignore_patterns(".git", "libdramsim3.so"))
    (dest / "src/controller.cc").write_bytes(patched)
    with dest_config.open("xb") as stream:
        stream.write(config)
    print("{}  {}".format(hashlib.sha256(patched).hexdigest(), dest / "src/controller.cc"))
    print("{}  {}".format(hashlib.sha256(config).hexdigest(), dest_config))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stock", "dest", "stock_config", "dest_config"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        prepare(args.stock, args.dest, args.stock_config, args.dest_config)
    except (OSError, ValueError) as error:
        parser.exit(1, "DRAMsim3 write setup failed: {}\n".format(error))


if __name__ == "__main__":
    main()
