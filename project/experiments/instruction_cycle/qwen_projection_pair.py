"""Advance the first K128 activation and two EXEC records of 105530 Q.

Inputs are the predicted front end and first two typed weight transports.
Cycles use the pre-edge core count. The modeled path ends at the third
registered M weight request offer.
"""

from collections import deque

from qwen_drl1_cycle import gated_edge
from qwen_native_control import service_spans
from qwen_native_ddr import require
from qwen_projection_front import WORDS_A16, first_weight_offer
from qwen_prompt_cycle import BURST_BYTES, SRAM_ACCEPT_TO_ACK


COPY_WRITE, A_LOAD_READ, COPY_READ = 1, 2, 3
SRAM_OWNERS = 2
SRAM_CLIENTS = 4
OPERAND_BEATS = 8


def _activation_window(header_publish, mode):
    # Header phase-1 ACK, HEADER DONE, sequencer take, COPY start, and
    # request registration precede the first same-P scratch read.
    copy_start = header_publish + 4
    cycle = copy_start + 2
    offers = {COPY_READ: cycle}
    responses = deque()
    copy_reads, copy_writes, a_reads = [], [], []
    accepts = {COPY_READ: copy_reads, COPY_WRITE: copy_writes, A_LOAD_READ: a_reads}
    copy_acks, a_acks = [], []
    # The last quantizer scratch write belongs to client 3 and has drained.
    cursor = 0
    held = None

    while len(a_acks) < WORDS_A16:
        require(cycle - copy_start < 1024, "first Q activation window stalled")
        request_gate = gated_edge(cycle, mode, 7, 2) == cycle
        response_gate = gated_edge(cycle, mode, 11, 4) == cycle
        valid = {client for client, start in offers.items() if request_gate and start <= cycle}
        selected = held
        if selected is None:
            for offset in range(SRAM_CLIENTS):
                client = (cursor + offset) % SRAM_CLIENTS
                if client in valid:
                    selected = client
                    break

        # The shared 1RW S128 mux accepts one request per edge. Its FIFO
        # keeps two owners including the SRAM operation still in flight.
        pop = responses and responses[0][0] <= cycle and response_gate
        if selected in valid:
            if len(responses) < SRAM_OWNERS or pop:
                del offers[selected]
                accepts[selected].append(cycle)
                cursor = (selected + 1) % SRAM_CLIENTS
                held = None
            else:
                held = selected
                selected = None
        else:
            selected = None

        if pop:
            _, client = responses.popleft()
            if client == COPY_READ:
                offers[COPY_WRITE] = cycle + 1
            elif client == COPY_WRITE:
                copy_acks.append(cycle)
                # The non-prefetching copier issues after the destination
                # releases its hold. A LOAD only sees the new real prefix
                # after this edge and separately registers its read offer.
                if len(copy_acks) < WORDS_A16:
                    offers[COPY_READ] = cycle + 2
            else:
                a_acks.append(cycle)
        if selected is not None:
            responses.append((cycle + SRAM_ACCEPT_TO_ACK, selected))
        if A_LOAD_READ not in offers and len(a_reads) == len(a_acks) < len(copy_acks):
            offers[A_LOAD_READ] = cycle + 2
        cycle += 1

    require(len(copy_reads) == len(copy_writes) == len(copy_acks) == len(a_reads) == WORDS_A16
            and held is None and not offers and not responses, "incomplete first Q activation window")
    # Last A response creates the load receipt, which is offered once the
    # frontend selects the pending receipt. The COPY done has reached PROOF.
    return {"copy_start": copy_start, "copy_reads": copy_reads, "copy_writes": copy_writes,
            "copy_acks": copy_acks, "copy_last_ack": copy_acks[-1], "a_load_reads": a_reads,
            "a_load_acks": a_acks, "a_load_last_ack": a_acks[-1], "a_load_proof": a_acks[-1] + 2}


