"""Search range dispatches over access and service contracts, without op names.

A graph has one independently dispatchable output axis and optionally one
ordered reduction axis per operator. Other axes have already been fixed by
the graph adapter. State uses aligned cells, so every legal chunking shares
one progress lattice. Times model serialized reads, compute and writes over one SRAM pool and
one DDR link. After decoding inputs in the fixed workspace, this abstract
service may recycle dead input space before committing its outputs.
"""
from dataclasses import dataclass

from solver import Unsupported


@dataclass(frozen=True)
class Axis:
    extent: int
    alignment: int

    @property
    def cells(self):
        return (self.extent + self.alignment - 1) // self.alignment

    def offset(self, cell):
        return min(self.extent, cell * self.alignment)

    def size(self, start, stop):
        return self.offset(stop) - self.offset(start)


@dataclass(frozen=True)
class Access:
    value: str
    axis: str  # output, reduction, or full


@dataclass(frozen=True)
class Operator:
    value: str
    output: Axis
    record_bytes: int
    reads: tuple
    reduction: Axis = None
    static_bytes_per_pair: int = 0
    external_bytes_per_pair: int = 0
    export: bool = False


@dataclass(frozen=True)
class Offer:
    max_output_cells: int
    setup_ticks: int
    pairs_per_tick: int
    accumulator_bytes: int = 0
    max_reduction_cells: int = 0  # max cells per continuation; zero disables continuation


@dataclass(frozen=True)
class Hardware:
    sram_bytes: int
    ddr_bytes_per_tick: int
    sram_bytes_per_tick: int
    workspace_bytes: int = 0


@dataclass(frozen=True)
class Progress:
    out: int = 0
    stop: int = 0  # chosen output tile end while a reduction is open
    prefix: int = 0


@dataclass(frozen=True)
class State:
    progress: tuple
    resident: tuple
    backed: tuple


@dataclass
class Label:
    ticks: int
    ddr: int
    peak: int
    parent: object = None
    action: dict = None

def blocks(volume, rate):
    return (volume + rate - 1) // rate


def interval(start, stop):
    return ((1 << stop) - 1) ^ ((1 << start) - 1)


def span_choices(start, end, cap):
    """Consider aligned power-of-two widths and the last legal width."""
    limit = min(cap, end - start)
    width = 1
    while width < limit:
        yield start + width
        width *= 2
    if limit > 0:
        yield start + limit


