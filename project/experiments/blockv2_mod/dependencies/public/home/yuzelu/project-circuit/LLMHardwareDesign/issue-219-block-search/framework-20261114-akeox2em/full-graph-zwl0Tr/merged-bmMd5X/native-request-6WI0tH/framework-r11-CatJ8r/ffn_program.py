"""Program geometry and construction for the calibrated three-P FFN."""
from collections import defaultdict

from event_replay import ReplayDeadlock
from ffn_a import P_COUNT
from ffn_control import (CALL_TO_FETCH, DOWN_GROUPS, GATE_UP_COLUMNS, GATE_UP_STRIPES, STRIPE_COLUMNS,
                         MotherController, ScopeGroup)
from ffn_dispatch import ScopeAdmission
from ffn_m import Record
from ffn_m_issue import CommandLink
from ffn_p import ProgrammedP
from ffn_program_cost import DESCRIPTOR_BASE, FfnCost
from ffn_result import down_group_addresses
from ffn_scatter import stripe_fragments
from ffn_w import BEATS
from ffn_w_dma import WeightCommandLinks, WeightReplay


DOWN_SCOPE_COLUMNS = 384


def p_result_addresses(session, client):
    if session > GATE_UP_STRIPES:
        return tuple(down_group_addresses(session - GATE_UP_STRIPES - 1, DOWN_GROUPS, client))
    first = STRIPE_COLUMNS * (session - 1)
    width = min(STRIPE_COLUMNS, GATE_UP_COLUMNS - first)
    return tuple(fragment.scratch + word for fragment in stripe_fragments(first, width)
                 if fragment.client == client for word in range(fragment.words))


def p_k_slices(owner):
    return (GATE_UP_COLUMNS if owner > GATE_UP_STRIPES else 2048) // 128


def m_records(dispatches):
    """Expand each programmed (client, dispatch, scope) into its K128 records."""
    records = defaultdict(list)
    sequence = 0
    for client, dispatch, owner in dispatches:
        contexts = len(p_result_addresses(owner, client)) // 2
        slices = p_k_slices(owner)
        for k in range(slices):
            for context in range(contexts):
                sequence += 1
                # A_LAST releases its input slot. The first member of a
                # pair can retire directly from the detached result guard.
                retire_delay = 3 if context + 1 == contexts else context % 2
                records[client].append(Record(sequence, dispatch, owner, k * 128, context,
                                              k + 1 == slices, retire_delay))
    return records


def weight_address(client, record):
    """Address of an unheaded K128 weight record in the programmed fixture."""
    if record.scope > GATE_UP_STRIPES:
        base = 0x06000000
        first = DOWN_SCOPE_COLUMNS * (record.scope - GATE_UP_STRIPES - 1)
        group = record.context
    else:
        groups = len(p_result_addresses(record.scope, client)) // 4
        way, group = divmod(record.context, groups)
        base = (way + 1) * 0x02000000
        first = STRIPE_COLUMNS * (record.scope - 1)
    column = first + 8 * client + 24 * group
    index = (column // 8) * p_k_slices(record.scope) + record.k // 128
    return base + 64 * BEATS * index


def window_plan(records_by_client):
    keys = sorted({(record.scope, record.k) for records in records_by_client.values() for record in records})
    return [(scope, k, scope > GATE_UP_STRIPES, scope == 1) for scope, k in keys]


def scope_groups(records_by_client):
    last = defaultdict(dict)
    for client, records in records_by_client.items():
        for record in records:
            last[record.scope][client] = record.sequence
    return [ScopeGroup(owner, tuple(last[owner][p] for p in range(P_COUNT)), owner > GATE_UP_STRIPES)
            for owner in sorted(last)]


def programmed_ffn(start, mode, seed, *, lookahead=True, copy_delay_epoch=0, replay_class=WeightReplay, fabric=None,
                   address_offset=0):
    dispatches = ((client, -1, owner) for owner in range(1, GATE_UP_STRIPES + DOWN_GROUPS + 1)
                  for client in range(P_COUNT))
    records = m_records(dispatches)
    addresses = {p: {record.sequence: address_offset + weight_address(p, record) for record in rows}
                 for p, rows in records.items()}
    p = ProgrammedP(records, (), mode, lookahead=lookahead, copy_delay_epoch=copy_delay_epoch,
                    window_plan=window_plan(records), live_dispatch=True)
    links = WeightCommandLinks({client: CommandLink({r.sequence: r.stores for r in rows})
                                for client, rows in records.items()}, addresses, join_driver=p)
    mother = MotherController(start, scope_groups(records), p.lanes)
    admission = ScopeAdmission(start, mode, mother, p)
    options = {} if fabric is None else {'fabric': fabric}
    return replay_class(mode, seed, CALL_TO_FETCH, links=links, mother=mother, admission=admission,
                        descriptor_base=DESCRIPTOR_BASE + address_offset, **options)


def finish_program(replay, first, deadline):
    """Price the remaining program from a live replay or a copy of its state."""
    for tick in range(first, deadline):
        events = replay.advance(tick)
        if 'result' in events:
            replay.validate()
            (reads, writes), = events['result']
            return FfnCost(tick, reads, writes)
    raise ReplayDeadlock('programmed FFN exceeded its replay horizon')
