"""Derive a strict width/group audit without modifying the frozen R4 audit.

The original arithmetic, DDR, private-S, capacity, latency and byte inventories
remain intact. New configurations replace the old single-port bound with actual
per-group service bounds and an independently enumerated pool-address ledger.
This module only reads/generates Python audit text; it runs no simulation.
"""
import hashlib
import importlib.util
from pathlib import Path

FROZEN_AUDIT_SHA256 = 'ca20aaa9de6c3968338db87b02ebca4db0b3d9a6601719a88e18a5042435fa9c'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('frozen width-audit anchor is not unique: ' + repr(old))
    return text.replace(old, new)


# This is an independent address/amount inventory. It does not import model
# scheduling code, synthesize model output, or project counters to legacy ones.
GROUP_CHECKS = r'''


def _group_inventory(facts, item):
    reads = [0] * WIDTH_GROUPS
    writes = [0] * WIDTH_GROUPS
    worker_reads = [[0] * WIDTH_GROUPS for _ in range(2)]
    worker_cycles = [0, 0]
    pair = 'pair' in item['variant']
    weight_bytes = 1 if item['profile'] == 'queued_pipe_w8' else 2
    workspace = 1536 if 'combine' in item['variant'] else 1024

    def owner(line):
        require(0 <= line < 512, 'pool line exceeds the fixed 32KiB physical extent')
        if WIDTH_GROUPS == 1:
            return 0
        return line // 256 if WIDTH_MAPPING == 'contiguous' else line % 2

    for op in facts['operations']:
        rows, stride, covered = op['rows'], op['row_stride_bytes'], op['covered_k']
        require(rows <= 2, 'width main-case inventory needs extension for rows > 2')
        for r in range(rows):
            # Row padding is present in capacity and bus work, never payload.
            for line in range(r * stride // 64, (r * stride + covered * 4 + 63) // 64):
                writes[owner(line)] += 1
        full_a = rows * op['k'] * 4
        max_k = (16384 - rows * 96 - workspace) // (2 * (rows * 4 + 8 * weight_bytes))
        tile_k = min(256, max(8, max_k // 8 * 8))
        if full_a + rows * 96 + workspace < 16384:
            resident_k = (16384 - full_a - rows * 96 - workspace) // (16 * weight_bytes)
            if resident_k >= 8:
                tile_k = min(tile_k, resident_k // 8 * 8)
        ncols = [sum(((col // (16 if pair else 8)) % 2) == p
                     for col in range(0, op['cols'], 8)) for p in range(2)]
        for ki in range(0, op['k'], tile_k):
            count = min(tile_k, op['k'] - ki)
            shared_k = max(0, min(count, covered - ki))
            if not shared_k:
                continue
            for r in range(rows):
                first = r * stride + ki * 4
                last = first + shared_k * 4
                for line in range(first // 64, (last + 63) // 64):
                    group = owner(line)
                    valid = min(last, (line + 1) * 64) - max(first, line * 64)
                    require(0 < valid <= 64 and valid % 4 == 0, 'independent line mask')
                    for p in range(2):
                        worker_reads[p][group] += ncols[p]
                        reads[group] += ncols[p]
                        if WIDTH_BYTES <= 64:
                            worker_cycles[p] += ((valid + WIDTH_BYTES - 1) // WIDTH_BYTES) * ncols[p]
    return dict(reads=reads, writes=writes, worker_reads=worker_reads,
                worker_cycles=worker_cycles)


def _integer_vector(meta, key, size):
    value = meta[key]
    require(isinstance(value, list) and len(value) == size and
            all(type(x) is int and x >= 0 for x in value), 'invalid group vector ' + key)
    return value


def _check_group_ports(meta, facts, item, row):
    require(meta['service_groups'] == WIDTH_GROUPS and meta['bank_mapping'] == WIDTH_MAPPING,
            'physical service-group configuration drift')
    require(meta['fill_ingress_bytes_per_cycle'] == 64,
            'group replication silently widened the shared fill ingress')
    busy = _integer_vector(meta, 'group_service_subcycles', WIDTH_GROUPS)
    reads = _integer_vector(meta, 'group_read_beats', WIDTH_GROUPS)
    writes = _integer_vector(meta, 'group_write_beats', WIDTH_GROUPS)
    waits = _integer_vector(meta, 'group_wait_subcycles', WIDTH_GROUPS)
    lane_busy = _integer_vector(meta, 'bank_service_subcycles', 4 * WIDTH_GROUPS)
    inventory = _group_inventory(facts, item)
    require(reads == inventory['reads'] and writes == inventory['writes'],
            'group read/write ownership differs from independent pool-address inventory')
    require(sum(reads) == meta['read_beats'] and sum(writes) == meta['write_beats'],
            'group reads/writes do not sum to global transfers')
    duration = item['pool_port_cycles'] * 1000
    require(busy == [(reads[g] + writes[g]) * duration for g in range(WIDTH_GROUPS)],
            'per-group port service does not charge each real 64B transaction')
    require(sum(busy) == meta['port_service_subcycles'], 'group/global service sum mismatch')
    require(sum(waits) == meta['port_wait_subcycles'], 'group/global port-wait sum mismatch')
    require(lane_busy == [busy[g] for g in range(WIDTH_GROUPS) for _ in range(4)],
            'four lanes per service group do not conserve SRAM service')
    require(all(b <= row['detail']['end_subcycles'] for b in busy),
            'one physical group overlaps its own service')
    return inventory


def _check_consumer_width(worker, index, inventory, item):
    cycles = worker['consumer_cycles']
    peak = worker['consumer_peak_bytes_per_cycle']
    pairs = worker['two_line_consume_cycles']
    issue_peak = worker['issue_peak_per_cycle']
    require(0 < cycles and 0 < peak <= WIDTH_BYTES and peak % 4 == 0,
            'consumer clock/width receipt invalid')
    require(0 <= pairs <= cycles and 0 < issue_peak <= (2 if WIDTH_BYTES == 128 else 1),
            'consumer pair or per-P issue width exceeds the selected datapath')
    require(worker['consumed_bytes'] <= cycles * WIDTH_BYTES and
            worker['feed_subcycles'] >= cycles * 1000,
            'consumer bytes/elapsed time exceed selected per-P width')
    require(sum(inventory['worker_reads'][index]) == worker['reads'],
            'worker and group read counts disagree')
    if WIDTH_BYTES <= 64:
        require(cycles == inventory['worker_cycles'][index] and pairs == 0,
                'single-line consumer cycles differ from independent valid-byte masks')
    else:
        require(cycles + pairs == worker['reads'],
                '128B consumption must account for one or two actual FIFO lines per clock')
        require(peak <= 64 or pairs > 0, '128B peak reported without real two-line consumption')
        require(pairs == 0 or item['fifo_beats'] >= 2, 'two-line consume without two FIFO credits')
'''


