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
BACKING = ((0x1000, 0x7000), (0x02000000, 0x036D8000),
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

    @classmethod
    def from_spec(cls, spec):
        if (not isinstance(spec, dict)
                or spec.keys() != {'mode', 'seed', 'lookahead', 'copy_delay_epoch'}
                or type(spec['mode']) is not int or spec['mode'] not in (0, 1)
                or type(spec['seed']) is not int or not 0 <= spec['seed'] < 2**32
                or type(spec['lookahead']) is not bool
                or type(spec['copy_delay_epoch']) is not int
                or not 0 <= spec['copy_delay_epoch'] <= 1444):
            raise ValueError('invalid calibrated FFN program')
        return cls(**spec)

    @lru_cache(maxsize=128)
    def receipt(self, start):
        # Delay the import because the native program itself uses event replay
        # to clock the scatter and result readback services.
        from ffn_program import finish_program
        return qualified_cost(finish_program(self.start(start), start, start + 2_000_000))

    def start(self, tick, fabric=None):
        from ffn_program import programmed_ffn
        return programmed_ffn(tick, self.mode, self.seed, lookahead=self.lookahead,
                              copy_delay_epoch=self.copy_delay_epoch, fabric=fabric)


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
