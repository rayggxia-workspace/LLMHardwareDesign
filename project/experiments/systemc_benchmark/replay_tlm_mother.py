"""Issue native mother CALL and WAIT operations to a transaction scheduler."""

from struct import unpack


def execute(instructions, *, issue, wait, max_steps, entry_pc=0, instruction=None):
    """Run a page. Issue admits a CALL and returns its completion handle.

    Wait advances the scheduler until the specified handles have completed.
    Neither callback may manufacture a completion from the instruction itself.
    """
    registers = [0] * 8
    live = {}
    pc = entry_pc
    for _ in range(max_steps):
        if not 0 <= pc < len(instructions):
            raise ValueError("mother PC outside image")
        row = instructions[pc]
        imm, c, b, a, opcode = unpack("<IBBBB", bytes.fromhex(row["encoding"]))
        if (row["pc"], row["opcode"]) != (pc, opcode):
            raise ValueError("inconsistent mother instruction record")
        if instruction is not None:
            instruction(opcode)
        if opcode == 0x10:
            if a >= 9 or b >= 16 or c or imm or b in live or any(target == a for target, _ in live.values()):
                raise ValueError("invalid or overlapping mother CALL")
            live[b] = (a, issue(a, b, tuple(registers)))
        elif opcode == 0x11:
            slots = [slot for slot in range(16) if imm & (1 << slot)]
            if a or b or c or imm >> 16 or not slots or any(slot not in live for slot in slots):
                raise ValueError("WAIT references an unallocated completion")
            wait(tuple(live[slot][1] for slot in slots))
            for slot in slots:
                del live[slot]
        elif opcode == 0x13:
            if a >= 8 or b or c:
                raise ValueError("invalid MOVI")
            registers[a] = imm
        elif opcode == 0x16:
            if a not in (0, 2, 4, 6) or b or c:
                raise ValueError("invalid ADDI64")
            pointer = registers[a] + (registers[a+1] << 32) + imm
            if pointer >= 1 << 64:
                raise ValueError("descriptor pointer overflow")
            registers[a], registers[a+1] = pointer & 0xffffffff, pointer >> 32
        elif opcode == 0x17:
            if not 2 <= a < 8 or b or c or not entry_pc <= imm < pc or not 0 < registers[a] <= 65535:
                raise ValueError("invalid LOOP")
            registers[a] -= 1
            if registers[a]:
                pc = imm
                continue
        elif opcode == 0x1f:
            if a or b or c or imm or live:
                raise ValueError("END with malformed fields or outstanding calls")
            return
        else:
            raise ValueError(f"unsupported mother opcode {opcode:#x}")
        pc += 1
    raise ValueError("mother program exceeded its step budget")
