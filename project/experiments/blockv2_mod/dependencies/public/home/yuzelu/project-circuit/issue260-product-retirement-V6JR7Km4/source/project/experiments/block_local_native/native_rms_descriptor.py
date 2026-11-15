"""Encode a resident S32 RMS row after the selected gamma COPY commits."""

from math import isfinite
import struct
import zlib


def q16_rms_profile(epsilon):
    """Encode the graph's exact dyadic epsilon in the qualified Q16 RMS ABI."""
    if type(epsilon) is not float or not isfinite(epsilon) or not 0 < epsilon < 1:
        raise ValueError("RMS needs a positive finite graph epsilon")
    mantissa, denominator = epsilon.as_integer_ratio()
    # The input and baseline are both Q16. N receives epsilon in the
    # corresponding squared units. Preserve the tested two rounding points.
    shift = 32 - (denominator.bit_length() - 1)
    if mantissa >= 2**32 or not -128 <= shift < 128:
        raise ValueError("exact graph epsilon exceeds the native RMS encoding")
    return dict(baseline_shift=0, epsilon=mantissa, epsilon_shift=shift,
                factor_shift=13, gamma_shift=17)


def rms_provider(*, schema, provider_abi, operation, topology, site,
                 x_word, output_word, baseline_shift, epsilon, epsilon_shift, factor_shift, gamma_shift):
    if any(type(value) is not int or not 0 < value < 2**bits for value, bits in (
            (schema, 32), (provider_abi, 32), (operation, 16), (topology, 32), (epsilon, 32))):
        raise ValueError("invalid native RMS profile identity")
    if x_word not in (0, 512) or output_word not in (0, 512):
        raise ValueError("resident RMS requires the two qualified S128 half-bank windows")
    if (type(baseline_shift) is not int or not -32 <= baseline_shift < 32
            or any(type(shift) is not int or not -128 <= shift < 128
            for shift in (epsilon_shift, factor_shift, gamma_shift))):
        raise ValueError("native RMS shifts exceed the service format")

    def encode(command):
        if command["op"] != "EXEC" or len(command["read"]) != 2 or len(command["write"]) != 1:
            raise ValueError("resident RMS needs a local activation, local gamma, and local output")
        output, = command["write"]
        gamma_word = 512 - x_word
        reads = {(operand["site"], operand["address"], operand["bytes"]) for operand in command["read"]}
        if reads != {(site, 16*x_word, 8192), (site, 16*gamma_word, 8192)} or (
                output["site"], output["address"], output["bytes"]) != (site, 16*output_word, 8192):
            raise ValueError("RMS operands do not match the registered SRAM windows")
        row = bytearray(128)
        struct.pack_into("<IHHIIHHHHIbbbb", row, 0, schema, 128, operation, provider_abi, topology,
                         x_word, gamma_word, output_word, 0, epsilon,
                         baseline_shift, epsilon_shift, factor_shift, gamma_shift)
        struct.pack_into("<I", row, 124, zlib.crc32(row[:124]))
        return bytes(row)

    return "service_done", encode
