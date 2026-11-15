"""Encode bound descriptor calls for the native MC v3 scope ABI."""

from bisect import bisect_right
from collections import defaultdict
import struct

PM_INSTRUCTIONS = (16384 - 128) // 8
MAX_PATTERN_GROUPS = (PM_INSTRUCTIONS - 10) // 3


class MotherProgramCapacityError(ValueError):
    pass


def repeated_groups(groups):
    """Find repeated target patterns without assuming a model or layer shape."""
    locations = defaultdict(list)
    for index, targets in enumerate(groups):
        locations[targets].append(index)
    cursor = 0
    while cursor < len(groups):
        uniform = cursor + 1
        while uniform < len(groups) and groups[uniform] == groups[cursor]:
            uniform += 1
        best_period, best_count = 1, min(uniform - cursor, 65535)
        best_saved = (best_count - 1) * (2 * len(groups[cursor]) + 1)
        positions = locations[groups[cursor]]
        start = bisect_right(positions, uniform - 1)
        for occurrence in range(start, len(positions)):
            position = positions[occurrence]
            period = position - cursor
            if period > min((len(groups) - cursor) // 2, MAX_PATTERN_GROUPS):
                break
            pattern = groups[cursor:position]
            if pattern != groups[position:position + period]:
                continue
            count = 2
            while count < 65535:
                next_begin = cursor + count * period
                if groups[next_begin:next_begin + period] != pattern:
                    break
                count += 1
            saved = (count - 1) * sum(2 * len(targets) + 1 for targets in pattern)
            if saved > best_saved:
                best_period, best_count, best_saved = period, count, saved
        yield groups[cursor:cursor + best_period], best_count
        cursor += best_period * best_count


def emit_mother(groups, base, topology, assembler, expand):
    """Emit one ordered stream of groups with a terminal ACK fence per group.

    A group is the ordered tuple of real LC target IDs associated with the
    next descriptor records in DDR. The caller supplies checked provider
    bindings and places the actual records in this order.
    """
    if type(base) is not int or not 0 <= base < 2**48 or base % 128:
        raise ValueError("native descriptor arena is not 128-byte aligned")
    if type(topology) is not int or not 0 < topology < 2**32:
        raise ValueError("invalid native topology")
    groups = [tuple(group) for group in groups]
    for group in groups:
        if (not group or any(type(target) is not int or not 0 <= target < 9 for target in group)
                or len(set(group)) != len(group)):
            raise ValueError("invalid or conflicting local controller targets")
    if not groups or base + 128 * sum(map(len, groups)) >= 2**48:
        raise ValueError("native descriptor arena is empty or exceeds 48 bits")
    registers = [base & 0xFFFFFFFF, base >> 32, 0x00010080,
                 0x02510001, topology, 0x02500002, 0]
    program = [("MOVI", index, 0, 0, value) for index, value in enumerate(registers)]
    expanded_instructions = len(program) + 1
    for pattern, count in repeated_groups(groups):
        # Use only R7 as the loop counter. The other registers carry the
        # live descriptor pointer and LC call metadata.
        program.append(("MOVI", 7, 0, 0, count))
        loop_start = len(program)
        for targets in pattern:
            for target in targets:
                program.extend((assembler.call(target), ("ADDI64", 0, 0, 0, 128)))
            program.append(assembler.wait(sum(1 << target for target in targets)))
        program.append(("LOOP", 7, 0, 0, loop_start))
        if len(program) >= PM_INSTRUCTIONS:  # Leave one word for END.
            raise MotherProgramCapacityError("native mother image exceeds the 16 KiB program store")
        expanded_instructions += 1 + count * (len(program) - loop_start)
    program.append(assembler.END)
    actual, steps = expand(program, expanded_instructions)
    expected_targets = (target for group in groups for target in group)
    if steps != expanded_instructions or len(actual) != sum(map(len, groups)):
        raise ValueError("independent MC expansion disagrees with native calls")
    for index, (call, target) in enumerate(zip(actual, expected_targets, strict=True)):
        if call != dict(target=target, token=target, reference=base+128*index):
            raise ValueError(f"independent MC expansion disagrees at native call {index}")
    mother = bytearray(assembler.image(program, max_steps=steps + 1))
    struct.pack_into("<I", mother, 64, topology)
    return bytes(mother), actual, steps, len(program)


def emit_mother_pages(groups, base, topology, assembler, expand):
    """Cut an oversized phase only after full LC completion waves."""
    groups = tuple(tuple(group) for group in groups)

    def encode(start, end, address):
        image, calls, steps, _ = emit_mother(groups[start:end], address, topology, assembler, expand)
        return dict(image=image, descriptor_base=address, call_count=len(calls),
                    wave_count=end-start, dynamic_instruction_count=steps)

    try:
        return [encode(0, len(groups), base)]
    except MotherProgramCapacityError:
        pass

    pages, start, address, words = [], 0, base, 8  # Seven initial registers plus END.
    for end, group in enumerate(groups):
        # Worst case per wave is MOVI, CALL/ADDI64 per target, WAIT and LOOP.
        needed = 3 + 2 * len(group)
        if words + needed > PM_INSTRUCTIONS:
            page = encode(start, end, address)
            pages.append(page)
            address += 128 * page["call_count"]
            start, words = end, 8
        words += needed
    pages.append(encode(start, len(groups), address))
    return pages
