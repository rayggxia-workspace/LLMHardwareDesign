"""Schedule the first two K128 windows of the 105530 Q projection."""

from collections import deque
from dataclasses import dataclass, field

from qwen_drl1_cycle import gated_edge
from qwen_native_control import service_spans
from qwen_native_ddr import require
from qwen_projection_front import WORDS_A16, WORDS_S32, first_weight_offer
from qwen_projection_pair import OPERAND_BEATS, _activation_window
from qwen_prompt_cycle import BURST_BYTES, SRAM_ACCEPT_TO_ACK


BEGIN, INPUT, RF, ALLOC, FILL = range(5)
WEIGHT_BANKS = 4
CONVERT_READ, PACKED_WRITE = range(2)


@dataclass
class Record:
    index: int
    address: int
    beats: int
    accepted: int
    bank: int = -1
    generation: int = 0
    edges: dict = field(default_factory=dict)


class K0Schedule:
    """Successful K0 create path with a real shared M→P response link."""

    def __init__(self, transport, activation, spans):
        self.transport = transport
        self.activation = activation
        self.spans = spans
        self.records = []
        self.owners = {}
        self.generations = [0] * WEIGHT_BANKS
        self.bank_cursor = 0
        self.actions = {}
        self.replies = []
        self.active_reply = None
        self.fill_owner = None
        self.fill_pending = []
        self.m_available = 0
        self.m_active = None
        self.k0_complete = None

    def _schedule(self, cycle, action, record):
        self.actions.setdefault(cycle, []).append((action, record))

    def _new_record(self, cycle):
        index = len(self.records)
        span = self.spans[index]
        record = Record(index, span["address"], span["bytes"] // BURST_BYTES, cycle)
        self.records.append(record)
        # The record executes eight BEGIN flits, then M registers its reply.
        self._schedule(cycle + 9, "begin", record)

    def _reply(self, ready, kind, record):
        self.replies.append((ready, kind, record))

    def _advance_replies(self, cycle):
        if self.fill_owner is None:
            candidates = [item for item in self.fill_pending if item[0] <= cycle]
            if candidates:
                selected = min(candidates, key=lambda item: item[1].bank)
                self.fill_pending.remove(selected)
                _, self.fill_owner = selected
                # Weight bank ACK owner selection is registered before the
                # independent M reply register sees the FILL valid.
                self._reply(cycle + 1, FILL, self.fill_owner)
        if self.active_reply is None:
            available = [item for item in self.replies if item[0] <= cycle]
            if available:
                chosen = min(available, key=lambda item: item[1])
                self.replies.remove(chosen)
                _, kind, record = chosen
                self.active_reply = (cycle + 2, kind, record)
        elif self.active_reply[0] == cycle:
            _, kind, record = self.active_reply
            self.active_reply = None
            self._on_reply(cycle, kind, record)

    def _step_weights(self, cycle):
        for fill in self.transport.step(cycle):
            if fill.record_complete:
                record = self.owners[fill.bank]
                require(record.generation == fill.generation, "unexpected projection weight generation")
                self.fill_pending.append((cycle + 1, record))

    def _on_action(self, cycle, action, record):
        if action == "record":
            self._new_record(cycle)
        elif action == "begin":
            self._reply(cycle + 1, BEGIN, record)
        elif action == "context":
            self._reply(cycle + 1, RF, record)
        elif action == "allocate":
            for offset in range(WEIGHT_BANKS):
                bank = (self.bank_cursor + offset) % WEIGHT_BANKS
                if bank not in self.owners:
                    break
            else:
                raise ValueError("K0 create has no free M weight bank")
            self.generations[bank] += 1
            record.bank, record.generation = bank, self.generations[bank]
            self.owners[bank] = record
            self.bank_cursor = (bank + 1) % WEIGHT_BANKS
            record.edges["weight_allocated"] = cycle
            record.edges["weight_table_installed"] = cycle + 1
            self.transport.install_record(cycle + 1, record.address, bank, record.generation, beats=record.beats)
            self._reply(cycle + 1, ALLOC, record)
        elif action == "execute":
            self._launch(cycle, record)
        elif action == "m_start":
            if self.m_active is not None or cycle < self.m_available:
                self._schedule(cycle + 1, action, record)
            else:
                self._start(cycle, record)
        elif action == "release":
            del self.owners[record.bank]
            self.transport.release_record(cycle, record.bank)

    def _launch(self, join, record):
        # W_JOIN, guard command and registered issue, two P→M EXEC flits.
        guard = join + 1
        eop = guard + 3
        a_use = eop + 1
        record.edges.update(w_join=join, guard_accept=guard, exec_first_flit=eop - 1,
                            exec_last_flit=eop, a_use=a_use)
        self._schedule(a_use, "m_start", record)

    def _start(self, cycle, record):
        self.m_active = record
        first = cycle + 1
        last = first + OPERAND_BEATS - 1
        raw_accept = last + 3
        rf_offer = raw_accept + 3
        record.edges.update(m_exec_start=cycle, first_operand=first, last_operand=last,
                            raw_accept=raw_accept, rf_offer=rf_offer)
        self._reply(last + 1, INPUT, record)
        self._reply(rf_offer, RF, record)

    def _on_reply(self, cycle, kind, record):
        edges = record.edges
        if kind == BEGIN:
            edges["begin_eop"] = cycle
            # P takes BEGIN, pushes CTX then sends its one-flit command.
            self._schedule(cycle + 4, "context", record)
        elif kind == RF and "rf_offer" not in edges:
            edges["context_eop"] = cycle
            self._schedule(cycle + 4, "allocate", record)
        elif kind == ALLOC:
            edges["allocate_eop"] = cycle
            if record.index % 2 == 0:
                # ALLOC_WAIT consumes ACK, then FILL_WAIT starts the pair.
                self._schedule(cycle + 3, "record", None)
            else:
                self._try_older(record)
        elif kind == FILL:
            edges["fill_eop"] = cycle
            self.fill_owner = None
            if record.index % 2 == 0 and len(self.records) > record.index + 1:
                self._try_older(self.records[record.index + 1])
            elif record.index % 2 and "input_eop" in self.records[record.index - 1].edges:
                self._schedule(cycle + 2, "execute", record)
        elif kind == INPUT:
            edges["input_eop"] = cycle
            self._schedule(cycle + 1, "release", record)
            if record.index % 2 == 0:
                younger = self.records[record.index + 1]
                if "fill_eop" in younger.edges:
                    self._schedule(cycle + 1, "execute", younger)
        else:
            edges["rf_eop"] = cycle
            require(self.m_active is record, "K0 RF completion has no active operand owner")
            self.m_active = None
            self.m_available = cycle + 2
            edges["guard_terminal"] = cycle + 2
            # Older pair member is detached at INPUT EOP. Active younger
            # member enters COMPLETE, or closes and releases the final A slot.
            complete = cycle + (2 if record.index % 2 == 0 else 3)
            if record.index == len(self.spans) - 1:
                complete += 2
                self.k0_complete = complete
            elif record.index % 2:
                self._schedule(complete + 1, "record", None)
            edges["range_complete"] = complete

    def _try_older(self, younger):
        older = self.records[younger.index - 1]
        if "allocate_eop" not in younger.edges or "fill_eop" not in older.edges:
            return
        # Younger ALLOC_WAIT must first enter FILL_WAIT. Then real older W
        # and A receipts both unlock W_JOIN. Younger W may still be filling.
        join = max(younger.edges["allocate_eop"] + 3, older.edges["fill_eop"] + 2,
                   self.activation["a_load_proof"] + 2)
        self._schedule(join, "execute", older)

    def run(self, start):
        self._new_record(start)
        cycle = start
        while self.k0_complete is None or cycle <= self.k0_complete:
            require(cycle - start < 8192, "K0 projection stalled")
            for action, record in self.actions.pop(cycle, []):
                self._on_action(cycle, action, record)
            self._advance_replies(cycle)
            self._step_weights(cycle)
            cycle += 1
        require(not self.owners and not self.replies and self.active_reply is None
                and not self.fill_pending and self.fill_owner is None and self.m_active is None, "K0 did not drain")


class ResidentWindowSchedule(K0Schedule):
    """Advance one nonfinal K window with live RF contexts and W lookahead."""

    def __init__(self, previous, activation, spans):
        super().__init__(previous.transport, activation, spans)
        self.generations = previous.generations
        self.bank_cursor = previous.bank_cursor
        self.m_available = previous.m_available
        self.p_state = "idle"
        self.active_record = None
        self.pair_saved = None
        self.pair_stage = None
        self.ahead = deque()
        self.side = None
        self.guard_start = None
        self.guard_owned = set()
        self.range_offer_edge = None
        self.window_complete = None

    def _take_range(self, cycle):
        index = len(self.records)
        span = self.spans[index]
        record = Record(index, span["address"], span["bytes"] // BURST_BYTES, cycle)
        self.records.append(record)
        self.range_offer_edge = cycle + 2
        return record

    def _on_reply(self, cycle, kind, record):
        if kind == ALLOC:
            record.edges["allocate_eop"] = cycle
        elif kind == FILL:
            record.edges["fill_eop"] = cycle
            self.fill_owner = None
        elif kind == INPUT:
            record.edges["input_eop"] = cycle
            self._schedule(cycle + 1, "release", record)
            if self.p_state == "exec_wait" and self.pair_stage == "first":
                # The guard's INPUT EOP is combinational on its accepted
                # frame, and the linked P pair detaches on this edge.
                self.active_record, self.pair_saved = self.pair_saved, record
                self.pair_stage = "detached"
                self.p_state = "join" if "fill_eop" in self.active_record.edges else "fill"
        else:
            require(kind == RF and self.m_active is record, "resident RF reply has no EXEC owner")
            record.edges["rf_eop"] = cycle
            record.edges["guard_terminal"] = cycle + 2
            self.m_active = None
            self.m_available = cycle + 2

    def _link_ready(self, cycle):
        # The leaf may buffer one command frame during an older EXEC, but a
        # new header cannot overtake the buffered command's processing edge.
        return all(action not in ("allocate", "m_start") for action, _ in self.actions.get(cycle, ()))

    def _drive_commands(self, cycle):
        ready = self._link_ready(cycle)
        side_before = self.side
        if side_before is not None and ready:
            record, flit, is_ahead = side_before
            if flit == 0:
                self.side = record, 1, is_ahead
            else:
                self.side = None
                self._schedule(cycle + 1, "allocate", record)
                record.edges["allocate_last_flit"] = cycle
                if not is_ahead:
                    self.p_state = "alloc_ack"
        if self.guard_start is not None and cycle >= self.guard_start and ready and side_before is None:
            record = self.active_record
            if "exec_first_flit" not in record.edges:
                record.edges["exec_first_flit"] = cycle
            else:
                record.edges["exec_last_flit"] = cycle
                record.edges["a_use"] = cycle + 1
                self._schedule(cycle + 1, "m_start", record)
                self.guard_start = None
        return side_before

    def _front(self, cycle):
        if self.ahead:
            record = self.ahead[0]
            fill_eop = record.edges.get("fill_eop")
            return record if fill_eop is not None and fill_eop < cycle else None
        if len(self.records) < len(self.spans) and cycle >= self.range_offer_edge:
            return len(self.records)
        return None

    def _take_front(self, cycle, front):
        if isinstance(front, Record):
            self.ahead.popleft()
            front.edges["replay_accept"] = cycle
            self.p_state = "fill"
            return front
        record = self._take_range(cycle)
        # ALLOC_SEND becomes valid after the accepting edge.
        self.side = record, 0, False
        self.p_state = "alloc_send"
        return record

    def _terminal(self, cycle):
        record = self.active_record
        # A detached pair owner can retire while the other record executes.
        if self.pair_stage == "detached":
            older = self.pair_saved
            if older.edges.get("guard_terminal") == cycle:
                older.edges["range_complete"] = cycle
                self.guard_owned.remove(older.index)
                self.pair_saved = None
                self.pair_stage = None
        if self.p_state == "exec_wait" and record.edges.get("guard_terminal") == cycle:
            self.guard_owned.remove(record.index)
            self.p_state = "close" if record.index == len(self.spans) - 1 else "complete"

    def _advance_p(self, cycle):
        state = self.p_state
        record = self.active_record
        stage = self.pair_stage
        front = self._front(cycle)
        side = self._drive_commands(cycle)
        # Stage side selection and range enqueue from pre-edge state. A
        # just-admitted range record is invisible to the ahead transmit FSM.
        can_take = front is not None and (state == "idle" or state == "pair_accept")
        if side is None and (state in ("join", "exec_wait", "complete") or
                             (state == "idle" and front is None) or (state == "fill" and stage == "prepare")):
            pending = next((item for item in self.ahead if item.edges.get("allocate_last_flit") is None), None)
            if pending is not None:
                self.side = pending, 0, True
        if not can_take and stage in ("prepare", "first", "detached") and len(self.ahead) < 2 and \
                len(self.records) < len(self.spans) and cycle >= self.range_offer_edge:
            self.ahead.append(self._take_range(cycle))

        if can_take:
            self.active_record = self._take_front(cycle, front)
            if state == "pair_accept":
                self.pair_stage = "prepare"
        elif state == "alloc_ack" and "allocate_eop" in record.edges:
            self.p_state = "fill"
        elif state == "fill":
            if stage is None and record.index % 2 == 0:
                self.pair_saved = record
                self.p_state = "pair_accept"
            else:
                waiting = self.pair_saved if stage == "prepare" else record
                if "fill_eop" in waiting.edges and cycle > self.activation["a_load_proof"]:
                    if stage == "prepare":
                        self.active_record, self.pair_saved = self.pair_saved, record
                        self.pair_stage = "first"
                    self.p_state = "join"
        elif state == "join":
            record.edges["w_join"] = cycle
            self.p_state = "exec_push"
        elif state == "exec_push" and side is None and len(self.guard_owned) < 2:
            record.edges["guard_accept"] = cycle
            self.guard_owned.add(record.index)
            self.guard_start = cycle + 2
            self.p_state = "exec_issue"
        elif state == "exec_issue" and record.edges.get("a_use") == cycle:
            self.p_state = "exec_wait"
        elif state == "close":
            self.p_state = "release"
        elif state == "release":
            self.p_state = "complete"
        elif state == "complete":
            record.edges["range_complete"] = cycle
            self.p_state = "idle"
            if record.index == len(self.spans) - 1:
                self.window_complete = cycle
        self._terminal(cycle)

    def run(self, start):
        self.range_offer_edge = start
        cycle = start
        while self.window_complete is None:
            require(cycle - start < 8192, "resident Q window stalled")
            # Link readiness depends on a command that is pending at this
            # edge. Replies sampled here become visible to P next edge.
            self._advance_p(cycle)
            for action, record in self.actions.pop(cycle, []):
                self._on_action(cycle, action, record)
            self._advance_replies(cycle)
            self._step_weights(cycle)
            cycle += 1
        require(not self.owners and not self.replies and self.active_reply is None and not self.guard_owned
                and not self.ahead and not self.fill_pending and self.fill_owner is None, "resident Q window did not drain")


def _k1_header(last_k0_record_accept, mode):
    # The iterator registers the pending K1 A_first after K0's final record
    # admission. COPY/LOAD proof already released K0's stream lease. K0 EXEC
    # leaves results in RF, hence P SRAM scratch is available for quantization.
    first_scan = last_k0_record_accept + 4
    convert_start = first_scan + WORDS_S32 * (SRAM_ACCEPT_TO_ACK + 1) + 1
    issued_reads = issued_writes = written = 0
    allocated = [False, False]
    returned = [0, 0]
    held = inflight = None

    # One physical transaction is live at the prompt SRAM mux. The
    # quantizer can still present and lock a convert read while that mux
    # waits for its prior ACK. A newly ready pack cannot overtake it.
    cycle = convert_start
    while written < WORDS_A16:
        require(cycle - convert_start < 512, "Q packed quantization stalled")
        offer = held
        if offer is None:
            if issued_writes < WORDS_A16 and returned[issued_writes % 2] == 2:
                offer = (PACKED_WRITE, issued_writes)
            elif issued_reads < WORDS_S32 and (issued_reads % 2 or not allocated[issued_reads // 2 % 2]):
                offer = (CONVERT_READ, issued_reads)
        if inflight is not None and inflight[0] == cycle:
            _, kind, index = inflight
            inflight_ready = False
            inflight = None
            if kind == PACKED_WRITE:
                written += 1
                allocated[index % 2] = False
                returned[index % 2] = 0
            else:
                returned[index // 2 % 2] += 1
        else:
            inflight_ready = inflight is None

        if offer is not None:
            kind, index = offer
            if inflight_ready and (kind != PACKED_WRITE or gated_edge(cycle, mode, 7, 2) == cycle):
                response = cycle + SRAM_ACCEPT_TO_ACK
                if kind == PACKED_WRITE:
                    issued_writes += 1
                    response = gated_edge(response, mode, 11, 4)
                else:
                    issued_reads += 1
                    allocated[index // 2 % 2] = True
                inflight = (response, kind, index)
                held = None
            else:
                held = offer
        cycle += 1
    # Last write ACK, quantizer DONE, sequencer take, lease, and two headers.
    return cycle + 6


def run_k0(call, front, fabric, mode, *, through_k1=False):
    """Predict K0 and optionally K1 on the live DDR fabric."""
    from qwen_weight_pipeline import WeightPipeline

    require(mode in (0, 1) and front == first_weight_offer(call, front["service_accept"], mode),
            "unexpected first Q activation prefix")
    raw = bytes.fromhex(call["descriptor_hex"])
    spans = service_spans(raw[:4], call["operation"], raw)
    groups = raw[74]
    require(groups == 16 and len(spans) == 256, "unexpected Q group count")
    activation = _activation_window(front["header_publish"], mode)
    transport = WeightPipeline(fabric)
    schedule = K0Schedule(transport, activation, spans[:groups])
    schedule.run(front["first_record_accept"])
    records = _record_results(schedule)
    require(records[0]["weight"]["client_accepts"][0] == front["weight_source_offer"]
            and records[1]["weight"]["client_accepts"][0] == front["second_weight_source_offer"],
            "K0 does not reproduce the initial two control offers")

    header = _k1_header(schedule.records[-1].accepted, mode)
    accept = max(header, schedule.k0_complete) + 1
    # Existing RF context means K1 begins with two ALLOC flits, not BEGIN.
    install = accept + 4
    next_window = {"header_publish": header, "first_record_accept": accept, "first_weight_table_installed": install,
                   "first_weight_source_offer": install + 2, "first_weight_address": spans[groups]["address"],
                   "first_weight_record_beats": spans[groups]["bytes"] // BURST_BYTES}
    result = {"activation": activation, "records": records, "k0_range_complete": schedule.k0_complete,
              "next_window": next_window}
    if through_k1:
        k1_activation = _activation_window(header, mode)
        k1 = ResidentWindowSchedule(schedule, k1_activation, spans[groups:2 * groups])
        k1.run(accept)
        result["k1"] = {"activation": k1_activation, "records": _record_results(k1),
                        "range_complete": k1.window_complete}
    return result


def _record_results(schedule):
    return [{"index": record.index, "address": record.address, "bank": record.bank,
             "generation": record.generation, "record_accept": record.accepted, **record.edges,
             "weight": schedule.transport.record_result(record.bank, record.generation)}
            for record in schedule.records]