def _execute_record(join, m_ready):
    # W_JOIN completes before the guard command is pushed. The registered
    # guard issue selects its owner, then sends two 128-bit EXEC flits.
    guard_accept = join + 1
    exec_first_flit = guard_accept + 2
    exec_last_flit = exec_first_flit + 1
    a_use = exec_last_flit + 1
    m_start = max(exec_last_flit + 1, m_ready)

    # The A frontend presents a registered operand stream, and M consumes
    # all eight matching A/W beats at II=1 with the group pipeline empty.
    first_beat = max(a_use, m_start) + 1
    last_beat = first_beat + OPERAND_BEATS - 1
    input_eop = last_beat + 3  # M reply register, header, and metadata.
    raw_accept = last_beat + 3  # Product, sum, and accumulation registers.
    rf_offer = raw_accept + 3  # Scale product, RNE, and RF response register.
    rf_eop = max(rf_offer, input_eop + 1) + 2  # Registered two-flit RF reply, no result payload at K0.
    return {"w_join": join, "guard_accept": guard_accept, "exec_first_flit": exec_first_flit,
            "exec_last_flit": exec_last_flit, "a_use": a_use, "m_exec_start": m_start,
            "first_operand": first_beat, "last_operand": last_beat, "input_eop": input_eop,
            "raw_accept": raw_accept, "rf_offer": rf_offer, "rf_eop": rf_eop,
            "guard_terminal": rf_eop + 2, "m_idle": rf_eop + 2}


def projection_pair(call, front, first_weight, second_weight, mode):
    """Predict COPY, A LOAD, EXEC, and the observed-at-DDR third record boundary."""
    require(mode in (0, 1) and front == first_weight_offer(call, front["service_accept"], mode),
            "unexpected first Q activation and control prefix")
    fill_acks = []
    for prefix, weight in (("", first_weight), ("second_", second_weight)):
        require(weight["address"] == front[prefix + "weight_address"]
                and len(weight["client_responses"]) == front[prefix + "weight_record_beats"]
                and weight["client_accepts"][0] == front[prefix + "weight_source_offer"],
                "unexpected first Q weight transport")
        # All beats fill the bank, ACK pending is selected on the following
        # edge, then M registers it and P accepts the two flits.
        fill_acks.append(max(weight["client_responses"]) + 4)

    activation = _activation_window(front["header_publish"], mode)
    proof = activation["a_load_proof"]
    # This fixture reaches FILL_WAIT for both allocations and sees both
    # independent FILL replies before A readiness. An earlier proof would
    # need the competing ALLOC/FILL/EXEC reply scheduling modeled explicitly.
    require(fill_acks[0] < front["second_weight_source_offer"]
            and front["second_weight_source_offer"] + 2 < fill_acks[1] < proof,
            "first Q pair weight replies do not precede A LOAD proof")
    older = _execute_record(proof + 2, 0)
    # INPUT EOP moves the younger prepared record to W_JOIN while the
    # detached older record still owns the M RF response until retirement.
    younger = _execute_record(older["input_eop"] + 1, older["m_idle"])
    older["range_complete"] = older["guard_terminal"]
    younger["range_complete"] = younger["guard_terminal"] + 1
    require(older["range_complete"] < younger["range_complete"], "first Q pair did not retire in order")
    third_record_accept = younger["range_complete"] + 1
    # The K0 iterator held its third record while both context-create records
    # used the guard. It still needs the same BEGIN/CONTEXT/ALLOC command path.
    control_latency = front["weight_source_offer"] - front["first_record_accept"]
    raw = bytes.fromhex(call["descriptor_hex"])
    third = service_spans(raw[:4], call["operation"], raw)[2]
    return {**activation, "weight_fill_ack": fill_acks, "exec": [older, younger],
            "third_record_accept": third_record_accept,
            "third_weight_source_offer": third_record_accept + control_latency,
            "third_weight_address": third["address"], "third_weight_record_beats": third["bytes"] // BURST_BYTES}
