"""Install exact arithmetic substitutions for archived job 107361."""

import ctypes as c
from hashlib import sha256
from pathlib import Path
from struct import calcsize
import sys


PROJECTION_SHA256 = "089a55339de384182046211ef15407830a51aa619efc7ea6cb3181193407c739"
ATTENTION_SHA256 = "d15bdbd913ee8bc574e932b99e495f3832ef0f746f2eafc5ce9f362450052b68"
U_ARITHMETIC_SHA256 = "56cf35efb4546fdc93b6c466c850cf52c851be18099b16dc8ce1b22101229804"


class NativeMath:
    def __init__(self, library):
        self.library = c.CDLL(str(library))
        self.projection = self.library.fast_tlm_projection
        self.projection.restype = c.c_int
        self.projection.argtypes = (c.c_char_p, c.POINTER(c.c_int16), c.c_int, c.c_int,
                                    c.POINTER(c.c_int32))
        self.qk = self.library.fast_tlm_qk
        self.qk.restype = None
        self.qk.argtypes = (c.c_char_p, c.c_char_p, c.c_uint, c.POINTER(c.c_int32))
        self.av = self.library.fast_tlm_av
        self.av.restype = None
        self.av.argtypes = (c.c_char_p, c.c_char_p, c.c_uint, c.POINTER(c.c_uint64), c.POINTER(c.c_int64))
        self.activation = None
        self.activation_array = (c.c_int16 * 128)()
        self.prefix = (c.c_int32 * 8)()
        self.qk_results = (c.c_int32 * 8)()
        self.av_low = (c.c_uint64 * 8)()
        self.av_high = (c.c_int64 * 8)()

    def accelerate_projection(self, original):
        def accumulate(weights, activation, shift, prefix, head16):
            # The archived provider supplies one reused tuple per K128 tile.
            if type(weights) is not bytes or len(weights) != (1152 if head16 else 1088):
                return original(weights, activation, shift, prefix, head16)
            if activation is not self.activation:
                if (type(activation) is not tuple or len(activation) != 128 or
                        any(type(value) is not int or not -32768 <= value <= 32767 for value in activation)):
                    return original(weights, activation, shift, prefix, head16)
                self.activation_array[:] = activation
                self.activation = activation
            if (type(shift) is not int or not 0 <= shift <= 17 or type(prefix) is not list or len(prefix) != 8 or
                    any(type(value) is not int or not -(1 << 31) <= value < 1 << 31 for value in prefix)):
                return original(weights, activation, shift, prefix, head16)
            self.prefix[:] = prefix
            if not self.projection(weights, self.activation_array, shift, head16, self.prefix):
                # Preserve the original exception class, message and partial
                # mutation, including a failing lane after earlier updates.
                return original(weights, activation, shift, prefix, head16)
            prefix[:] = self.prefix[:]
        return accumulate

    def attention_scores(self, query, keys, n):
        if not 1 <= n <= 8 or len(query) != 512 or len(keys) != 512 * n:
            raise ValueError("unexpected archived QK payload")
        self.qk(query, keys, n, self.qk_results)
        return self.qk_results[:n]

    def attention_values(self, probs, values, n, sums):
        if not 1 <= n <= 128 or len(probs) != ((n + 3) // 4) * 16 or len(values) != 32 * n:
            raise ValueError("unexpected archived AV payload")
        self.av(probs, values, n, self.av_low, self.av_high)
        for lane in range(8):
            sums[lane] += (self.av_high[lane] << 64) | self.av_low[lane]


def install(library):
    """Enable only the two arithmetic loops in the pinned module versions."""
    import native_tlm_attention as attention
    import native_tlm_projection as projection
    import native_tlm_u as u_arithmetic

    for module, expected in ((projection, PROJECTION_SHA256), (attention, ATTENTION_SHA256),
                             (u_arithmetic, U_ARITHMETIC_SHA256)):
        source = Path(module.__file__).read_bytes()
        if sha256(source).hexdigest() != expected:
            raise ValueError("arithmetic source seal mismatch: " + module.__name__)
    if calcsize("i") != 4 or sys.byteorder != "little":
        raise ValueError("native arithmetic requires a little-endian 32-bit int ABI")

    native = NativeMath(Path(library).resolve())
    # Preserve all event/descriptor logic. The source seal restricts these
    # replacements to the archived scalar QK and AV loops.
    path = Path(attention.__file__)
    code = path.read_text(encoding="utf8")
    loops = (
        ('''                        q = unpack("<128i", q)
                        values = []
                        for row in range(n):
                            key = unpack_from("<128i", keys, 512 * row)
                            partial = rne(sum(a*b for a, b in zip(q, key)), 16)
                            values.append(s32(partial))''',
         "                        values = _fast_scores(q, keys, n)"),
        ('''                    probability = unpack("<" + "i"*(len(probs)//4), probs)
                    for row in range(n):
                        for lane, value in enumerate(unpack_from("<8i", values, 32*row)):
                            sums[lane] += probability[row]*value''',
         "                    _fast_values(probs, values, n, sums)"),
    )
    for original, replacement in loops:
        if code.count(original) != 1:
            raise ValueError("arithmetical substitution does not match archived source")
        # Preserve the source line numbers for any exception outside the loop.
        code = code.replace(original, replacement + "\n" * original.count("\n"), 1)
    attention._fast_scores = native.attention_scores
    attention._fast_values = native.attention_values
    exec(compile(code, str(path), "exec"), attention.__dict__)
    projection.accumulate = native.accelerate_projection(projection.accumulate)
