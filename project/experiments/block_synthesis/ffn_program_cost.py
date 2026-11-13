"""Cost a qualified #251 FFN program at its actual launch edge."""
from dataclasses import dataclass
from functools import lru_cache


# Descriptor and weight reads at the external interface, and local result
# writes reported by the fixture. Only reads contribute to external traffic.
READ_BYTES = 71884800
LOCAL_WRITE_BYTES = 96256
INPUT_BYTES = 8192
RESULT_BYTES = (2752, 2720, 2720)
RESOURCES = dict.fromkeys(('MC', 'DDR', 'U.S.port', *(f'P{p}.{unit}' for p in range(3)
                                                    for unit in ('LC', 'S.port', 'M'))), 1)
SITES = ('U', 'P0', 'P1', 'P2')
SHARED_RESOURCES = {name: count for name, count in RESOURCES.items() if name != 'DDR'}
EXTERNAL_CLIENTS = frozenset(range(3, 9))
DESCRIPTOR_BASE = 0x1000
BACKING = ((DESCRIPTOR_BASE, 0x7000), (0x02000000, 0x036D8000),
           (0x04000000, 0x056D8000), (0x06000000, 0x076D8000))


def qualified_cost(cost):
    if (cost.read_bytes, cost.write_bytes) != (READ_BYTES, LOCAL_WRITE_BYTES):
        raise ValueError('calibrated FFN program traffic differs')
    return cost


@dataclass(frozen=True, slots=True)
class FfnCost:
    result_tick: int
    read_bytes: int
    write_bytes: int


@dataclass(frozen=True)
class Program:
    mode: int
    seed: int
    lookahead: bool
    copy_delay_epoch: int
    address_offset: int = 0

    @classmethod
    def from_spec(cls, spec):
        required = {'mode', 'seed', 'lookahead', 'copy_delay_epoch'}
        if (not isinstance(spec, dict)
                or not required <= spec.keys() <= required | {'address_offset'}
                or type(spec['mode']) is not int or spec['mode'] not in (0, 1)
                or type(spec['seed']) is not int or not 0 <= spec['seed'] < 2**32
                or type(spec['lookahead']) is not bool
                or type(spec['copy_delay_epoch']) is not int
                or not 0 <= spec['copy_delay_epoch'] <= 1444):
            raise ValueError('invalid calibrated FFN program')
        program = cls(**spec)
        offset = program.address_offset
        # Preserve descriptor alignment and the provider's channel-select bit.
        if type(offset) is not int or offset % 4096 or not 0 <= offset <= 2**64 - BACKING[-1][1]:
            raise ValueError('invalid calibrated FFN address offset')
        return program

    @property
    def backing(self):
        return tuple((lo + self.address_offset, hi + self.address_offset) for lo, hi in BACKING)

    @lru_cache(maxsize=128)
    def receipt(self, start):
        # Delay the import because the native program itself uses event replay
        # to clock the scatter and result readback services.
        from ffn_program import finish_program
        return qualified_cost(finish_program(self.start(start), start, start + 2_000_000))

    def start(self, tick, fabric=None):
        from ffn_program import programmed_ffn
        return programmed_ffn(tick, self.mode, self.seed, lookahead=self.lookahead,
                              copy_delay_epoch=self.copy_delay_epoch, fabric=fabric,
                              address_offset=self.address_offset)


class ActiveProgram:
    def __init__(self, program, start, fabric):
        self.replay = program.start(start, fabric)
        self.deadline = start + 2_000_000

    def advance(self, tick):
        from event_replay import ReplayDeadlock
        if tick >= self.deadline:
            raise ReplayDeadlock('programmed FFN exceeded its replay horizon')
        events, reads = self.replay.advance_shared(tick)
        if 'result' not in events:
            return None, reads
        self.replay.validate()
        (read, write), = events['result']
        return qualified_cost(FfnCost(tick, read, write)), reads
