"""Produce one bounded 352-byte native-scope kernel, not a model program.

The typed scope service registration remains an integration gate. PM tests
check the actual image, byte CRC and instruction words without claiming that
the production LC already executes this new service.
"""
import argparse
import json
import struct
import zlib
from pathlib import Path


def kernel():
    b = bytearray(352)
    def field(bit, width, value):
        b[bit//8:(bit+width)//8] = value.to_bytes(width//8, "little")
    for bit, width, value in [
        (0,64,0x313041534943424c),(64,16,2),(80,8,1),(88,8,8),
        (96,32,352),(160,32,3),(192,32,128),(224,16,1),(256,16,1),
        (288,32,160),(352,32,224),(416,32,3),(448,32,1),
        (480,32,25001),(512,32,25001),(544,32,0x02500002),(672,32,0x02510001),
    ]:
        field(bit,width,value)
    struct.pack_into('<QQQ',b,128,0x4100000000000000,0x4400000000000001,0x4f00000000000000)
    # One task and one existing-width execution record. This new native-op
    # value is a candidate service ID; old ABI/profile must reject the image.
    for off, bit, width, value in [
        (160,0,16,1),(160,128,32,3),(160,160,32,1),
        (160,192,32,25001),(160,224,32,25001),(160,352,32,0x02500002),
        (224,0,32,1),(224,32,16,0x0250),(224,64,32,0xffffffff),
        (224,160,48,0xffffffffffff),(224,448,32,0x02500002),
    ]:
        field(off*8+bit,width,value)
    return b


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    good=kernel();old=bytearray(good);struct.pack_into('<H',old,8,1)
    rows={}
    for name,data in [('kernel',good),('old-version',old)]:
        (args.out/(name+'.mem')).write_text(''.join(f'{int.from_bytes(data[i:i+16],"little"):032x}\n' for i in range(0,len(data),16)),encoding='ascii')
        rows[name]={'bytes':len(data),'instruction_words':3,'instruction_bytes':24,'aligned_instruction_bytes':32,'header_bytes':128,'task_bytes':64,'execution_bytes':128,'crc32':f'{zlib.crc32(data):08x}'}
    (args.out/'kernel.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
