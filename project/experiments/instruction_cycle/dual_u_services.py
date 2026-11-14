"""Narrow S, compact E, and stored-link protocol for the frozen two-U64 fixture."""

from dataclasses import dataclass, field
import struct


COMMAND, SEND, RECEIVE, RESERVE = 0x100, 0x101, 0x102, 0x103
E_CLIENT, RX_CLIENT, TX_CLIENT = 1, 2, 3
WORD_MASK = (1 << 128) - 1


def seed_memory(inputs):
    """Pack the three generated signed vectors as the fixture's S seed writes."""
    def word(name):
        values = inputs[name]
        if len(values) != 8 or any(type(value) is not int or not -32768 <= value < 32768 for value in values):
            raise ValueError("expected a single eight-lane S16 word")
        return int.from_bytes(struct.pack("<8h", *values), "little")

    return {0: {40: word("x"), 41: word("y")}, 1: {40: word("z")}}


def evaluate(op, shift, left, right):
    lhs = struct.unpack("<8h", left.to_bytes(16, "little"))
    rhs = struct.unpack("<8h", right.to_bytes(16, "little"))
    raw = [a + b for a, b in zip(lhs, rhs)] if op == 0 else [a * b for a, b in zip(lhs, rhs)]
    if op == 2 and shift:
        scale = 1 << shift
        half = scale // 2
        rounded = []
        for value in raw:
            quotient, remainder = divmod(value, scale)
            rounded.append(quotient + int(remainder > half or remainder == half and quotient % 2))
        raw = rounded
    result = [max(-32768, min(32767, value)) for value in raw]
    return int.from_bytes(struct.pack("<8h", *result), "little"), raw != result


@dataclass(frozen=True)
class Request:
    client: int
    addr: int
    write: bool = False
    data: int = 0


@dataclass
class Port:
    pointer: int
    saved: Request = None
    phase: str = "idle"
    visible: int = 0
    result: int = 0

    def advance(self, cycle, contenders, accepting, memory):
        """One old-state handshake, retaining owner through response acceptance."""
        if self.phase == "idle":
            for offset in range(4):
                client = (self.pointer + offset) % 4
                if client in contenders:
                    self.saved = contenders[client]
                    self.pointer = (client + 1) % 4
                    self.phase = "send"
                    return "S_GRANT", self.saved, 0
        elif self.phase == "send":
            request = self.saved
            if request.write:
                # local_s_base disables write-data echo. Visibility follows the
                # physical SRAM send; consumers receive credit on later S_RSP.
                memory[request.addr] = request.data
                self.result = 0
            elif request.addr in memory:
                self.result = memory[request.addr]
            else:
                raise ValueError("read of uninitialized private S word {}".format(request.addr))
            self.visible = cycle + 2
            self.phase = "return"
            return "S_SEND", request, 0
        elif cycle >= self.visible and self.saved.client in accepting:
            request = self.saved
            self.saved = None
            self.phase = "idle"
            return "S_RSP", request, self.result
        return None, None, 0


@dataclass
class Endpoint:
    port: Port
    adapter: str = "idle"
    execution: dict = None
    reserved: int = None
    committed: bool = False
    reads: int = 0
    writes: int = 0
    saturated: bool = False
    element: str = "idle"
    operand_index: int = 0
    operands: list = field(default_factory=list)
    e_visible: int = 0
    e_data: int = 0
    transport: str = "idle"
    tx_slot: str = "idle"
    tx_source: int = 0
    tx_dest: int = 0
    tx_data: int = 0


