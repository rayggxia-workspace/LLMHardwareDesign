"""Check the frozen #179 native 16-byte DMA and finite memory-peer trace.

The memory-side accepted request is the prediction boundary. The provider
predicts each response from its RTL seed, accepted request and stall setting.
DMA-side Q records check identity, data and cross-clock causality.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re


PROFILES = {
    "receiver_fast": (0, 1, "8a9ecaa47aaa275f5051384281a935b648b470a6f52b3d0ef3d8374e2774e5d2"),
    "receiver_stalled": (3, 1, "1903064598fa7af7b4a55de1c4cbc6f24a359d57924d0ebbce452f7f15fe3d1d"),
    "receiver_two_jobs": (2, 2, "29e4728d809c720957b5f0a884db0b1ff680414938c407fb60aebb4574fb8f5f"),
}
MASK_128 = (1 << 128) - 1
EVENT = re.compile(r"^([EQ]) (\d+) (REQ|RSP) ([0-9a-f]+)$", re.I)


def rows(log):
    records = {name: [] for name in ("E", "Q")}
    for line in log.splitlines():
        if not line.startswith(("E ", "Q ")):
            continue
        match = EVENT.fullmatch(line)
        if match is None:
            raise ValueError("invalid native DMA event")
        domain, edge, operation, payload = match.groups()
        cycle = int(edge)
        if records[domain] and cycle <= records[domain][-1][0]:
            raise ValueError("non-increasing {} handshake cycle".format(domain))
        records[domain].append((cycle, operation, int(payload, 16)))
    return records


def compare(log, stall, jobs):
    summary = "PASS network actualMother=1 actualLC=2 CALL={} CANCEL=0 results={} poison=0".format(2 * jobs, jobs)
    if log.splitlines().count(summary) != 1 or "%Fatal" in log or "%Error" in log:
        raise ValueError("legacy DMA RTL did not pass with the expected job count")
    records = rows(log)
    peer, dma = records["E"], records["Q"]
    if len(peer) != 6 * jobs or len(dma) != len(peer):
        raise ValueError("legacy DMA did not drain all request/response pairs")
    if [record[1:] for record in dma] != [record[1:] for record in peer]:
        raise ValueError("native request/response identity or payload changed across CDC")

    # finite_external_memory seeds 64 words; writes become visible on E REQ.
    memory = [0x0f0e0d0c0b0a09080706050403020100
              ^ sum(((index // 4 - 6) & 0xffffffff) << shift for shift in (0, 32, 64, 96))
              for index in range(64)]
    written, read_after_write, visibility_discriminators, tags = {}, [], [], set()
    for index in range(0, len(peer), 2):
        issue, req_kind, request = peer[index]
        done, rsp_kind, response = peer[index + 1]
        if req_kind != "REQ" or rsp_kind != "RSP" or request >> 185 or response >> 146:
            raise ValueError("legacy provider violated its one-pending transaction contract")
        tag = (request >> 168) & 0xffff
        address = (request >> 128) & ((1 << 40) - 1)
        write = bool(request >> 184)
        if address >= 1024 or address % 16 or tag in tags or stall and issue % 7:
            raise ValueError("invalid legacy request address, tag or ready phase")
        tags.add(tag)
        word = address // 16
        if write:
            payload = request & MASK_128
            written[address] = memory[word] != payload
            memory[word] = payload
        else:
            payload = memory[word]
            if address in written:
                read_after_write.append(address)
                if written[address]:
                    visibility_discriminators.append(address)
        if (done, response) != (issue + 3 + 3 * stall, (tag << 128) | payload):
            raise ValueError("legacy peer response differs for tag {} at address {:#x}".format(tag, address))
        # Q posedges are 5 + 10q ns, E posedges are 3 + 6e ns.
        if not 5 + 10 * dma[index][0] < 3 + 6 * issue < 3 + 6 * done < 5 + 10 * dma[index + 1][0]:
            raise ValueError("legacy DMA CDC handshake order is invalid")
    if len(read_after_write) != jobs:
        raise ValueError("missing same-address read after write")
    return {"matched_native_transactions": len(peer) // 2, "matched_crossings": len(peer),
            "read_after_write_addresses": read_after_write,
            "visibility_discriminator_addresses": visibility_discriminators,
            "peer_response_cycles": 3 + 3 * stall}


def compare_archived(directory):
    results = {}
    for name, (stall, jobs, digest) in PROFILES.items():
        data = (directory / (name + ".log")).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("archived log SHA-256 differs: " + name)
        results[name] = dict(compare(data.decode("ascii"), stall, jobs), log_sha256=digest)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archived_log_directory", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare_archived(args.archived_log_directory), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, "legacy DMA comparison failed: {}\n".format(exc))
