"""Cycle-driven read timing backend for a live DRAMsim3 subprocess.

One model edge equals one DRAM tick. Poll completions before making requests
at that edge. The read callback carries timing and identity, with data supplied
by the caller's memory model. Writes require a separate visibility contract.
"""

from pathlib import Path
import subprocess


class DramLive:
    def __init__(self, binary, config, output_dir, *, model_period_ps=None, capacity_bytes):
        if type(capacity_bytes) is not int or not 64 <= capacity_bytes <= 1 << 64 or capacity_bytes % 64:
            raise ValueError("DRAM capacity must describe whole 64-byte bursts")
        if model_period_ps is not None and (type(model_period_ps) is not int or model_period_ps <= 0):
            raise ValueError("model clock period must be a positive integer in picoseconds")
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=False)
        self._stderr = (output / "bridge.stderr.log").open("w", encoding="utf-8")
        self._pending = {}
        self._identities = set()
        self._serial = 0
        self._cycle = 0
        self.capacity_bytes = capacity_bytes
        self._process = None
        try:
            self._process = subprocess.Popen(
                [str(Path(binary).resolve()), str(Path(config).resolve()), str(output)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                encoding="ascii", bufsize=1,
            )
            response = self._read()
            if len(response) != 2 or response[0] != "READY":
                raise RuntimeError("invalid DRAM bridge startup response: {}".format(response))
            self.period_ps = int(response[1])
            if self.period_ps <= 0 or model_period_ps is not None and self.period_ps != model_period_ps:
                raise ValueError("model edge period does not equal the DRAM tick period")
        except BaseException:
            self._dispose()
            raise

    @property
    def idle(self):
        """True after all accepted read transactions have returned."""
        return not self._pending

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
        if type(cycle) is not int or cycle != self._cycle:
            raise ValueError("poll DRAM completions at the current edge before submitting")
        if beat.write is not False:
            raise ValueError("DRAMsim3 write callback proves admission only; live writes are unsupported")
        if type(beat.address) is not int or beat.address % 64 or not 0 <= beat.address < self.capacity_bytes:
            raise ValueError("invalid or out-of-range 64-byte DRAM address")
        if beat.identifier in self._identities:
            raise ValueError("duplicate live DRAM transaction identity")

    def can_accept(self, cycle, beat):
        self._check_beat(cycle, beat)
        response = self._command("CAN {}".format(beat.address))
        if response not in (["CAN", "0"], ["CAN", "1"]):
            raise RuntimeError("invalid DRAM admission response: {}".format(response))
        return response[1] == "1"

    def submit(self, cycle, beat):
        self._check_beat(cycle, beat)
        serial = self._serial
        response = self._command("READ {} {}".format(serial, beat.address))
        if response != ["READ", str(serial)]:
            raise RuntimeError("invalid DRAM read submission response: {}".format(response))
        self._pending[serial] = (beat.identifier, beat.address)
        self._identities.add(beat.identifier)
        self._serial += 1

    def completions(self, cycle):
        if type(cycle) is not int or cycle < self._cycle:
            raise ValueError("DRAM model edges must be nondecreasing integers")
        elapsed = cycle - self._cycle
        if not elapsed:
            return []
        if elapsed != 1 and not self.idle:
            raise ValueError("poll every DRAM edge while reads are live")
        response = self._command("TICK {}".format(elapsed))
        if len(response) < 2 or response[0] != "DONE" or len(response) != 2 + 2 * int(response[1]):
            raise RuntimeError("invalid DRAM completion response: {}".format(response))
        completed = []
        for index in range(2, len(response), 2):
            serial, address = map(int, response[index:index + 2])
            if serial not in self._pending or self._pending[serial][1] != address:
                raise RuntimeError("DRAM callback identity or address does not match a live transaction")
            identity, _ = self._pending.pop(serial)
            self._identities.remove(identity)
            completed.append(identity)
        self._cycle = cycle
        return completed

    def close(self):
        if self._process is None:
            return
        try:
            if not self.idle:
                raise RuntimeError("DRAM bridge closed before reads drained")
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
