"""Schedule all K0 records and the first K1 weight offer for 105530 Q."""

from dataclasses import dataclass, field

from qwen_drl1_cycle import gated_edge
from qwen_native_control import service_spans
from qwen_native_ddr import require
from qwen_projection_front import WORDS_A16, WORDS_S32, first_weight_offer
from qwen_projection_pair import OPERAND_BEATS, _activation_window
from qwen_prompt_cycle import BURST_BYTES, SRAM_ACCEPT_TO_ACK


BEGIN, INPUT, RF, ALLOC, FILL = range(5)
WEIGHT_BANKS = 4


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
            # As in the M leaf, an EOP edge cannot also register a new reply.
            if self.fill_owner is None and self.fill_pending:
                ready, record = self.fill_pending[0]
                if ready <= cycle:
                    self.fill_pending.pop(0)
                    self.fill_owner = record
                    self._reply(cycle, FILL, record)
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

            for fill in self.transport.step(cycle):
                if fill.record_complete:
                    record = self.owners[fill.bank]
                    require(record.generation == fill.generation, "unexpected K0 weight generation")
                    self.fill_pending.append((cycle + 2, record))
            cycle += 1
        require(not self.owners and not self.replies and self.active_reply is None
                and not self.fill_pending and self.fill_owner is None and self.m_active is None, "K0 did not drain")


def _k1_header(last_k0_record_accept, mode):
    # The iterator registers the pending K1 A_first after K0's final record
    # admission. COPY/LOAD proof already released K0's stream lease. K0 EXEC
    # leaves results in RF, hence P SRAM scratch is available for quantization.
    first_scan = last_k0_record_accept + 4
    stride = SRAM_ACCEPT_TO_ACK + 1
    last_scan_ack = first_scan + (WORDS_S32 - 1) * stride + SRAM_ACCEPT_TO_ACK
    next_pair = last_scan_ack + 2
    for _ in range(WORDS_A16):
        write = gated_edge(next_pair + 2 * stride, mode, 7, 2)
        write_ack = gated_edge(write + SRAM_ACCEPT_TO_ACK, mode, 11, 4)
        next_pair = write_ack + 1
    return write_ack + 7


def run_k0(call, front, fabric, mode):
    """Predict K0 by stepping the live DDR fabric and the P/M ownership path."""
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
    records = [{"index": record.index, "address": record.address, "bank": record.bank,
                "generation": record.generation, "record_accept": record.accepted, **record.edges,
                "weight": transport.record_result(record.bank, record.generation)} for record in schedule.records]
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
    return {"activation": activation, "records": records, "k0_range_complete": schedule.k0_complete,
            "next_window": next_window}
