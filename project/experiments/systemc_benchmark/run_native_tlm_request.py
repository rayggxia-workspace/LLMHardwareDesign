"""Execute the sealed Qwen request continuously with persistent SRAM and DDR."""

from argparse import ArgumentParser
from bisect import bisect_right
from collections import defaultdict
import json
from pathlib import Path
from struct import pack, unpack, unpack_from

from export_tlm_mother_program import export, parse_pm_image
from native_tlm_attention import Attention
from native_tlm_dma import CommittedMemory, NativeDMA
from native_tlm_ffn import FFN
from native_tlm_local import run_page
from native_tlm_projection import Projection
from native_tlm_timing import Clock, Dram, Images, S128, Scheduler, Transfer, embedding
from native_tlm_u import UArithmetic
from prepare_native_whole_request import digest


P = (0, 0x02505001, 0x02504d02, 2)
ABI = 0x02500002
VOCAB = 151936


def key(target, schema, opcode=1):
    return target, int.from_bytes(schema, "little"), ABI, opcode


class DecodeKV(CommittedMemory):
    """Supply representative historical rows and audit the two live KV appends."""

    def __init__(self, images, write_regions, binding):
        super().__init__(images, write_regions)
        if (binding["row_bytes"], binding["stream_count"], len(binding["streams"])) != (512, 144, 144):
            raise ValueError("unexpected deployed KV geometry")
        phases = binding["phases"]
        if [(p["first"], p["rows"], p["exclusive_end"]) for p in phases[1:3]] != [(512, 1, 513), (513, 1, 514)]:
            raise ValueError("expected two adjacent decode positions after the 512-token prefix")
        self.bases_kv = sorted(stream["base"] for stream in binding["streams"])
        if any(a + binding["capacity"] * 512 > b for a, b in zip(self.bases_kv, self.bases_kv[1:])):
            raise ValueError("overlapping KV streams")
        self.new_beats = [{base + row * 512 + offset for base in self.bases_kv for offset in range(0, 512, 64)}
                          for row in (512, 513)]
        self.reread = set()
        self.step = 0

    def __call__(self, address):
        index = bisect_right(self.bases_kv, address) - 1
        if index >= 0 and 0 <= address - self.bases_kv[index] < 512 * 512:
            if self.binding(address) is None:
                raise ValueError("historical KV is outside the compiled DDR allocation")
            return bytes(64)
        payload = super().__call__(address)
        if self.step == 2 and address in self.new_beats[0]:
            self.reread.add(address)
        return payload

    def finish(self, step):
        if (step != self.step or not self.new_beats[step - 1] <= self.committed.keys()
                or (step == 2 and self.reread != self.new_beats[0])):
            raise ValueError("live KV writes or cross-step reads are incomplete")


class Vocabulary:
    def __init__(self, projection):
        self.projection = projection
        self.columns = 0
        self.best = None

    def provider(self, record):
        columns, first, stride, groups = unpack_from("<IIHB", record, 64)
        out, = unpack_from("<H", record, 86)
        if (columns, first, stride, groups, record[83]) != (VOCAB, self.columns, 8, 16, 1):
            raise ValueError("incomplete or out-of-order vocabulary tile")
        execute = self.projection.provider(record)

        def run(done):
            def projected():
                def consumed(payload):
                    for index, logit in enumerate(unpack("<128i", payload), first):
                        if self.best is None or logit > self.best[0]:
                            self.best = logit, index
                    self.columns += 128
                    done()

                self.projection.read_span(self.projection.target, out, 32, consumed)
            execute(projected)
        return run

    def retire(self):
        if self.columns != VOCAB or self.best is None:
            raise ValueError("token retirement lacks the complete vocabulary")
        return self.best[1]


