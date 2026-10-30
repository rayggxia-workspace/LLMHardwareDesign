"""Issue130 copy/hash slots; cannot create locks in another task directory."""
from contextlib import contextmanager
import fcntl
import hashlib
from pathlib import Path
import time

def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):digest.update(data)
    return digest.hexdigest()

@contextmanager
def slot(base):
    base=Path(base).resolve()
    allowed=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees')
    assert allowed in base.parents and any(p.startswith('issue130-') for p in base.parts)
    selected=None
    while selected is None:
        for number in range(2):
            stream=(base/('issue130-io-%d.lock'%number)).open('a')
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:stream.close();continue
            selected=stream;break
        if selected is None:time.sleep(.2)
    try:yield
    finally:fcntl.flock(selected,fcntl.LOCK_UN);selected.close()