class Frontier:
    def __init__(self, graph, offers, hardware, *, depth, width=None, objective='time'):
        self.graph = tuple(graph)
        self.offers = tuple(offers[node.value] for node in self.graph)
        self.hardware = hardware
        if (not self.graph or depth < 0 or width is not None and width < 1
                or objective not in ('time', 'ddr')
                or not 0 <= hardware.workspace_bytes < hardware.sram_bytes
                or min(hardware.sram_bytes, hardware.ddr_bytes_per_tick,
                       hardware.sram_bytes_per_tick) <= 0):
            raise ValueError('invalid frontier bounds or hardware')
        self.depth, self.width, self.objective = depth, width, objective
        self.capacity = hardware.sram_bytes - hardware.workspace_bytes
        known = {}
        reads = []
        users = [[] for _ in self.graph]
        for i, (node, service) in enumerate(zip(self.graph, self.offers)):
            if (node.value in known or node.output.extent < 1 or node.output.alignment < 1
                    or node.record_bytes < 1 or service.max_output_cells < 1
                    or service.setup_ticks < 0 or service.pairs_per_tick < 1
                    or service.accumulator_bytes < 0 or service.max_reduction_cells < 0
                    or min(node.static_bytes_per_pair, node.external_bytes_per_pair) < 0
                    or node.reduction and min(node.reduction.extent, node.reduction.alignment) < 1
                    or service.max_reduction_cells and not (node.reduction and service.accumulator_bytes)):
                raise ValueError('invalid operator or service: ' + node.value)
            mapped = []
            for read in node.reads:
                if read.value not in known or read.axis not in ('output', 'reduction', 'full'):
                    raise ValueError('access must refer to an earlier value and a known axis')
                source = known[read.value]
                axis = self.graph[source].output
                required = node.output if read.axis == 'output' else node.reduction
                if read.axis != 'full' and required != axis:
                    raise ValueError('incompatible access axis: ' + read.value)
                mapped.append((source, read.axis))
                users[source].append((i, read.axis))
            reads.append(tuple(mapped))
            known[node.value] = i
        self.reads = tuple(reads)
        self.users = tuple(map(tuple, users))
        self.exports = tuple(node.export or not users[i] for i, node in enumerate(self.graph))
        self.full = tuple(interval(0, node.output.cells) for node in self.graph)
        self.reductions = tuple(node.reduction.cells if node.reduction else 1 for node in self.graph)
        self.total = sum(node.output.cells * k for node, k in zip(self.graph, self.reductions))

    def size(self, i, mask):
        node = self.graph[i]
        axis = node.output
        count = mask.bit_count() * axis.alignment
        if mask & (1 << (axis.cells - 1)):
            count -= axis.cells * axis.alignment - axis.extent
        return count * node.record_bytes

    def used(self, progress, residents):
        return (sum(self.size(i, mask) for i, mask in enumerate(residents) if mask)
                + sum(self.graph[i].output.size(p.out, p.stop) * self.offers[i].accumulator_bytes
                      for i, p in enumerate(progress) if p.prefix))

    def live(self, i, progress):
        mask = 0
        for user, axis in self.users[i]:
            p = progress[user]
            extent = self.graph[user].output.cells
            if p.out == extent:
                continue
            lower = p.out if axis == 'output' else 0
            if axis == 'reduction' and p.stop == extent:
                lower = p.prefix
            mask |= self.full[i] & ~interval(0, lower)
        return mask

    def ranking(self, state, label):
        # Rank equal-cell-work states by estimated final cost. Cell work is
        # useful for topological order but is not comparable across operators.
        remaining_ticks = 0
        remaining_ddr = 0
        for i, (node, service, p) in enumerate(zip(self.graph, self.offers, state.progress)):
            work = node.output.size(p.out, node.output.cells)
            k = node.reduction.extent if node.reduction else 1
            work *= k
            if p.prefix:
                work -= node.output.size(p.out, p.stop) * node.reduction.offset(p.prefix)
            remaining_ticks += blocks(work, service.pairs_per_tick)
            remaining_ddr += work * (node.static_bytes_per_pair + node.external_bytes_per_pair)
            if self.exports[i]:
                remaining_ddr += node.output.size(p.out, node.output.cells) * node.record_bytes
            remaining_ddr += self.size(i, state.backed[i] & ~state.resident[i])
        remaining_ticks += blocks(remaining_ddr, self.hardware.ddr_bytes_per_tick)
        return self.cost(label.ticks + remaining_ticks, label.ddr + remaining_ddr, label.peak)

    def cost(self, ticks, ddr, peak):
        return (ticks, ddr, peak) if self.objective == 'time' else (ddr, ticks, peak)

    def legal_depth(self, progress, depth):
        longest = []
        for i, p in enumerate(progress):
            previous = max((longest[src] for src, _ in self.reads[i]), default=0)
            open_now = p.prefix > 0 or 0 < p.out < self.graph[i].output.cells
            longest.append(previous + int(open_now))
            if longest[-1] > depth:
                return False
        return True

    def actions(self, state, depth, continuation):
        for i, (node, service, p) in enumerate(zip(self.graph, self.offers, state.progress)):
            end = node.output.cells
            if p.out >= end:
                continue
            if p.prefix:
                stops = (p.stop,)
            elif depth == 0:
                stops = (end,) if end <= service.max_output_cells else ()
            else:
                stops = span_choices(p.out, end, service.max_output_cells)
            for stop in stops:
                limit = self.reductions[i]
                if not depth or not continuation or not service.max_reduction_cells:
                    next_prefixes = (limit,)
                else:
                    next_prefixes = tuple(span_choices(p.prefix, limit, service.max_reduction_cells))
                    if not p.prefix and next_prefixes[-1] != limit:
                        next_prefixes += (limit,)
                for prefix in next_prefixes:
                    yield from self.dispatch(state, i, stop, prefix, depth)

    def dispatch(self, state, i, stop, prefix, depth):
        node, service = self.graph[i], self.offers[i]
        p = state.progress[i]
        output = interval(p.out, stop)
        reduction = interval(p.prefix, prefix)
        finish = prefix == self.reductions[i]
        progress = list(state.progress)
        progress[i] = Progress(stop) if finish else Progress(p.out, stop, prefix)
        if not self.legal_depth(progress, depth):
            return
        from_ddr = {}
        local_bytes = 0
        for src, axis in self.reads[i]:
            if axis == 'output':
                mask = output
            elif axis == 'reduction':
                mask = reduction
            else:
                mask = self.full[src]
            if mask & ~(state.resident[src] | state.backed[src]):
                return
            cold = self.size(src, mask & ~state.resident[src])
            if cold:
                name = self.graph[src].value
                from_ddr[name] = from_ddr.get(name, 0) + cold
            local_bytes += self.size(src, mask & state.resident[src])

        outputs = node.output.size(p.out, stop)
        k = node.reduction.size(p.prefix, prefix) if node.reduction else 1
        weights = outputs * k * node.static_bytes_per_pair
        external = outputs * k * node.external_bytes_per_pair
        partial = outputs * service.accumulator_bytes * (int(bool(p.prefix)) + int(not finish))
        # Dead versions can be dropped after all reads in this dispatch.
        live = tuple(self.live(j, progress) for j in range(len(self.graph)))
        resident = [mask & needed for mask, needed in zip(state.resident, live)]
        backed = [mask & needed for mask, needed in zip(state.backed, live)]
        result_mask = output if finish else 0
        can_keep = bool(result_mask & live[i])
        choices = (False, True) if can_keep else (False,)
        for keep in choices:
            placed, saved = resident.copy(), backed.copy()
            writes = {}
            retained = result_mask & live[i] if keep else 0
            placed[i] |= retained
            saved[i] |= result_mask & live[i] & ~retained
            written = result_mask if self.exports[i] else result_mask & ~retained
            saved[i] |= written & live[i]
            volume = self.size(i, written)
            if volume:
                writes[node.value] = volume
            # Spill oldest aligned cells first if this transition needs space.
            # The current output can instead select its direct-DDR alternative.
            usage = self.used(progress, placed)
            for src, mask in enumerate(resident):
                while usage > self.capacity and mask:
                    cell = mask & -mask
                    mask ^= cell
                    size = self.size(src, cell)
                    usage -= size
                    placed[src] ^= cell
                    if not saved[src] & cell:
                        name = self.graph[src].value
                        writes[name] = writes.get(name, 0) + size
                        saved[src] |= cell
            if usage > self.capacity:
                continue
            ddr = sum(from_ddr.values()) + sum(writes.values()) + weights + external
            onchip = local_bytes + self.size(i, retained) + partial
            ticks = (service.setup_ticks + blocks(outputs * k, service.pairs_per_tick)
                     + blocks(ddr, self.hardware.ddr_bytes_per_tick)
                     + blocks(onchip, self.hardware.sram_bytes_per_tick))
            action = {'operator': node.value, 'output': [node.output.offset(p.out), node.output.offset(stop)],
                      'reduction': ([node.reduction.offset(p.prefix), node.reduction.offset(prefix)]
                                    if node.reduction else None),
                      'publishes': finish, 'retains_bytes': self.size(i, retained),
                      'sram_live_bytes': usage, 'sram_service_bytes': onchip,
                      'sram_reserved_bytes': usage + self.hardware.workspace_bytes,
                      'sram_partial_service_bytes': partial,
                      'read_bytes': from_ddr, 'write_bytes': writes, 'static_bytes': weights,
                      'external_input_bytes': external,
                      'ticks': ticks}
            advance = (stop - p.out) * (prefix - p.prefix)
            yield State(tuple(progress), tuple(placed), tuple(saved)), action, advance, ddr

    def solve(self):
        """Find a dispatch plan under the selected candidate and beam bounds."""
        labels, metrics = self.search(self.depth, self.width, True)
        metrics['incumbent_expanded'] = 0
        if self.depth and self.width is not None:
            # Preserve weaker plans even when the main beam drops them.
            variants = [(0, False)]
            if any(service.max_reduction_cells for service in self.offers):
                variants.append((self.depth, False))
            for depth, continuation in variants:
                baseline, counters = self.search(depth, self.width, continuation)
                metrics['incumbent_expanded'] += counters['expanded']
                labels.extend(baseline)
        if not labels:
            raise Unsupported('no complete range dispatch plan')
        best = min(labels, key=lambda label: self.cost(label.ticks, label.ddr, label.peak))
        actions = []
        cursor = best
        while cursor.parent:
            actions.append(cursor.action)
            cursor = cursor.parent
        return {'ticks': best.ticks, 'ddr_bytes': best.ddr, 'sram_peak': best.peak,
                **metrics, 'actions': actions[::-1]}

    def search(self, depth, width, continuation):
        count = len(self.graph)
        empty = State((Progress(),) * count, (0,) * count, (0,) * count)
        buckets = {0: {empty: Label(0, 0, 0)}}
        expanded = generated = pruned = 0
        for rank in range(self.total):
            labels = buckets.pop(rank, {})
            entries = labels.items()
            if width is not None and len(labels) > width:
                pruned += len(labels) - width
                entries = sorted(entries, key=lambda entry: self.ranking(*entry))[:width]
            for state, label in entries:
                expanded += 1
                for successor, action, advance, io in self.actions(state, depth, continuation):
                    generated += 1
                    step = Label(label.ticks + action['ticks'], label.ddr + io,
                                 max(label.peak, action['sram_reserved_bytes']), label, action)
                    bucket = buckets.setdefault(rank + advance, {})
                    previous = bucket.get(successor)
                    if (previous is None or self.cost(step.ticks, step.ddr, step.peak)
                            < self.cost(previous.ticks, previous.ddr, previous.peak)):
                        bucket[successor] = step
        return list(buckets.get(self.total, {}).values()), {
            'expanded': expanded, 'generated': generated, 'beam_pruned': pruned,
        }


def compile_ranges(contract, *, depth, width=None, objective='time'):
    """Compile typed range descriptors to a modeled dispatch and traffic plan."""
    graph, offers = [], {}
    services = {name: Offer(**item) for name, item in contract['services'].items()}
    for item in contract['operators']:
        value = item['value']
        node = Operator(value, Axis(**item['output']), item['record_bytes'],
                        tuple(Access(**read) for read in item.get('reads', ())),
                        Axis(**item['reduction']) if item.get('reduction') else None,
                        item.get('static_bytes_per_pair', 0), item.get('external_bytes_per_pair', 0),
                        item.get('export', False))
        graph.append(node)
        offers[value] = services[item['service']]
    hardware = Hardware(**contract['hardware'])
    return Frontier(graph, offers, hardware, depth=depth, width=width, objective=objective).solve()


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--depth', type=int, default=2)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--objective', choices=('time', 'ddr'), default='time')
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding='utf-8'))
    print(json.dumps(compile_ranges(contract, depth=args.depth, width=args.width, objective=args.objective), indent=2))


if __name__ == '__main__':
    main()
