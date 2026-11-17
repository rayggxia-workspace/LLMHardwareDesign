"""Sample frozen attention services with real KV prefixes and a declared fixed query.

This is a component timing experiment, not a full-model numerical replay.
Recurrent probes use fixed-size zero/frozen512 states, never pretend that a
truncated recurrent tensor is a genuine intermediate-prefix state.
"""
import argparse
from collections import Counter
from bisect import bisect_right
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, pack_into, unpack_from
import sys
from types import SimpleNamespace
from zlib import crc32

from fast_qwen3_short import BatchedClock
from fast_tlm_replay import DramBridge
from native_tlm_timing import Images, S128
from native_tlm_projection import Projection
from attention_compact import TiledAttention
from attention_wide import WideAttention
from pr272_native_attention import Attention
from hybrid_short import Recurrent

ATT1 = int.from_bytes(b'ATT1', 'little')
CONTEXTS = [1, 2, 4, 7, 8, 9, 16, 32, 64, 65, 128, 129, 256, 257, 512]


def digest(path):
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


class Memory:
    def __init__(self, plan, assets, image, synthetic=None, zero_state=None):
        self.base = image
        self.history = plan['representative_history']['images']
        self.assets = assets
        self.loaded = {}
        self.written = {}
        self.synthetic = synthetic
        self.zero_state = zero_state
        self.proof = {}
        self.read_beats = 0
        self.write_beats = 0
        self.allowed_writes = [(base, size) for _, base, size in plan.get('recurrent_regions', [])]
        self.expected = {item['address']: item['sha256'] for item in plan['images']}

    def __call__(self, address):
        self.read_beats += 1
        if address in self.written:
            return self.written[address]
        if self.synthetic and self.synthetic[0] <= address < sum(self.synthetic):
            return pack('<16i', *([64] * 16))
        if self.zero_state and self.zero_state[0] <= address < sum(self.zero_state):
            return bytes(64)
        for item in self.history:
            base, size = item['address'], item['bytes']
            if base <= address < base + size:
                if base not in self.loaded:
                    path = self.assets / item['file']
                    raw = path.read_bytes()
                    value = sha256(raw).hexdigest()
                    if value != item['sha256'] or len(raw) != size:
                        raise ValueError('historical image failed SHA/size')
                    self.loaded[base] = raw
                    self.proof[str(path)] = value
                raw = self.loaded[base][address-base:address-base+64]
                if len(raw) != 64:
                    raise ValueError('historical read exceeds snapshot')
                return raw
        base = self.base.bases[bisect_right(self.base.bases, address)-1]
        _, path = self.base.regions[base]
        if str(path) not in self.proof:
            value = digest(path)
            if value != self.expected[base]:
                raise ValueError('immutable input hash mismatch')
            self.proof[str(path)] = value
        return self.base(address)

    def begin_write(self, address, tag, payload):
        if tag != address // 64 or len(payload) != 64 or not any(
                base <= address < base + size for base, size in self.allowed_writes):
            raise ValueError('recurrent write outside declared state')
        def commit():
            self.written[address] = payload
            self.write_beats += 1
        return commit


def descriptors(plan, images):
    found = []
    for layer, pages in enumerate(plan['phases'][0]['layers']):
        for page in pages:
            for index in range(page['count']):
                base = page['descriptor_base'] + 128 * index
                raw = images(base) + images(base + 64)
                if crc32(raw[:124]) != unpack_from('<I', raw, 124)[0]:
                    raise ValueError('descriptor CRC failed')
                schema, size, opcode, abi, topology = unpack_from('<IHHII', raw)
                if schema in (ATT1, 15, 18):
                    found.append(dict(layer=layer, page=page['path'], index=index,
                                      schema=schema, raw=raw, address=base))
    return found