def main():
    parser = ArgumentParser(description=__doc__)
    for name in ("program", "memory", "dram_library", "dram_config", "out"):
        parser.add_argument(name, type=Path)
    parser.add_argument("deployment_sha256")
    parser.add_argument("--checkpoint-pages", type=int, default=0)
    parser.add_argument("--prefill-tokens", type=int, choices=(1, 2))
    parser.add_argument("--capture-first-layer", action="store_true")
    parser.add_argument("--decode-kv-binding", type=Path)
    parser.add_argument("--decode-kv-sha256")
    parser.add_argument("--dma-fabric-budget", action="store_true")
    parser.add_argument("--kv-read-window", type=int, default=1, choices=range(1, 33))
    parser.add_argument("--sram-port-bits", type=int, default=128, choices=(128, 512))
    parser.add_argument("--pipeline-memory", action="store_true")
    parser.add_argument("--rtl-weight-fetch", action="store_true")
    parser.add_argument("--av-value-fetch", choices=("legacy", "selected", "paired"), default="legacy")
    args = parser.parse_args()
    if args.checkpoint_pages < 0:
        parser.error("--checkpoint-pages must be nonnegative")
    decode = args.decode_kv_binding is not None
    if args.prefill_tokens and (decode or args.checkpoint_pages or args.capture_first_layer):
        parser.error("short prefill starts from empty KV and runs complete input positions")
    if decode and (args.checkpoint_pages or args.capture_first_layer or
                   digest(args.decode_kv_binding) != args.decode_kv_sha256):
        parser.error("decode requires a pinned KV binding and complete phases")
    program = args.program
    proof = program / "proof.sha256"
    if digest(proof) != args.deployment_sha256:
        raise ValueError("deployment proof mismatch")
    seals = {name: sha for sha, name in (line.split("  ", 1) for line in proof.read_text().splitlines())}

    def sealed(name):
        path = program / name
        if digest(path) != seals[name]:
            raise ValueError(f"native input seal mismatch: {name}")
        return path

    witness = json.loads(sealed("witness.json").read_bytes())
    topology = witness["topology"]
    phases = witness["phases"]
    if len(phases) != 128:
        raise ValueError("expected one prefill and 127 feedback phases")
    ffns = {(step, page): address for step, page, address, size in (
        map(int, line.split()) for line in sealed("ffn-activation.tsv").read_text().splitlines())
            if size == 8192}
    rows = sealed("input-index.tsv").read_text().splitlines()
    ingress = {(step, page): (position, mode, address, word, offset)
               for step, page, position, mode, address, word, offset in (
                   (int(x, 16) for x in row.split()) for row in rows[1:])}
    if int(rows[0]) != len(ingress) or len(ingress) != 639:
        raise ValueError("incomplete prompt and feedback ingress schedule")
    prefill_end = None
    if args.prefill_tokens:
        prefill_end, = (page for (step, page), (position, mode, *_) in ingress.items()
                        if step == 0 and mode == 1 and position == args.prefill_tokens)
    local = {}
    for row in sealed("runtime-assets.tsv").read_text().splitlines()[1:]:
        step, kind, target, address, length, crc, _, _, name = row.split()
        if kind == "L":
            local[int(step, 16), int(target, 16)] = int(address, 16), int(length), int(crc, 16), name
    args.out.mkdir()
    clock = Clock()
    u, *banks = [S128(clock, core_ps=3334, port_bits=args.sram_port_bits) for _ in range(4)]
    srams = dict(zip(("U", "P0", "P1", "P2"), (u, *banks)))
    p0 = banks[0]
    images = Images(args.memory)
    writes = [tuple(map(int, line.split())) for line in sealed("ddr-writes.tsv").read_text().splitlines()]
    memory = (DecodeKV(images, writes, json.loads(args.decode_kv_binding.read_bytes()))
              if decode else CommittedMemory(images, writes))
    dram = Dram(clock, args.dram_library, args.dram_config, args.out,
                credits=32 if args.dma_fabric_budget else 1, core_ps=3334 if args.dma_fabric_budget else None)
    base, descriptor = 0, b""

    def read(address):
        if base <= address < base + len(descriptor):
            return descriptor[address-base:address-base+64]
        return memory(address)

    scheduler = Scheduler(clock, dram, read, core_ps=3334, pm_write_bits=args.sram_port_bits,
                          pipeline=args.pipeline_memory)
    dma = NativeDMA(clock, dram, memory, core_ps=3334, pipeline=args.pipeline_memory)
    u_service, p_service = UArithmetic(clock, u), UArithmetic(clock, p0)
    projection = Projection(clock, dram, memory, u, p0, source_word=512, scratch_word=1008,
                            scratch_sram=p0, rtl_weight_fetch=args.rtl_weight_fetch)
    attention = Attention(clock, dram, memory, projection, kv_window=args.kv_read_window,
                          pipeline=args.pipeline_memory, value_fetch=args.av_value_fetch)
    providers = {
        P: projection.provider,
        (3, 3, 7, 4): embedding(u, dram, memory, pipeline=args.pipeline_memory),
        (3, 3, 7, 3): u_service.rms,
        (3, 3, 7, 2): u_service.add,
        (0, 3, 7, 2): p_service.add,
        key(0, b"DRL1"): dma.provider(p0, size=512, channel=1),
        key(3, b"DRL8"): dma.provider(u, size=8192, channel=1),
        key(0, b"DWS1"): dma.provider(p0, size=512, store=True),
        key(3, b"DWS8"): dma.provider(u, size=8192, store=True),
        key(0, b"KVR1"): dma.provider(p0, size=512, store=True),
        key(0, b"KVR1", 2): dma.provider(p0, size=512, store=True),
        key(0, b"RPE1"): p_service.rope,
        key(0, b"ATT1"): attention.provider,
        key(0, b"FDS8"): dma.provider(None, size=8192, store=True, down_sram=banks),
    }
    retired, installed = [], {}
    progress = args.out / "progress.jsonl"
    image = None
    step, positions, layers = -1, (512 if decode else 0), 0
    awaiting_residual = False
    prefix = args.checkpoint_pages
    first_ffn = None

    def capture(sram, start, words):
        return b"".join(sram.words[word] for word in range(start, start + words))

    def log(record):
        with progress.open("a", encoding="ascii") as stream:
            stream.write(json.dumps(record) + "\n")
        print(json.dumps(record), flush=True)

    try:
        with (sealed("mother-descriptors.tsv").open(encoding="ascii") as extents,
              (args.out / "page-timing.jsonl").open("w", encoding="ascii") as timing_file):
            page_count = int(next(extents))
            completed = 0
            if decode:
                for _ in range(phases[0]["page_count"]):
                    next(extents)
            for page in export(program, args.deployment_sha256, prefill_end or prefix,
                               first_step=1 if decode else 0,
                               last_step=2 if decode else 0 if prefill_end else None):
                page_start = clock.now
                ddr_start = dram.stats.copy()
                sram_start = {name: s.stats.copy() for name, s in srams.items()}
                page_step, index = page["step"], page["page"]
                if page_step != step:
                    if image is not None:
                        if image.read(1):
                            raise ValueError("unconsumed previous descriptor phase")
                        image.close()
                    step = page_step
                    if decode:
                        memory.step = step
                    image = sealed(f"phase-{step}/descriptors.bin").open("rb")
                ds, dp, addr, size = next(extents).split()
                base, size = int(addr, 16), int(size)
                phase = phases[step]
                if ((int(ds, 16), int(dp, 16)) != (step, index) or
                        base != phase["descriptor_base"] + image.tell() or size % 128 or not size):
                    raise ValueError("sealed descriptor extent differs from its page")
                descriptor = image.read(size)
                if len(descriptor) != size:
                    raise ValueError("truncated descriptor page")
                if (step, index) in ingress:
                    position, mode, address, word, offset = ingress.pop((step, index))
                    if position != positions or (completed and layers != 36):
                        raise ValueError("position advanced before 36 layers completed")
                    positions += 1
                    layers = 0
                    ready = []
                    if mode == 1 and step == 0:
                        def received():
                            projection.write_span(u, word, memory(address), lambda: ready.append(True))
                        dram.submit(Transfer(address), received)
                    elif mode == 2 and decode and step == 1 and not retired:
                        payload = bytearray(16)
                        payload[offset:offset+4] = pack("<I", 840)
                        u.access(word, lambda _: ready.append(True), bytes(payload))
                    elif mode == 2 and step and len(retired) == step - int(decode):
                        payload = bytearray(16)
                        payload[offset:offset+4] = pack("<I", retired[-1][0])
                        u.access(word, lambda _: ready.append(True), bytes(payload))
                    else:
                        raise ValueError("input index lacks live prompt or prior token")
                    clock.until(lambda: bool(ready))
                ingress_end = clock.now
                for target in range(4):
                    if page["targets"] & (1 << target):
                        binding = local[step, target]
                        if installed.get(target) != binding:
                            address, pm_size, crc, name = binding
                            path = sealed(name)
                            _, _, raw = parse_pm_image(path.read_bytes(), path, base=address, count=pm_size,
                                                       crc=crc, role="local", topology=topology)
                            scheduler.install_pm(address, pm_size, mother=False)
                            scheduler.bind_local(target, raw)
                            installed[target] = binding
                scheduler.install_pm(page["program_base"], page["program_bytes"], mother=True)
                pm_end = clock.now
                page_providers = providers.copy()
                ffn = None
                vocabulary = None
                if (step, index) in ffns:
                    activation = ffns.pop((step, index))
                    ffn = FFN(clock, dram, memory, u, banks, dma, activation,
                              rtl_weight_fetch=args.rtl_weight_fetch)
                    if args.capture_first_layer and positions == 1 and layers == 0:
                        weights = unpack_from("<QQ", descriptor, 48)
                        down, = unpack_from("<Q", descriptor, len(descriptor)-128+48)
                        first_ffn = dict(activation=activation, weights=(*weights, down))
                        (args.out / "first-ffn-input.bin").write_bytes(capture(u, 0, 512))
                    for target in range(3):
                        page_providers[(target, *P[1:])] = ffn.provider(target)
                elif descriptor[:4] == b"\x01PP\x02" and descriptor[83] == 1:
                    vocabulary = Vocabulary(projection)
                    page_providers[P] = vocabulary.provider
                dispatch_start = clock.now
                samples = defaultdict(lambda: [0, 0, 0])
                instruction_cycles = 0
                mother_wait_ps = 0

                def record_wait(duration):
                    nonlocal mother_wait_ps
                    mother_wait_ps += duration

                def mother_instruction(opcode):
                    nonlocal instruction_cycles
                    # Fetch, registered SRAM return and decode, with one
                    # additional edge to accept a CALL in the transport.
                    cycles = 6 + (opcode == 0x10)
                    instruction_cycles += cycles
                    ready = []
                    clock.after(cycles * scheduler.core_ps, lambda: ready.append(True))
                    clock.until(lambda: bool(ready))

                def measure(provider, issue, dispatch, terminal):
                    row = samples[provider]
                    row[0] += 1
                    row[1] += dispatch - issue
                    row[2] += terminal - dispatch

                av_before = attention.stats["av_read_requests"]
                av_legacy_before = attention.stats["av_legacy_read_requests"]
                run_page(page, topology=topology, descriptor_base=base, descriptor_bytes=size,
                         scheduler=scheduler, providers=page_providers,
                         after_wait=ffn.after_wait if ffn else None, timing=measure,
                         instruction=mother_instruction, wait_timing=record_wait)
                timing_file.write(json.dumps(dict(
                    generation=page["generation"], step=step, page=index, start_ps=page_start,
                    ingress_end_ps=ingress_end, pm_end_ps=pm_end, dispatch_start_ps=dispatch_start,
                    end_ps=clock.now, ddr=dict(dram.stats-ddr_start),
                    av_read_requests=attention.stats["av_read_requests"] - av_before,
                    av_legacy_read_requests=attention.stats["av_legacy_read_requests"] - av_legacy_before,
                    mother_instruction_cycles=instruction_cycles,
                    mother_wait_ps=mother_wait_ps,
                    mid_barrier_ps=ffn.mid_barrier_ps if ffn else 0,
                    sram_port_wait_ps=sum(s.stats["port_wait_ps"] - sram_start[name]["port_wait_ps"]
                                          for name, s in srams.items()),
                    sram={name: dict(s.stats - sram_start[name]) for name, s in srams.items()},
                    # Concurrent CALL intervals are sums of service time, not page elapsed time.
                    calls=[dict(provider=key, count=row[0], descriptor_ps=row[1], service_ps=row[2])
                           for key, row in samples.items()])) + "\n")
                timing_file.flush()
                if ffn is not None and (ffn.scope_count, ffn.mid_count) != (192, 86):
                    raise ValueError("FFN did not complete its sealed scopes and Mid tiles")
                if awaiting_residual:
                    tail = descriptor[-128:]
                    if (page["targets"] != 8 or tail[:4] != b"\x03\0\0\0" or tail[6] != 2 or
                            unpack_from("<4H", tail, 16) != (512, 0, 0, 512)):
                        raise ValueError("layer has no committed final residual after Down")
                    layers += 1
                    awaiting_residual = False
                elif descriptor[:4] == b"FDS8":
                    awaiting_residual = True
                    if first_ffn is not None and positions == 1 and layers == 0:
                        address, = unpack_from("<Q", descriptor, 24)
                        (args.out / "first-ffn-down.bin").write_bytes(b"".join(
                            memory(address + offset) for offset in range(0, 8192, 64)))
                        (args.out / "first-ffn-binding.json").write_text(json.dumps(
                            dict(first_ffn, down=address)) + "\n", encoding="ascii")
                if vocabulary is not None:
                    if index+1 != phase["page_count"] or layers != 36 or len(retired) != step - int(decode):
                        raise ValueError("token retirement was not at a complete phase boundary")
                    if decode:
                        memory.finish(step)
                    retired.append((vocabulary.retire(), clock.now))
                    log(dict(step=step, token=retired[-1][0], retirement_ps=clock.now))
                completed += 1
                if completed <= 10 or completed % 1000 == 0:
                    log(dict(generation=completed, step=step, page=index, position=positions-1,
                             time_ps=clock.now, ddr=dict(dram.stats)))
            if prefill_end:
                if (completed != prefill_end or step != 0 or
                        (positions, layers, len(retired)) != (args.prefill_tokens, 36, 0) or
                        awaiting_residual or memory.pending):
                    raise ValueError("short prefill did not finish every selected position")
            elif decode:
                if (completed != sum(p["page_count"] for p in phases[1:3]) or image.read(1) or
                        (positions, layers, len(retired)) != (514, 36, 2) or awaiting_residual):
                    raise ValueError("two-step decode did not exhaust the selected phases")
            elif not prefix and (completed != page_count or next(extents, None) is not None or image.read(1) or
                               (positions, layers, len(retired)) != (639, 36, 128) or ffns or ingress or
                               awaiting_residual):
                raise ValueError("whole-request execution did not exhaust the deployment")
        dram.close()
        if dram.stats["reads"] + dram.stats["writes"] != dram.stats["callbacks"]:
            raise ValueError("DDR callbacks failed to reconcile")
        result = dict(pages=completed, positions=positions, retirements=retired, ddr=dict(dram.stats),
                      completed_layers_in_current_position=layers,
                      timing_calibrated=False, numerically_accepted=False,
                      sram_port_bits=args.sram_port_bits,
                      pipeline_memory=args.pipeline_memory, av_value_fetch=args.av_value_fetch,
                      rtl_weight_fetch=args.rtl_weight_fetch,
                      sram={name: dict(s.stats) for name, s in srams.items()},
                      attention_kv=dict(window=args.kv_read_window, **attention.stats),
                      dma_scope=("32 credits per channel and rolling issue limits with FIFO arbitration"
                                 if args.dma_fabric_budget else "one credit per channel with FIFO arbitration"))
        if prefill_end:
            result.update(initial_history=0, elapsed_ps=clock.now,
                          deployment_sha256=args.deployment_sha256,
                          scope="native mother program prompt processing with modeled local services")
        elif not prefix:
            result["retirement_interval_ps"] = retired[-1][1] - retired[0][1]
        if decode:
            result.update(initial_history=512, kv_cross_step_read_beats=len(memory.reread),
                          deployment_sha256=args.deployment_sha256, kv_binding_sha256=args.decode_kv_sha256,
                          scope="two native mother program decode phases with modeled local services")
        (args.out / "execution.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    finally:
        if image is not None:
            image.close()


if __name__ == "__main__":
    main()
