"""Hash only this newly created task's immutable artifacts on the compute node."""
import hashlib
from pathlib import Path

excluded = {'source', 'cache', 'tmp', 'xdg-cache'}
with Path('output-files.sha256').open('w') as out:
    for path in sorted(Path('.').rglob('*')):
        if not path.is_file() or path.is_symlink() or path.parts[0] in excluded:
            continue
        if path.as_posix() in ('output-files.sha256', 'step.log', 'output-hash-exit-code.txt'):
            continue
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(8*1024*1024), b''):h.update(chunk)
        out.write(h.hexdigest() + '  ' + path.as_posix() + '\n')