GROUP_NEGATIVE_CHECKS = '''    if item['shared_pool_KiB'] and not WIDTH_LEGACY_CONTROL:
        changes += [
            ('group_service_lost', lambda r: r['shared_pool_study']['group_service_subcycles'].__setitem__(
                0, r['shared_pool_study']['group_service_subcycles'][0] + 1000)),
            ('group_read_ownership_wrong', lambda r: r['shared_pool_study']['group_read_beats'].__setitem__(
                0, r['shared_pool_study']['group_read_beats'][0] + 1)),
            ('group_write_ownership_wrong', lambda r: r['shared_pool_study']['group_write_beats'].__setitem__(
                0, r['shared_pool_study']['group_write_beats'][0] + 1)),
            ('group_wait_unaccounted', lambda r: r['shared_pool_study']['group_wait_subcycles'].__setitem__(
                0, r['shared_pool_study']['group_wait_subcycles'][0] + 1)),
            ('physical_lane_service_lost', lambda r: r['shared_pool_study']['bank_service_subcycles'].__setitem__(
                0, r['shared_pool_study']['bank_service_subcycles'][0] + 1000)),
            ('consumer_cycle_lost', lambda r: r['shared_pool_study']['P'][0].__setitem__(
                'consumer_cycles', r['shared_pool_study']['P'][0]['consumer_cycles'] - 1)),
            ('consumer_width_exceeded', lambda r: r['shared_pool_study']['P'][0].__setitem__(
                'consumer_peak_bytes_per_cycle', WIDTH_BYTES + 4)),
            ('per_P_issue_width_exceeded', lambda r: r['shared_pool_study']['P'][0].__setitem__(
                'issue_peak_per_cycle', 3 if WIDTH_BYTES == 128 else 2)),
            ('bank_mapping_changed', lambda r: r['shared_pool_study'].__setitem__('bank_mapping', 'invalid'))]
'''