class Services:
    def __init__(self, inputs, request_period=1, request_phase=0, ack_period=1, ack_phase=0):
        for period, phase in ((request_period, request_phase), (ack_period, ack_phase)):
            if type(period) is not int or type(phase) is not int or not 0 <= phase < period:
                raise ValueError("invalid stored-link gate")
        if set(inputs) != {0, 1} or any(type(addr) is not int or not 0 <= addr < 1024
                                      or type(word) is not int or not 0 <= word <= WORD_MASK
                                      for words in inputs.values() for addr, word in words.items()):
            raise ValueError("invalid private S seed memory")
        self.memory = [dict(inputs[block]) for block in range(2)]
        # Every initialized block was seeded through RX client 2, making 3 next.
        self.endpoints = [Endpoint(Port(3 if inputs[block] else 0)) for block in range(2)]
        self.request_period, self.request_phase = request_period, request_phase
        self.ack_period, self.ack_phase = ack_period, ack_phase
        self.events = []
        self.last_cycle = None

    @property
    def active(self):
        return any(endpoint.adapter != "idle" or endpoint.port.phase != "idle" for endpoint in self.endpoints)

    def event(self, cycle, kind, **fields):
        self.events.append(dict(cycle=cycle, kind=kind, **fields))

    def start(self, endpoint, descriptor):
        op, n0, n1, n2 = (descriptor[key] for key in ("native_op", "native0", "native1", "native2"))
        n3 = descriptor.get("native3", 0)
        if any(type(value) is not int or value < 0 for value in (op, n0, n1, n2, n3)) or n3:
            raise ValueError("unsupported native descriptor")
        endpoint.reads = endpoint.writes = 0
        endpoint.saturated = False
        endpoint.execution = descriptor
        if op == COMMAND:
            if n0 >> 15 or (n0 & 31) != 24 or n1 >> 20 or n2 >> 9 or (n2 & 15) not in (0, 2):
                raise ValueError("unsupported compact E command")
            endpoint.adapter = "issue_e"
        elif op == SEND and not (n0 >> 20 or n1 or n2):
            endpoint.tx_source, endpoint.tx_dest = n0 & 1023, n0 >> 10
            endpoint.adapter = "issue_send"
        elif op == RESERVE and not (n0 >> 10 or n1 or n2) and endpoint.reserved is None:
            endpoint.reserved = n0
            endpoint.adapter = "response"
        elif op == RECEIVE and not (n0 or n1 or n2) and endpoint.reserved is not None:
            endpoint.adapter = "receive"
        else:
            raise ValueError("invalid or unsupported native service: {}".format(op))

    def element_cycle(self, cycle, block, endpoint, adapter, signal, request, response):
        phase = endpoint.element
        if phase == "idle" and adapter == "issue_e":
            endpoint.operand_index = 0
            endpoint.operands = []
            endpoint.element = "read"
            endpoint.adapter = "wait_e"
            self.event(cycle, "E_ISSUE", block=block, op=endpoint.execution["native2"] & 15)
        elif phase in ("read", "write") and signal == "S_GRANT" and request.client == E_CLIENT:
            endpoint.element = phase + "_response"
        elif phase in ("read_response", "write_response") and signal == "S_RSP" and request.client == E_CLIENT:
            if phase == "read_response":
                endpoint.operands.append(response)
                endpoint.element = "beat"
            else:
                endpoint.element = "done"
        elif phase == "beat":
            op = endpoint.execution["native2"] & 15
            self.event(cycle, "E_BEAT", block=block, op=op, beat=endpoint.operand_index)
            endpoint.operand_index += 1
            if endpoint.operand_index == 2:
                endpoint.e_visible = cycle + 4  # MUL, TOTAL, WRITE, then visible
                endpoint.element = "result"
            else:
                endpoint.element = "read"
        elif phase == "result" and cycle >= endpoint.e_visible:
            op = endpoint.execution["native2"] & 15
            shift = (endpoint.execution["native2"] >> 4) & 31
            endpoint.e_data, endpoint.saturated = evaluate(op, shift, *endpoint.operands)
            endpoint.element = "write"
            self.event(cycle, "E_RESULT", block=block, op=op)
        elif phase == "done" and adapter == "wait_e":
            endpoint.element = "idle"
            endpoint.adapter = "response"
            endpoint.reads, endpoint.writes = 32, 16
            self.event(cycle, "E_RETURN", block=block, op=endpoint.execution["native2"] & 15)

    def step(self, cycle, offered, response_ready):
        """Consume this pre-edge once. Controller offers and readiness come from old state."""
        if type(cycle) is not int or cycle < 0:
            raise ValueError("invalid service cycle")
        if self.last_cycle is not None:
            if cycle <= self.last_cycle or self.active and cycle != self.last_cycle + 1:
                raise ValueError("cannot replay an edge or skip active service cycles")
        self.last_cycle = cycle
        adapters = [endpoint.adapter for endpoint in self.endpoints]
        committed = [endpoint.committed for endpoint in self.endpoints]
        commands = []
        for block, endpoint in enumerate(self.endpoints):
            contenders, accepting = {}, set()
            if endpoint.element == "read":
                addr = (endpoint.execution["native1"] >> (10 * endpoint.operand_index)) & 1023
                contenders[E_CLIENT] = Request(E_CLIENT, addr)
            elif endpoint.element == "write":
                contenders[E_CLIENT] = Request(E_CLIENT, endpoint.execution["native0"] >> 5,
                                              True, endpoint.e_data)
            elif endpoint.element in ("read_response", "write_response"):
                accepting.add(E_CLIENT)
            if endpoint.transport == "read" and endpoint.tx_slot == "idle":
                contenders[TX_CLIENT] = Request(TX_CLIENT, endpoint.tx_source)
            elif endpoint.tx_slot == "read":
                accepting.add(TX_CLIENT)
            peer = self.endpoints[1 - block]
            if peer.transport == "offer" and peer.tx_slot == "held" and endpoint.reserved == peer.tx_dest:
                if not endpoint.committed and cycle % self.request_period == self.request_phase:
                    contenders[RX_CLIENT] = Request(RX_CLIENT, peer.tx_dest, True, peer.tx_data)
            if peer.transport == "commit" and peer.tx_slot == "held" and cycle % self.ack_period == self.ack_phase:
                accepting.add(RX_CLIENT)
            commands.append((contenders, accepting))

        writes, commits = set(), set()
        for block, (endpoint, (contenders, accepting)) in enumerate(zip(self.endpoints, commands)):
            if len(contenders) > 1:
                self.event(cycle, "S_CONTEND", block=block, mask=sum(1 << client for client in contenders))
            kind, request, response = endpoint.port.advance(cycle, contenders, accepting, self.memory[block])
            if kind is not None:
                self.event(cycle, kind, block=block, client=request.client, addr=request.addr,
                           write=int(request.write))
                if request.client == TX_CLIENT:
                    if kind == "S_GRANT":
                        endpoint.transport = "offer"
                        endpoint.tx_slot = "read"
                        self.event(cycle, "TX_READ", block=block, addr=request.addr)
                    elif kind == "S_RSP":
                        endpoint.tx_data = response
                        endpoint.tx_slot = "held"
                elif request.client == RX_CLIENT:
                    if kind == "S_GRANT":
                        writes.add(block)
                        self.event(cycle, "WRITE", src=1 - block, dst=block, addr=request.addr, data=request.data)
                    elif kind == "S_RSP":
                        commits.add(block)
                        self.event(cycle, "COMMIT", src=1 - block, dst=block, addr=request.addr, data=request.data)
                        self.event(cycle, "RELEASE", block=1 - block)
            self.element_cycle(cycle, block, endpoint, adapters[block], kind, request, response)

        accepted, returned = {}, {}
        for block, endpoint in enumerate(self.endpoints):
            adapter = adapters[block]
            if adapter == "idle" and block in offered:
                self.start(endpoint, offered[block])
                accepted[block] = offered[block]
            elif adapter == "response" and response_ready.get(block, False):
                returned[block] = dict(read_bytes=endpoint.reads, write_bytes=endpoint.writes,
                                       status=0, saturated=int(endpoint.saturated))
                endpoint.adapter = "idle"
            elif adapter == "issue_send":
                if endpoint.transport != "idle" or endpoint.tx_slot != "idle":
                    raise ValueError("stored link still owns a source slot")
                endpoint.transport = "read"
                endpoint.adapter = "wait_send"
            elif adapter == "receive" and committed[block]:
                endpoint.reserved = None
                endpoint.committed = False
                endpoint.writes = 16
                endpoint.adapter = "response"
            if 1 - block in writes:
                endpoint.transport = "commit"
            if 1 - block in commits:
                endpoint.transport = "idle"
                endpoint.tx_slot = "idle"
                endpoint.reads = 16
                endpoint.adapter = "response"
            if block in commits:
                endpoint.committed = True
        return accepted, returned
