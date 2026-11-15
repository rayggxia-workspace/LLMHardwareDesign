"""Encode a selected W8 projection as native P stream descriptors."""

import json
import zlib

from ffn_scope_emit import DESC_BYTES, SCHEMA, require
from pack_native_projections import HEAD16, RECORD_SIZES, projection_size


def emit_projection(weight, binding, *, first_column=None):
    """Return descriptor bytes and their output-consumption contract.

    The stream service produces unbiased S32. The selected binding must
    separately implement checkpoint bias if one is required. A reused output
    window stays owned until the previous consumer acknowledges it. A selected
    first column emits only its descriptor while preserving global identity.
    """
    n, k = weight["shape"]
    base = weight["base"]
    format_name = weight["format"]
    require(weight["bytes"] == projection_size(n, k, base, format_name), "incompatible weight image")
    record_bytes = RECORD_SIZES[format_name]
    bias = weight.get("bias")
    require(not weight.get("bias_tensor") or (bias and binding.get("bias_service")),
            "projection requires a selected bias service")
    require(not binding.get("bias_service") or bias, "bias service has no packed operand")

    topology, rf_base, version, sequence = (
        binding[key] for key in ("topology", "rf_object_base", "output_version", "record_sequence_base")
    )
    input_key = binding["input_key"]
    require(all(type(value) is int and 0 <= value < 2**32
                for value in (topology, rf_base, version, sequence, *input_key))
            and len(input_key) == 4 and topology != 0 and input_key[0] != 0,
            "invalid projection identity")
    require(rf_base + n // 8 <= 2**32, "projection RF object range wraps")
    require(sequence + n // 8 * (k // 128) <= 2**32, "projection record sequence wraps")

    input_s, output_s = binding["input_s_word"], binding["output_s_word"]
    output_words = min(n // 8, 16) * 2
    require(type(input_s) is int and 0 <= input_s <= 1024 - 16
            and type(output_s) is int and 0 <= output_s <= 1024 - output_words
            and (input_s + 16 <= output_s or output_s + output_words <= input_s),
            "projection SRAM windows overlap or exceed the stream aperture")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fields = {field["name"]: (field["offset"], field["bytes"]) for field in schema["fields"]}
    packed_key = int.from_bytes(b"".join(value.to_bytes(4, "big") for value in input_key), "big")
    image = bytearray()
    tiles = []
    if first_column is not None and (
            type(first_column) is not int or first_column % 128 or not 0 <= first_column < n):
        raise ValueError("selected projection column is outside the registered tile grid")
    columns = range(0, n, 128) if first_column is None else (first_column,)
    for first in columns:
        groups = min(16, (n - first) // 8)
        record_count = groups * (k // 128)
        record_offset = (first // 8) * (k // 128)
        row = bytearray(DESC_BYTES)
        values = dict(
            schema_abi=int(schema["schema_abi"], 16), provider_abi=int(schema["provider_abi"], 16),
            length=DESC_BYTES, service=2, topology=topology, input_key=packed_key,
            rf_object_base0=rf_base, output_version=version, record_sequence_base=sequence + record_offset,
            weight_base0=base, columns=n, first_column=first, column_stride=8,
            groups=groups, full_k=k, k_end=k, ways=1, input_s_base=input_s,
            output_s_base0=output_s, flags=int(format_name == HEAD16),
        )
        for name, value in values.items():
            offset, size = fields[name]
            row[offset:offset + size] = value.to_bytes(size, "little")
        row[124:128] = zlib.crc32(row[:124]).to_bytes(4, "little")
        tiles.append(dict(
            descriptor_offset=len(image), first_column=first, columns=groups * 8,
            weight_start=base + record_offset * record_bytes,
            records=record_count, record_bytes=record_bytes, record_sequence=sequence + record_offset,
            output_s_word=output_s,
            output_words=groups * 2, required_completion="final_sram_write_ack",
            previous_tile_requires_consumer_ack=first != 0,
        ))
        image.extend(row)
    return bytes(image), dict(tiles=tiles, bias_service=binding.get("bias_service"))
