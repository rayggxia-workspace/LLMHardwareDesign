"""Generate typed scope and PM stimuli; no host parameter side-load at runtime."""
import argparse
import json
import importlib.util
import struct
import zlib
from pathlib import Path
from make_lc_kernel import kernel


def scope(service=1, head=False):
    b = bytearray(128)
    for offset, fmt, value in [
        (0, 'I', 0x02505001), (4, 'H', 128), (6, 'H', service),
        (8, 'I', 0x02504d02), (12, 'I', 25001),
        (32, 'I', 4096), (36, 'I', 8192), (40, 'I', 1), (44, 'I', 100),
        (48, 'Q', 0x100000), (56, 'Q', 0x200000),
        (64, 'I', 32), (68, 'I', 0), (72, 'H', 8), (74, 'B', 2), (75, 'B', 0),
        (76, 'H', 256), (78, 'H', 0), (80, 'H', 256), (82, 'B', 2), (83, 'B', int(head)),
        (84, 'H', 0), (86, 'H', 256), (88, 'H', 320), (90, 'H', 512), (92, 'H', 768),
    ]:
        struct.pack_into('<' + fmt, b, offset, value)
    struct.pack_into('<IIII', b, 16, 7, 8, 9, 1)
    struct.pack_into('<I', b, 124, zlib.crc32(b[:124]))
    return b


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True); p.add_argument('--mc-assembler', type=Path); a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.mc_assembler:
        spec = importlib.util.spec_from_file_location('mc_image', a.mc_assembler)
        mc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mc)
        args = [0x4000, 0, 0x00010080, 0x02510001, 25001, 0x02500002, 0, 0]
        program = [('MOVI', r, 0, 0, v) for r, v in enumerate(args)] + [mc.call(0), mc.wait(1), mc.END]
        data = bytearray(mc.image(program)); struct.pack_into('<I', data, 64, 25001)
        assert len(data) == 224
        (a.out/'mother.mem').write_text(''.join(f'{int.from_bytes(data[i:i+16],"little"):032x}\n' for i in range(0,len(data),16)), encoding='ascii')
    k = kernel()
    (a.out/'kernel.mem').write_text(''.join(f'{int.from_bytes(k[i:i+16],"little"):032x}\n' for i in range(0,len(k),16)), encoding='ascii')
    # Bad table is intentionally CRC-certified by boot, then rejected by the
    # interpreter's real metadata reads. Boot CRC is not semantic validation.
    bad = bytearray(k); bad[228] ^= 1
    (a.out/'bad-table.mem').write_text(''.join(f'{int.from_bytes(bad[i:i+16],"little"):032x}\n' for i in range(0,len(bad),16)), encoding='ascii')
    scopes = [scope(), scope(service=2), scope(), scope(head=True)]
    scopes[2][0] ^= 1
    (a.out/'scopes.mem').write_text(''.join(f'{int.from_bytes(b[i:i+64],"little"):0128x}\n' for b in scopes for i in (0,64)), encoding='ascii')
    (a.out/'fixture.json').write_text(json.dumps({'kernel_crc':f'{zlib.crc32(k):08x}', 'bad_table_crc':f'{zlib.crc32(bad):08x}', 'record_count':8, 'input_key_fields':[7,8,9,1], 'not_native_M_numeric':True},indent=2)+'\n',encoding='utf8')


if __name__ == '__main__': main()
