"""Bind a Gather mother CALL image to the supplied native fabric topology."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import pack_into, unpack_from


def bind(mother, expected_sha, fabric_topology, local_topology):
    if (sha256(mother).hexdigest() != expected_sha or len(mother) < 144 or
            mother[:8] != b'LBCISA01' or unpack_from('<I', mother, 12)[0] != len(mother) or
            unpack_from('<II', mother, 64) != (local_topology, 0x02500002)):
        raise ValueError('Gather mother image or legacy topology differs')
    if not 0 < fabric_topology < (1 << 32):
        raise ValueError('invalid native fabric topology')
    image = bytearray(mother)
    pack_into('<I', image, 64, fabric_topology)
    return bytes(image)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'link', 'base', 'local', 'output'):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    link = json.loads(args.link.read_bytes())
    base = json.loads(args.base.read_bytes())
    local = args.local.read_bytes()
    if sha256(local).hexdigest() not in {row['local_pm_sha256'] for row in link['pages']}:
        raise ValueError('unregistered Gather local image')
    legacy_topology, = unpack_from('<I', local, 64)
    # Both formats use a topology field at byte 64.
    native_topology = base['native_service_routes']['topology_id']
    data = bind(args.source.read_bytes(), link['mother_pm_sha256'], native_topology, legacy_topology)
    args.output.mkdir()
    (args.output/'mother.pm').write_bytes(data)
    (args.output/'mother.hex').write_text(''.join(data[i:i+16][::-1].hex()+'\n'
                                                 for i in range(0, len(data), 16)))
    print(json.dumps(dict(native_topology=native_topology, local_topology=legacy_topology,
                          mother_sha256=sha256(data).hexdigest()), sort_keys=True))


if __name__ == '__main__':
    main()
