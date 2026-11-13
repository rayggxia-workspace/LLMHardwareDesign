"""Actual, measured power-of-two quantization; never just a dtype annotation.

Calibration arrays are explicit inputs. This primitive reports reconstruction
error and clipping; it does not claim full-model accuracy from weight error.
"""
import hashlib
import math


def quantize(values, *, bits=16, exponent=None, lanes=2):
    import numpy as np
    from numeric import Format
    x = np.asarray(values, dtype=np.float64)
    if x.size == 0 or not np.isfinite(x).all():
        raise ValueError('quantization requires finite, nonempty calibration data')
    if bits not in (8, 16, 32):
        raise ValueError('unsupported quantization width')
    maximum = float(np.abs(x).max())
    # Use the smaller signed magnitude limit for symmetric calibration.
    if exponent is None:
        exponent = math.ceil(math.log2(maximum / ((1 << (bits-1))-1))) if maximum else 0
    Format(bits, exponent, lanes)
    step = math.ldexp(1.0, exponent)
    scaled = np.rint(x / step)  # IEEE ties-to-even, matching native RNE.
    low, high = -(1 << (bits-1)), (1 << (bits-1))-1
    clipped = int(np.count_nonzero((scaled < low) | (scaled > high)))
    raw = np.clip(scaled, low, high).astype({8:'<i1',16:'<i2',32:'<i4'}[bits])
    error = raw.astype(np.float64) * step - x
    return raw, {'format': {'bits':bits,'exponent':exponent,'lanes':lanes},
        'elements':int(x.size), 'calibration_max_abs':maximum, 'clipped_elements':clipped,
        'max_abs_error':float(np.abs(error).max()), 'rms_error':float(np.sqrt(np.mean(error**2))),
        'source_float64_sha256':hashlib.sha256(x.astype('<f8').tobytes()).hexdigest(),
        'quantized_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),
        'rounding':'nearest ties to even', 'saturation':'signed destination range',
        'scope':'actual tensor quantization; full-model accuracy requires separate execution'}
