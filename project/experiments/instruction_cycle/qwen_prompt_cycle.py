"""Predict the first 105530 prompt, embedding and gamma DDR transactions."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import struct

from dma_ddr import Beat
from dram_live import DramLive
from qwen_native_ddr import CONFIG_SHA, DDR_PS, Proof, WINDOWS, fields, file_digest, require


CORE_PS = 10_000
BURST_BYTES = 64
ROW_BYTES = 8192
SRAM_WORD_BYTES = 16
SRAM_ACCEPT_TO_ACK = 2


def prompt_inputs(archive):
    proof = Proof(archive, WINDOWS["next_rms"][0])
    program = json.loads(proof.read("generated/program.json"))["prompt_ingress"]
    prompt_data = proof.read("generated/token.bin")
    gamma = int(proof.read("generated/rms-descriptor.txt").split()[0])
    require(len(prompt_data) == BURST_BYTES and len(program["tokens"]) == 3,
            "unsupported prompt ingress shape")
    tokens = list(struct.unpack_from("<3I", prompt_data))
    require(tokens == program["tokens"] and gamma == program["gamma_address"] and program["serial_rms"] is True,
            "prompt/RMS binding differs from physical deployment data")
    return {"prompt_base": program["prompt_address"], "embedding_base": program["embedding_address"],
            "gamma_base": gamma, "token": tokens[0], "job": 1}


class PromptDdr:
    """Drive the two live DDR devices through the fixture's physical read lanes."""

    def __init__(self, dram, mode):
        self.dram = dram
        self.mode = mode
        self.events = []
        self.tick = [0, 0]

    def read(self, ready_cycle, lane, tag, address, *, request_ready=None, response_ready=None):
        # Before the bridge advances the current edge, its count is the number
        # of elapsed non-reset core edges. The testbench uses the same index
        # for periodic request gating during this prefix.
        cycle = ready_cycle
        while (self.mode and (cycle + lane) % 5 == 0) or (request_ready and not request_ready(cycle)):
            cycle += 1
            require(cycle - ready_cycle < 4096, "read request remained blocked")
        channel = lane // 2
        device = self.dram[channel]
        tick = cycle * CORE_PS // DDR_PS
        require(tick >= self.tick[channel] and device.idle, "overlapping request in serial ingress")
        require(not device.completions(tick), "unexpected completion before ingress read")
        beat = Beat((lane, tag), address, False, None)
        self.events.append(("admit", cycle, lane, tag, address))
        # A single pending request on an otherwise drained channel can be
        # offered immediately. If the controller refuses, its head stays live.
        while not device.can_accept(tick, beat):
            tick += 1
            require(not device.completions(tick), "unexpected completion during admission stall")
        device.submit(tick, beat)
        self.events.append(("ddr_accept", tick, lane, tag, address))
        for tick in range(tick + 1, tick + 4097):
            completions = device.completions(tick)
            if completions:
                require(completions == [beat.identifier], "ingress DDR returned an unexpected transaction")
                break
        else:
            raise ValueError("ingress DDR did not complete within 4096 ticks")
        self.tick[channel] = tick
        self.events.append(("callback", tick, lane, tag, address))
        returned = (tick * DDR_PS + CORE_PS - 1) // CORE_PS
        while response_ready and not response_ready(returned):
            returned += 1
            require(returned - cycle < 4096, "read response remained blocked")
        self.events.append(("return", returned, lane, tag, address))
        return returned

    def read_pair(self, ready_cycle, lane, requests):
        """Two ordered, independently accepted beats of one typed record."""
        require(len(requests) == 2 and len(set(requests)) == 2, "invalid typed DDR record")
        channel = lane // 2
        device = self.dram[channel]
        tick = ready_cycle * CORE_PS // DDR_PS
        require(device.idle and tick >= self.tick[channel], "typed DDR record overlaps previous owner")
        require(not device.completions(tick), "unexpected completion before typed descriptor")
        addresses = dict(requests)
        pending = []
        issued, completed = set(), set()
        admitted, returned = [], []
        cycle = ready_cycle
        while len(returned) != len(requests):
            if pending and pending[0] in completed:
                tag = pending.pop(0)
                self.events.append(("return", cycle, lane, tag, addresses[tag]))
                returned.append(cycle)
            if len(returned) == len(requests):
                break
            if len(admitted) < len(requests) and (not self.mode or (cycle + lane) % 5):
                tag, address = requests[len(admitted)]
                pending.append(tag)
                admitted.append(cycle)
                self.events.append(("admit", cycle, lane, tag, address))
            target = (cycle + 1) * CORE_PS // DDR_PS
            while tick < target:
                for tag in pending:
                    if (lane, tag) in issued:
                        continue
                    address = addresses[tag]
                    beat = Beat((lane, tag), address, False, None)
                    if device.can_accept(tick, beat):
                        device.submit(tick, beat)
                        issued.add((lane, tag))
                        self.events.append(("ddr_accept", tick, lane, tag, address))
                    break  # the fixture accepts at most one request from this lane per tick
                elapsed = target - tick if device.idle and all((lane, tag) in issued for tag in pending) else 1
                tick += elapsed
                for response_lane, tag in device.completions(tick):
                    require(response_lane == lane and tag in pending and tag not in completed,
                            "typed DDR returned an unexpected transaction")
                    completed.add(tag)
                    self.events.append(("callback", tick, lane, tag, addresses[tag]))
            cycle += 1
            require(cycle - ready_cycle < 4096, "typed DDR record did not drain")
        self.tick[channel] = tick
        return admitted, returned


