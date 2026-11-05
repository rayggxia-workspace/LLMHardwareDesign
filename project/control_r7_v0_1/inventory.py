"""Inventory image storage and accepted interface traffic from the archived R6 run."""
import argparse
import hashlib
import json
import pathlib
import sys
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parent
EVIDENCE = ROOT / "work/Melodydt/179"
for name in ("control_r6_v0_1", "control_rtl_min_v0_1"):
    sys.path.insert(0, str(PROJECT / name))
import network_check
import run as common
from verify_bundle import image, verify


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(path.read_bytes())


def image_inventory(stem):
    path = PROJECT / "control_r6_v0_1"
    ir = (path / "examples" / (stem + ".json")).read_bytes()
    package = load_json(path / "generated" / (stem + ".bundle.json"))
    binaries, _ = verify(ir, package)
    images = {}
    for role, data in binaries.items():
        decoded = image.parse_image(data)
        record_bytes = {name: width * len(decoded["records"][name]) for name, width, _ in image.SECTIONS}
        assert sum(record_bytes.values()) + 128 == len(data)
        images[role] = dict(header_bytes=128, section_bytes=record_bytes, bytes=len(data),
                            capacity_bytes=image.LIMIT_BYTES[decoded["role"]], sha256=digest(data))
    return dict(images=images, bytes=sum(x["bytes"] for x in images.values()),
                pm_capacity_bytes=sum(x["capacity_bytes"] for x in images.values()))


def accepted(rows, valid, ready):
    return [t for t, signals in rows if signals[valid] and signals[ready]]


def measure_trace(log, expected, images):
    trace = network_check.decode(log)
    mother = [(row["cycle"], row["signals"]) for row in trace["mother"]]
    locals_ = [[(row["cycle"], common.check_cycles.sample(row["signals"]))
                for row in child["cycles"]] for child in trace["locals"]]
    assert len(mother) == expected["network"]["mother"]["cycles"]
    starts = accepted(mother, "start_valid_i", "start_ready_o")
    results = accepted(mother, "result_valid_o", "result_ready_i")
    assert len(starts) == expected["case"]["runs"]
    assert len(results) == expected["network"]["mother"]["results"]
    first = starts[0]
    last = results[-1] if results else mother[-1][0]
    active = [row for row in mother if first <= row[0] <= last]
    call_packets = len(accepted(active, "task_valid_o", "task_ready_i"))
    return_packets = len(accepted(active, "return_valid_i", "return_ready_o"))
    assert call_packets == expected["network"]["mother"]["CALLs"] + expected["network"]["mother"]["CANCELs"]
    assert return_packets == sum(c["terminals"] + c["READY_reports"] for c in expected["network"]["locals"])

    pm = {}
    for role, rows in zip(("mother", "local0", "local1"), [mother, *locals_]):
        requests = [(t, s["pm_req_write_o"]) for t, s in rows
                    if s["pm_req_valid_o"] and s["pm_req_ready_i"]]
        writes = sum(write for t, write in requests if t < first)
        assert writes * 16 == images[role]["bytes"]
        pm[role] = dict(load_write_beats=writes, load_read_beats=sum(not w for t, w in requests if t < first),
                        active_read_beats=sum(not w for t, w in requests if first <= t <= last))
        assert not any(w for t, w in requests if first <= t <= last)
    dma_req = dma_rsp = 0
    for line in log.splitlines():
        if line.startswith("Q "):
            _, cycle, direction, _ = line.split()
            if first <= int(cycle) <= last:
                if direction == "REQ":
                    dma_req += 1
                elif direction == "RSP":
                    dma_rsp += 1
    assert dma_req == dma_rsp == expected["DMA"]["physical_requests"]
    cycles = last - first + 1
    control_bits = 512 * (call_packets + return_packets)
    dma_bits = 185 * dma_req + 146 * dma_rsp
    return dict(name=expected["case"]["name"], successful_jobs=len(results), start_accept_cycle=first,
                end_cycle=last, end_marker="last_result_accept" if results else "last_trace_sample_after_poison",
                active_core_cycles=cycles, task_packets=call_packets, return_packets=return_packets,
                control_packet_bytes=control_bits // 8, control_bits_per_core_cycle=control_bits / cycles,
                dma_request_flits=dma_req, dma_response_flits=dma_rsp, dma_transport_bits=dma_bits,
                dma_transport_bits_per_core_cycle=dma_bits / cycles, pm=pm)


def inventory(archive):
    report_path = EVIDENCE / "control-r6-rtl-report.json"
    index = load_json(EVIDENCE / "control-r6-validation-index.json")
    assert digest(report_path.read_bytes()) == index["files"]["results/r6/report.json"]
    assert digest(archive.read_bytes()) == index["archive_sha256"]
    report = load_json(report_path)
    bundles = {key: image_inventory(key) for key in ("joined_wait", "split_wait")}
    traffic = []
    with tarfile.open(archive) as tar:
        for case in report["results"]:
            name = case["case"]["name"]
            path = f"results/r6/{name}/trace.log"
            raw = tar.extractfile(path).read()
            assert digest(raw) == index["files"][path] == case["trace_sha256"]
            bundle = bundles["joined_wait" if name == "joined_continuous" else "split_wait"]
            for role, metadata in case["provenance"]["images"].items():
                assert bundle["images"][role]["sha256"] == metadata["sha256"]
            traffic.append(measure_trace(raw.decode("utf-8"), case, bundle["images"]))

    return dict(
        schema="control-r7-inventory/0.1", r6_archive_sha256=index["archive_sha256"],
        r6_trace_source_commit=index["source"]["source_commit"],
        image_bundles=bundles, interface_traffic=traffic,
        declared_storage=dict(
            private_S_bytes_each=16384, private_S_count=2, external_fixture_words=64, data_word_bits=128,
            mc_packet_slots=dict(context=2, terminal=2, ready=2, outbound=1),
            mc_packet_bits=512, lc_packet_slots_per_instance=dict(task=1, terminal=1),
            lc_packet_bits=512, dma_slots_per_S=8, dma_credit_limit_per_S=1, dma_payload_bits_per_slot=128,
            async_fifo_entries_per_direction=4, fifo_request_bits=185, fifo_response_bits=146,
            async_fifo_total_payload_bits=4 * (185 + 146)),
        rate_method="sum of accepted payload bus bits from first START through final accepted RESULT "
                    "or the last poison trace sample, inclusive; excludes wire encoding and idle setup cycles")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r6-evidence", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = inventory(args.r6_evidence)
    args.out.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    for name, bundle in result["image_bundles"].items():
        print(f"{name}: {bundle['bytes']} B of {bundle['pm_capacity_bytes']} B")
    for case in result["interface_traffic"]:
        print(case["name"], case["active_core_cycles"], "active core cycles",
              case["control_packet_bytes"], "accepted control bytes")


if __name__ == "__main__":
    main()
