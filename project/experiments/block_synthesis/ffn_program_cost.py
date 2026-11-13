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
        from ffn_program import finish_program, programmed_ffn
        program = programmed_ffn(start, self.mode, self.seed, lookahead=self.lookahead,
                                 copy_delay_epoch=self.copy_delay_epoch)
        cost = finish_program(program, start, start + 2_000_000)
        if (cost.read_bytes, cost.write_bytes) != (READ_BYTES, LOCAL_WRITE_BYTES):
            raise ValueError('calibrated FFN program traffic differs')
        return cost