def derive(repo, out, width, groups, mapping):
    if type(width) is not int or width not in (16, 32, 64, 128):
        raise ValueError('invalid A consumption width')
    if type(groups) is not int or groups not in (1, 2):
        raise ValueError('invalid service-group count')
    if mapping not in (('single',) if groups == 1 else ('contiguous', 'striped')):
        raise ValueError('mapping incompatible with group count')
    path = Path(repo) / 'project/experiments/shared_pool_study/audit.py'
    if sha(path) != FROZEN_AUDIT_SHA256:
        raise ValueError('frozen audit source identity changed')
    text = path.read_text(encoding='utf-8')
    legacy = groups == 1 and width in (16, 32)
    config = dict(width=width, groups=groups, mapping=mapping, legacy_control=legacy)
    prefix = ('# Generated strict width/group derivative of the SHA-locked shared-pool audit.\n'
              'WIDTH_BYTES = ' + repr(width) + '\nWIDTH_GROUPS = ' + repr(groups) +
              '\nWIDTH_MAPPING = ' + repr(mapping) + '\nWIDTH_LEGACY_CONTROL = ' + repr(legacy) + '\n')
    text = once(text, 'A_feeder_bytes_per_cycle=32', 'A_feeder_bytes_per_cycle=' + str(width))
    text = once(text, "((w['consumed_bytes'] + 31) // 32)",
                "((w['consumed_bytes'] + " + str(width-1) + ') // ' + str(width) + ')')
    text = once(text, 'its 32B/cycle feeder', 'its ' + str(width) + 'B/cycle feeder')
    text = once(text, '    flows, old_flows = base_check(row, baseline, item)',
                "    require(item['shared_pool_KiB'] in (0, 32), 'width study changed fixed pool capacity')\n"
                "    require(WIDTH_LEGACY_CONTROL or item['shared_pool_KiB'] == 32, 'new datapath requires the fixed 32KiB study pool')\n"
                '    flows, old_flows = base_check(row, baseline, item)')
    if not legacy:
        text = once(text,
            "banks=4, bank_width_bits=128, bank_mode='1RW lockstep lanes', fabric_bytes=64,",
            "banks=" + str(4*groups) + ", bank_width_bits=128, bank_mode='1RW lockstep lanes per group', fabric_bytes=" + str(64*groups) + ',')
        text = once(text,
            "    require(meta['bank_service_subcycles'] == [meta['port_service_subcycles']] * 4,\n"
            "            'four physical-width lanes do not conserve shared 1RW service')\n"
            "    require(meta['port_service_subcycles'] <= row['detail']['end_subcycles'],\n"
            "            'single shared pool fabric overlaps its own service')",
            '    width_inventory = _check_group_ports(meta, facts, item, row)')
        text = once(text,
            "        require(w['avoided_local_write_subcycles'] == w['avoided_A_DDR_bus_bytes'] // 64 * 1000",
            "        _check_consumer_width(w, index, width_inventory, item)\n"
            "        require(w['avoided_local_write_subcycles'] == w['avoided_A_DDR_bus_bytes'] // 64 * 1000")
    text = once(text, '    rejected = []', GROUP_NEGATIVE_CHECKS + '    rejected = []')
    text = prefix + text + GROUP_CHECKS
    compile(text, str(out), 'exec')
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise ValueError('refuse to overwrite derived audit: ' + str(out))
    out.write_bytes(text.encode('utf-8'))
    spec = importlib.util.spec_from_file_location('shared_width_audit_' + str(width) + '_' + str(groups) + '_' + mapping, out)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DERIVATION_CONFIG = config
    module.DERIVATION_SHA256 = sha(out)
    module.FROZEN_SOURCE_SHA256 = FROZEN_AUDIT_SHA256
    return module