def load_row(ddr, first_request, lane, base, first_word):
    """READ_WAIT → four serialized STORE/STORE_WAIT pairs → READ or DONE."""
    next_request = first_request
    writes = []
    for burst in range(ROW_BYTES // BURST_BYTES):
        returned = ddr.read(next_request, lane, burst, base + BURST_BYTES * burst)
        store = returned + 1  # loader enters STORE after capturing the read response
        for word in range(BURST_BYTES // SRAM_WORD_BYTES):
            ack = store + SRAM_ACCEPT_TO_ACK
            scratch_word = first_word + burst * (BURST_BYTES // SRAM_WORD_BYTES) + word
            writes.append((scratch_word & 3, scratch_word >> 2, store, ack))
            store = ack + 1
        next_request = store
    return next_request, writes


def predict(archive, binary, config, output, mode, prompt_start, *, tail=None, allow_writes=False):
    inp = prompt_inputs(archive)
    require(file_digest(config) == CONFIG_SHA, "DDR config differs from 105530")
    output.mkdir()
    with ExitStack() as stack:
        devices = [stack.enter_context(DramLive(binary, config, output / "channel{}".format(channel),
                                               capacity_bytes=1 << 34, allow_writes=allow_writes)) for channel in range(2)]
        require(all(device.period_ps == DDR_PS for device in devices), "DDR device period differs from 105530")
        ddr = PromptDdr(devices, mode)
        prompt_return = ddr.read(prompt_start + 1, 0, inp["job"] << 32, inp["prompt_base"])
        # EMIT consumes the token, LAUNCH installs the embedding loader, then
        # READ issues. Embedding DONE is consumed before the RMS launch and
        # its gamma loader launch, so the two loaders never share the S port.
        embedding_done, embedding_stores = load_row(ddr, prompt_return + 3, 1,
                                                     inp["embedding_base"] + inp["token"] * ROW_BYTES, 0)
        gamma_done, gamma_stores = load_row(ddr, embedding_done + 3, 3, inp["gamma_base"], ROW_BYTES // SRAM_WORD_BYTES)
        result = {"scope": "105530 first prompt row through initial RMS gamma load", "mode": mode,
                  "prompt_start_core_cycle": prompt_start, "binding": inp,
                  "last_gamma_sram_ack_core_cycle": gamma_done - 1,
                  "ddr_events": ddr.events[:], "sram_writes": {"embedding": embedding_stores, "gamma": gamma_stores}}
        if tail is not None:
            return tail(result, ddr)
    return result


def compare(prediction, trace):
    """Compare against the archive only after the independent prediction exists."""
    require(len(prediction["ddr_events"]) == 4 * (1 + 2 * ROW_BYTES // BURST_BYTES),
            "prediction does not cover the complete ingress read prefix")
    count = 0
    with trace.open("r", encoding="ascii") as stream:
        for expected in prediction["ddr_events"]:
            name, cycle, lane, tag, address = fields(stream.readline(), 5)
            actual = (name, int(cycle), int(lane), int(tag), int(address))
            require(tuple(expected) == actual, "event {} differs: predicted {}, observed {}".format(count, expected, actual))
            count += 1
    return {"matched_events": count, "matched_bursts": count // 4, "trace_sha256": file_digest(trace)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    make = sub.add_parser("predict")
    for name in ("archive", "binary", "config", "output"):
        make.add_argument(name, type=Path)
    make.add_argument("--mode", type=int, choices=(0, 1), required=True)
    make.add_argument("--prompt-start", type=int, required=True, help="accepted testbench prompt-start boundary")
    check = sub.add_parser("compare")
    check.add_argument("prediction", type=Path)
    check.add_argument("archive", type=Path)
    args = parser.parse_args()
    if args.operation == "predict":
        require(args.prompt_start >= 0, "invalid prompt-start edge")
        result = predict(args.archive, args.binary.resolve(), args.config.resolve(), args.output.resolve(),
                         args.mode, args.prompt_start)
    else:
        prediction = json.loads(args.prediction.read_bytes())
        proof = Proof(args.archive, WINDOWS["next_rms"][0])
        trace = "DDR-{}/transactions.tsv".format(prediction["mode"])
        result = compare(prediction, proof.path(trace))
        proof.check(trace, result["trace_sha256"])
        result["prediction_sha256"] = file_digest(args.prediction)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
