"""Software-only finite_dma -> CONTROL_V1 descriptor translation.

Not a protocol bridge. C supplies tags; endpoint D supports S instance zero.
T streams require an explicit T->S drain and separate D store completion.
"""
def encode(mode, ext_base, ext_stride, rows, cols, s_base, s_stride):
    values = (mode, ext_base, ext_stride, rows, cols, s_base, s_stride)
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError('unsigned integer fields required')
    if mode not in (0, 1):
        raise ValueError('T direct stream is not a D operation')
    if not (1 <= rows <= 1024 and 1 <= cols <= 1024 and rows*cols <= 1024):
        raise ValueError('finite descriptor capacity')
    if ext_base >= 2**32 or ext_stride >= 2**32 or ext_base % 16 or ext_stride % 16:
        raise ValueError('finite external address/alignment')
    if ext_stride < cols*16 or ext_base+(rows-1)*ext_stride+cols*16 > 2**32:
        raise ValueError('external extent')
    if s_base >= 1024 or s_stride < cols or s_stride >= 2048 or s_base+(rows-1)*s_stride+cols > 1024:
        raise ValueError('S extent')
    # W0: op only; C replaces tag. No unchecked truncation or instance alias.
    return [mode, ext_base, s_base*16 << 12, cols*16,
            rows | (s_stride*16 << 16), ext_stride, 0, 0]
