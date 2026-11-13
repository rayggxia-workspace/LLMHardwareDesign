"""Deterministic transport fixture; not a typed deployable P/U/C/F/J scope."""
import argparse
import json
import zlib
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
data=bytearray((i*17+3)%256 for i in range(124))
crc=zlib.crc32(data)
data+=crc.to_bytes(4,'little')
args.out.mkdir(parents=True,exist_ok=True)
(args.out/'descriptor.mem').write_text(''.join(f'{int.from_bytes(data[i:i+64],"little"):0128x}\n' for i in range(0,128,64)),encoding='ascii')
(args.out/'descriptor.json').write_text(json.dumps({'bytes':128,'CRC_bytes':124,'CRC32_tail':f'{crc:08x}','typed_scope':False},indent=2)+'\n',encoding='utf8')
