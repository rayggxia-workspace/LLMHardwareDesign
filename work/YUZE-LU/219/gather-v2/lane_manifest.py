"""Export the client members referenced by the sealed v45 data contract."""
import sys
from pathlib import Path

DIRECTION = {
    'req_valid': ('INPUT', 1), 'req_ready': ('OUTPUT', 1),
    'req_address': ('INPUT', 64), 'req_tag': ('INPUT', 32),
    'req_channel': ('INPUT', 1), 'req_record_beats': ('INPUT', 5),
    'rsp_valid': ('OUTPUT', 1), 'rsp_ready': ('INPUT', 1),
    'rsp_tag': ('OUTPUT', 32), 'rsp_data': ('OUTPUT', 512),
    'close_valid': ('INPUT', 1), 'close_ready': ('OUTPUT', 1),
    'close_tag_base': ('INPUT', 32),
}

def main():
    client = int(sys.argv[1])
    if client not in range(3, 9):
        raise ValueError('client overlaps an assigned DMA family')
    with Path(sys.argv[2]).open('w') as out:
        for signal, (direction, width) in DIRECTION.items():
            for bit in range(width):
                print('gather_dma', f'c_{signal}[{client*width+bit}]', direction,
                      sep='\t', file=out)

if __name__ == '__main__':
    main()
