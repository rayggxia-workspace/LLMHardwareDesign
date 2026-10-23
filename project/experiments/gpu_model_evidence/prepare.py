"""Download one official revision, verify LFS SHA256 and retain a local manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import requests


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--revision')
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--transport', choices=['huggingface','modelscope'], default='huggingface')
    a = p.parse_args()
    a.root.mkdir(parents=True, exist_ok=True)
    meta_path = a.root / 'official-metadata.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        assert meta['id'] == a.model
    else:
        url = 'https://huggingface.co/api/models/' + a.model
        if a.revision:
            url += '/revision/' + a.revision
        r = requests.get(url, params={'blobs': 'true'}, timeout=60)
        r.raise_for_status()
        meta = r.json()
        meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    revision = meta['sha']
    if a.revision:
        assert revision == a.revision
    files = {}
    names = {'config.json', 'generation_config.json', 'tokenizer.json',
             'tokenizer_config.json', 'merges.txt', 'vocab.json', 'LICENSE',
             'README.md', 'chat_template.jinja', 'model.safetensors.index.json'}
    for item in meta['siblings']:
        name = item['rfilename']
        if name not in names and not name.endswith('.safetensors'):
            continue
        dest = a.root / name
        expected = item.get('lfs', {}).get('sha256')
        url = (f'https://modelscope.cn/models/{a.model}/resolve/master/{name}'
               if a.transport=='modelscope' else f'https://huggingface.co/{a.model}/resolve/{revision}/{name}')
        if not dest.exists() and item['size'] > (64 << 20):
            from ranged import download
            download(url, dest, item['size'], expected, a.workers)
        if not dest.exists():
            part = dest.with_suffix(dest.suffix + '.partial')
            # Full retry retains the failed partial under a distinct name.
            for attempt in range(4):
                try:
                    with requests.get(url, stream=True, timeout=(30, 180)) as r:
                        r.raise_for_status()
                        with part.open('wb') as f:
                            for b in r.iter_content(8 << 20):
                                f.write(b)
                    assert part.stat().st_size == item['size'], name
                    actual = sha(part)
                    assert not expected or actual == expected, name
                    part.rename(dest)
                    break
                except Exception as exc:
                    print(name, attempt, repr(exc), flush=True)
                    if attempt == 3:
                        raise
                    time.sleep(3)
        actual = sha(dest)
        assert dest.stat().st_size == item['size']
        assert not expected or actual == expected
        if not expected:
            data=dest.read_bytes()
            blob=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
            assert blob==item['blobId'], (name,blob,item['blobId'])
        files[name] = {'bytes': dest.stat().st_size, 'sha256': actual,
                       'official_lfs_sha256': expected, 'official_blob_id': item['blobId'],
                       'transport': a.transport}
        print(name, files[name], flush=True)
        (a.root / 'model-manifest.json').write_text(json.dumps({
            'model': a.model, 'revision': revision, 'root': str(a.root.resolve()),
            'files': files, 'complete': False}, indent=2), encoding='utf-8')
    (a.root / 'model-manifest.json').write_text(json.dumps({
        'model': a.model, 'revision': revision, 'root': str(a.root.resolve()),
        'files': files, 'complete': True}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
