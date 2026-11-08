"""Little-endian scene interchange; coordinates in microns, C in fF."""
import struct


class SceneWriter:
    def __init__(self, path, names, grounded=(), eps=3.9):
        self.path = path
        self.file = path.open('xb')
        self.file.write(struct.pack('<8sIQd', b'NATIVE22', len(names), 0, eps))
        self.count = 0
        for index, name in enumerate(names):
            value = name.encode('utf-8')
            self.file.write(struct.pack('<I', len(value)))
            self.file.write(value)
            self.file.write(struct.pack('<B', index in grounded))

    def add(self, net, owner, box):
        assert len(box) == 6 and all(box[i] < box[i+3] for i in range(3))
        self.file.write(struct.pack('<ii6d', net, owner, *box))
        self.count += 1

    def close(self):
        self.file.seek(12)
        self.file.write(struct.pack('<Q', self.count))
        self.file.close()


def write(path, names, entries, grounded=()):
    scene = SceneWriter(path, names, grounded)
    for row in entries:
        scene.add(*row)
    scene.close()
    return scene.count
