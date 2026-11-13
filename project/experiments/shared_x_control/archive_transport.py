"""Byte-exact <=1MiB archive transport; preserves every original archive byte.

open_archive(path) also resolves path+'.manifest.json' when the old single
blob is absent. No vectors, sources, logs or CSV are removed/recompressed.
"""
import argparse
from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
import tarfile

CHUNK_BYTES = 1024 * 1024


def split(path, replace=False):
    path = Path(path)
    parent = path.parent
    directory = parent / (path.name + '.parts')
    directory.mkdir(exist_ok=True)
    digest = hashlib.sha256()
    parts = []
    with path.open('rb') as source:
        while data := source.read(CHUNK_BYTES):
            target = directory / f'{len(parts):04d}.bin'
            if target.exists():
                assert target.read_bytes() == data, f'conflicting existing part: {target}'
            else:
                target.write_bytes(data)
            digest.update(data)
            parts.append(dict(path=target.relative_to(parent).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    manifest = dict(schema='byte-exact-split-archive/1', archive_name=path.name,
                    archive_bytes=path.stat().st_size, archive_sha256=digest.hexdigest(),
                    maximum_part_bytes=CHUNK_BYTES, parts=parts)
    manifest_path = Path(str(path) + '.manifest.json')
    encoded = (json.dumps(manifest, indent=2) + '\n').encode()
    if manifest_path.exists():
        assert manifest_path.read_bytes() == encoded, f'conflicting existing manifest: {manifest_path}'
    else:
        manifest_path.write_bytes(encoded)
    # Re-read every written byte and verify the original archive hash before
    # replacing its transport file. Only this explicitly named file is removed.
    with SplitArchive(manifest_path, verify=True) as transport:
        assert transport.total_bytes == manifest['archive_bytes']
    if replace:
        path.unlink()
    return manifest_path, manifest


class SplitArchive(io.RawIOBase):
    def __init__(self, manifest_path, verify=True):
        super().__init__()
        self.manifest_path = Path(manifest_path)
        self.manifest = json.loads(self.manifest_path.read_text())
        assert self.manifest['schema'] == 'byte-exact-split-archive/1'
        self.parts = self.manifest['parts']
        self.total_bytes = self.manifest['archive_bytes']
        self.position = 0
        self.active_index = None
        self.active_file = None
        self.starts = []
        offset = 0
        digest = hashlib.sha256()
        for part in self.parts:
            assert 0 < part['bytes'] <= CHUNK_BYTES
            self.starts.append(offset)
            offset += part['bytes']
            if verify:
                data = (self.manifest_path.parent / part['path']).read_bytes()
                assert len(data) == part['bytes'] and hashlib.sha256(data).hexdigest() == part['sha256']
                digest.update(data)
        assert offset == self.total_bytes
        assert all(part['bytes'] == CHUNK_BYTES for part in self.parts[:-1])
        if verify:
            assert digest.hexdigest() == self.manifest['archive_sha256']

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        position = offset if whence == io.SEEK_SET else (self.position if whence == io.SEEK_CUR else self.total_bytes) + offset
        if position < 0:
            raise ValueError('negative archive position')
        self.position = position
        return position

    def readinto(self, buffer):
        view = memoryview(buffer)
        count = min(len(view), max(0, self.total_bytes - self.position))
        written = 0
        while written < count:
            index = min(self.position // CHUNK_BYTES, len(self.parts) - 1)
            if self.active_index != index:
                if self.active_file:
                    self.active_file.close()
                self.active_file = (self.manifest_path.parent / self.parts[index]['path']).open('rb')
                self.active_index = index
            within = self.position - self.starts[index]
            take = min(count - written, self.parts[index]['bytes'] - within)
            self.active_file.seek(within)
            data = self.active_file.read(take)
            if len(data) != take:
                raise OSError('truncated archive part')
            view[written:written + take] = data
            self.position += take
            written += take
        return written

    def close(self):
        if self.active_file:
            self.active_file.close()
        super().close()


@contextmanager
def open_archive(path, verify=True):
    path = Path(path)
    if path.is_file():
        with tarfile.open(path, 'r:gz') as archive:
            yield archive
    else:
        with io.BufferedReader(SplitArchive(str(path) + '.manifest.json', verify=verify)) as stream:
            with tarfile.open(fileobj=stream, mode='r:gz') as archive:
                yield archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    path, manifest = split(args.source, args.replace)
    print(json.dumps(dict(manifest=str(path), archive_sha256=manifest['archive_sha256'], parts=len(manifest['parts']))))


if __name__ == '__main__':
    main()
