"""Live DRAM timing with exact host-clock sampling and bounded CDC queues."""

from collections import deque
from fractions import Fraction
from pathlib import Path
import subprocess


class DramLive:
    def __init__(self, binary, config, output_dir, *, model_period_ps=None, capacity_bytes,
                 request_depth=None, response_depth=None, request_sync_stages=2,
                 response_sync_stages=2, dram_phase_ps=0, allow_writes=False):
        """Use CDC FIFOs for unequal clocks or explicitly configured FIFO depths.

        Host edge 0 occurs at 0 ps; DDR tick 0 occurs at ``dram_phase_ps``.
        A transition is sampled on the first strictly later receiver edge,
        followed by the remaining synchronization stages. The request FIFO
        admits one host request and issues one DDR request per respective edge.
        A DDR issue reserves a response slot until the host consumes its event
        and the free-slot credit crosses back. Poll before offering at each edge.
        Equal periods with no CDC configuration retain direct timing.
        """
        if type(capacity_bytes) is not int or not 64 <= capacity_bytes <= 1 << 64 or capacity_bytes % 64:
            raise ValueError("DRAM capacity must describe whole 64-byte bursts")
        if model_period_ps is not None and (type(model_period_ps) not in (int, Fraction) or model_period_ps <= 0):
            raise ValueError("model clock period must be a positive exact number of picoseconds")
        stages = (request_sync_stages, response_sync_stages)
        depths = (request_depth, response_depth)
        if (any(type(n) is not int or n < 1 for n in stages)
                or any(n is not None and (type(n) is not int or n < 1) for n in depths)
                or type(dram_phase_ps) is not int or dram_phase_ps < 0 or type(allow_writes) is not bool):
            raise ValueError("invalid DRAM CDC configuration")
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=False)
        self._stderr = (output / "bridge.stderr.log").open("w", encoding="utf-8")
        self._pending = {}
        self._identities = set()
        self._addresses = set()
        self._requests = deque()
        self._responses = deque()
        self._request_credits = deque()
        self._response_credits = deque()
        self.events = []
        self._serial = 0
        self._last_host_accept = -1
        self.capacity_bytes = capacity_bytes
        self._process = None
        try:
            self._process = subprocess.Popen(
                [str(Path(binary).resolve()), str(Path(config).resolve()), str(output)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                encoding="ascii", bufsize=1,
            )
            response = self._read()
            if (len(response) not in (2, 3) or response[0] != "READY"
                    or len(response) == 3 and response[2] != "WR_COMPLETION"):
                raise RuntimeError("invalid DRAM bridge startup response: {}".format(response))
            self.period_ps = int(response[1])
            if not 0 <= dram_phase_ps < self.period_ps:
                raise ValueError("DRAM phase must be within one tick period")
            self.model_period_ps = Fraction(self.period_ps if model_period_ps is None else model_period_ps)
            self.supports_writes = len(response) == 3
            if allow_writes and not self.supports_writes:
                raise ValueError("DRAM bridge does not advertise write completion")
            self._allow_writes = allow_writes
            self.dram_phase_ps = dram_phase_ps
            self._cdc = (self.model_period_ps != self.period_ps or dram_phase_ps != 0
                         or any(depth is not None for depth in depths) or stages != (2, 2))
            self._request_depth = 2 if request_depth is None else request_depth
            self._response_depth = 2 if response_depth is None else response_depth
            self._request_sync = request_sync_stages
            self._response_sync = response_sync_stages
            self._cycle = -1 if self._cdc else 0
            self._ddr_tick = self._cycle
        except BaseException:
            self._dispose()
            raise

    @property
    def idle(self):
        """True once requests and completions have crossed both queues."""
        return not self._identities

    @property
    def transport_idle(self):
        """True after both queues drain and their pointer credits synchronize."""
        return self.idle and not self._request_credits and not self._response_credits

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.close()
        else:
            self._dispose()

    def _read(self):
        line = self._process.stdout.readline()
        if not line:
            raise RuntimeError("DRAM bridge exited without a reply; see bridge.stderr.log")
        return line.split()

    def _command(self, line):
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("DRAM bridge is closed; see bridge.stderr.log")
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()
        return self._read()

    def _check_beat(self, cycle, beat):
        if type(cycle) is not int or cycle < 0 or cycle != self._cycle:
            raise ValueError("poll DRAM completions at the current edge before submitting")
        if type(beat.write) is not bool:
            raise ValueError("invalid DRAM operation")
        if beat.write and not self._allow_writes:
            raise ValueError("DRAMsim3 write callback proves admission only; live writes are unsupported")
        if type(beat.address) is not int or beat.address % 64 or not 0 <= beat.address < self.capacity_bytes:
            raise ValueError("invalid or out-of-range 64-byte DRAM address")
        if beat.identifier in self._identities:
            raise ValueError("duplicate live DRAM transaction identity")

    def can_accept(self, cycle, beat):
        self._check_beat(cycle, beat)
        if beat.address in self._addresses:
            return False
        if self._cdc:
            return (cycle != self._last_host_accept
                    and len(self._requests) + len(self._request_credits) < self._request_depth)
        return self._can_ddr(beat)

    def _can_ddr(self, beat):
        command = "CAN {}".format(beat.address)
        if self.supports_writes:
            command += " {}".format(int(beat.write))
        response = self._command(command)
        if response not in (["CAN", "0"], ["CAN", "1"]):
            raise RuntimeError("invalid DRAM admission response: {}".format(response))
        return response[1] == "1"

    def submit(self, cycle, beat):
        if not self.can_accept(cycle, beat):
            raise ValueError("DRAM request submitted without a free admission slot")
        self._addresses.add(beat.address)
        self._identities.add(beat.identifier)
        self._last_host_accept = cycle
        ready = self._to_ddr(cycle * self.model_period_ps) if self._cdc else cycle
        self._event("host_accept", beat, cycle=cycle, request_ready_tick=ready)
        if self._cdc:
            self._requests.append((ready, beat))
        else:
            self._submit_ddr(ready, beat)

    def _submit_ddr(self, tick, beat):
        serial = self._serial
        kind = "WRITE" if beat.write else "READ"
        response = self._command("{} {} {}".format(kind, serial, beat.address))
        if response != [kind, str(serial)]:
            raise RuntimeError("invalid DRAM submission response: {}".format(response))
        self._pending[serial] = (beat, tick)
        self._serial += 1
        self._event("ddr_accept", beat, tick=tick)

    def _event(self, name, beat, **fields):
        self.events.append(dict(event=name, identifier=beat.identifier, address=beat.address,
                                write=beat.write, **fields))

    def _to_ddr(self, time_ps):
        sample = max(0, (time_ps - self.dram_phase_ps) // self.period_ps + 1)
        return sample + self._request_sync - 1

    def _to_host(self, time_ps):
        return time_ps // self.model_period_ps + self._response_sync

    def _ddr_time(self, tick):
        return self.dram_phase_ps + tick * self.period_ps

    @staticmethod
    def _release_credits(credits, edge):
        while credits and credits[0] <= edge:
            credits.popleft()

    def _tick(self, elapsed, tick):
        response = self._command("TICK {}".format(elapsed))
        width = 4 if self.supports_writes else 2
        if len(response) < 2 or response[0] != "DONE" or len(response) != 2 + width * int(response[1]):
            raise RuntimeError("invalid DRAM completion response: {}".format(response))
        for index in range(2, len(response), width):
            serial, address, *timing = map(int, response[index:index + width])
            entry = self._pending.get(serial)
            if entry is None or entry[0].address != address:
                raise RuntimeError("DRAM callback identity or address does not match a live transaction")
            beat, accepted = entry
            done, command = timing if timing else (tick, -1)
            if (done != tick or done <= accepted or (beat.write and not accepted <= command <= done)
                    or (not beat.write and command != -1)):
                raise RuntimeError("invalid DRAM callback timing or write command identity")
            del self._pending[serial]
            host_ready = self._to_host(self._ddr_time(done)) if self._cdc else done
            self._responses.append((host_ready, beat))
            self._event("ddr_complete", beat, tick=done, command_tick=None if command == -1 else command,
                        host_ready_cycle=host_ready)

    def _advance_cdc(self, target):
        while self._ddr_tick < target:
            tick = self._ddr_tick + 1
            if not self._pending and not self._requests:
                tick = target
            elapsed = tick - max(0, self._ddr_tick)
            if elapsed > 0:
                self._tick(elapsed, tick)
            self._ddr_tick = tick
            self._release_credits(self._response_credits, tick)
            reserved = len(self._pending) + len(self._responses) + len(self._response_credits)
            if self._requests and self._requests[0][0] <= tick and reserved < self._response_depth:
                _, beat = self._requests[0]
                if self._can_ddr(beat):
                    self._submit_ddr(tick, beat)
                    self._requests.popleft()
                    self._request_credits.append(self._to_host(self._ddr_time(tick)))

    def completions(self, cycle):
        if type(cycle) is not int or cycle < 0 or cycle < self._cycle:
            raise ValueError("DRAM model edges must be nondecreasing integers")
        elapsed = cycle - self._cycle
        if not elapsed:
            return []
        if elapsed != 1 and not self.idle:
            raise ValueError("poll every host edge while DRAM transactions are live")
        if self._cdc:
            target = (cycle * self.model_period_ps - self.dram_phase_ps) // self.period_ps
            self._advance_cdc(target)
            self._release_credits(self._request_credits, cycle)
        else:
            self._tick(elapsed, cycle)
        completed = []
        while self._responses and self._responses[0][0] <= cycle:
            _, beat = self._responses.popleft()
            self._identities.remove(beat.identifier)
            self._addresses.remove(beat.address)
            completed.append(beat.identifier)
            self._event("host_complete", beat, cycle=cycle)
            if self._cdc:
                self._response_credits.append(self._to_ddr(cycle * self.model_period_ps))
                break
        self._cycle = cycle
        return completed

    def close(self):
        if self._process is None:
            return
        try:
            if not self.idle:
                raise RuntimeError("DRAM bridge closed before transactions drained")
            if self._command("EXIT") != ["EXIT"] or self._process.wait(timeout=5) != 0:
                raise RuntimeError("DRAM bridge did not exit cleanly")
        finally:
            self._dispose()

    def _dispose(self):
        if self._process is not None:
            if self._process.poll() is None:
                self._process.kill()
                self._process.wait()
            self._process.stdin.close()
            self._process.stdout.close()
            self._process = None
        self._stderr.close()