def sample(plan, assets, images, item, context, state, out, library, ini):
    out.mkdir()
    clock = BatchedClock()
    dram = DramBridge(clock, library, ini, out, credits=32, core_ps=3334)
    ram = [S128(clock, core_ps=3334, port_bits=512) for _ in range(4)]
    for bank in ram:
        bank.words = {word: bytes(16) for word in range(1024)}
    record = bytearray(item['raw'])
    synthetic = zero = None
    if item['schema'] == 18:
        mode, _, _, source, before, after, params = unpack_from('<HHI4Q', record, 16)
        channels, depth = (8192, 128) if mode == 1 else (4608, 256)
        synthetic = (source, (channels + 4096 + (64 if mode == 1 else 32)) * 4)
        if state == 'zero':
            zero = (before, 32 * 128 * depth * 4 + channels * 16)
    else:
        pack_into('<H', record, 16, context)
        if item['schema'] == ATT1:
            pack_into('<H', record, 18, context - 1)
            width = plan['kv_row'] // 4
        else:
            width = 256
        query_word = unpack_from('<H', record, 20)[0]
        query = pack('<{}i'.format(width), *[(i % 17 - 8) * 64 for i in range(width)])
        for index in range(width // 4):
            ram[0].words[query_word+index] = query[index*16:index*16+16]
    pack_into('<I', record, 124, crc32(record[:124]))
    memory = Memory(plan, assets, images, synthetic, zero)
    proj = Projection(clock, dram, memory, ram[3], ram[0], source_word=0, scratch_word=944)
    if item['schema'] == 18:
        service = Recurrent(SimpleNamespace(plan=plan, proj=[proj], sram=ram, memory=memory, dram=dram))
        callback = service.bind(record)
    elif item['schema'] == 15:
        service = WideAttention(proj, pipeline=True)
        callback = service.bind(record)
    elif plan['kv_row'] == 256 or plan.get('tiled_attention128'):
        service = TiledAttention(proj, width, pipeline=True)
        callback = service.bind(record)
    else:
        service = Attention(clock, dram, memory, proj, kv_window=8, pipeline=True)
        callback = service.provider(record)
    complete = []
    callback(lambda: complete.append(True))
    clock.until(lambda: bool(complete))
    elapsed = clock.now
    stats = dict(dram.stats)
    if stats['reads'] + stats['writes'] != stats['callbacks'] or dram.pending:
        raise ValueError('sample DMA did not drain')
    dram.close()
    output = b''.join(ram[1 if item['schema'] == 18 else 0].words[i]
                      for i in (range(1024) if item['schema'] == 18 else range(832, 832+width//4)))
    return dict(layer=item['layer'], schema=item['schema'], context=context, state=state,
                elapsed_ps=elapsed, ddr=stats, sram=[dict(x.stats) for x in ram],
                descriptor_sha256=sha256(record).hexdigest(), output_sha256=sha256(output).hexdigest(),
                history_inputs=memory.proof, recurrent_write_beats=memory.write_beats,
                scope='isolated frozen service; no controller/projection competition; fixed synthetic query/input')


def main():
    parser = argparse.ArgumentParser()
    for name in ('model', 'baseline', 'library', 'ini', 'output'):
        parser.add_argument(name)
    args = parser.parse_args()
    baseline, out = Path(args.baseline), Path(args.output)
    out.mkdir()
    assets = baseline / 'assets'
    frozen = json.loads((baseline / 'result.json').read_text())
    if digest(assets / 'plan.json') != frozen['plan_sha256']:
        raise ValueError('frozen plan mismatch')
    plan = json.loads((assets / 'plan.json').read_text())
    if plan['history'] != 512 or not plan.get('three_p'):
        raise ValueError('requires accepted live512 three-P plan')
    images = Images(assets / 'ddr-initial.tsv')
    all_records = descriptors(plan, images)
    attention = [x for x in all_records if x['schema'] != 18]
    candidates = sorted(set(x['layer'] for x in attention))
    chosen_layers = sorted(set([candidates[0], candidates[len(candidates)//2], candidates[-1]] +
                              ([5] if args.model == 'gemma' else [])))
    selected = [next(x for x in attention if x['layer'] == layer) for layer in chosen_layers]
    result = dict(model=args.model, frozen_plan_sha256=frozen['plan_sha256'],
                  base_commit='89b02b0424e3ab923fca320509a4058692bd5f97',
                  contexts=CONTEXTS, selected_layers=chosen_layers, attention=[], recurrent=[],
                  full_model_validation='deferred by user', real_prefix_activations=False,
                  methodology='actual DRAMsim3/S128 and frozen ATT services; live KV prefixes; fixed query',
                  python=sys.version, inputs={'plan': digest(assets/'plan.json'), 'ini': digest(Path(args.ini)),
                                              'dram_library': digest(Path(args.library))})
    for item in selected:
        for context in CONTEXTS:
            row = sample(plan, assets, images, item, context, None,
                         out / ('attention-l{}-c{}'.format(item['layer'], context)), Path(args.library), Path(args.ini))
            result['attention'].append(row)
            print('ATT_SAMPLE', args.model, item['layer'], context, row['elapsed_ps'], flush=True)
    recurrent = [x for x in all_records if x['schema'] == 18]
    if recurrent:
        for item in (recurrent[0], recurrent[-1]):
            for state in ('zero', 'frozen512'):
                row = sample(plan, assets, images, item, None, state,
                             out / ('recurrent-l{}-{}'.format(item['layer'], state)), Path(args.library), Path(args.ini))
                result['recurrent'].append(row)
                print('REC_SAMPLE', args.model, item['layer'], state, row['elapsed_ps'], flush=True)
    result['source_files'] = {str(Path(mod.__file__).resolve()): digest(Path(mod.__file__))
                              for mod in list(sys.modules.values()) if getattr(mod, '__file__', None)
                              and ('/public/home/' in str(mod.__file__) or '/LLMHardware/zenanyan/' in str(mod.__file__))
                              and str(mod.__file__).endswith('.py')}
    result['source_files'][str(Path(__file__).resolve())] = digest(Path(__file__))
    (out / 'samples.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print('MODEL_SAMPLING_COMPLETE', args.model, len(result['attention']), len(result['recurrent']), flush=True)


if __name__ == '__main__':
    main()
