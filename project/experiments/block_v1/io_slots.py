"""Two shared heavy copy/hash slots inside this issue's own server directory."""
from contextlib import contextmanager
import fcntl
from pathlib import Path
import time


@contextmanager
def slot(base):
    base=Path(base).resolve()
    assert base==Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')
    selected=None
    while selected is None:
        for number in range(2):
            stream=(base/('yzl-bv1-io-%d.lock'%number)).open('a')
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:stream.close();continue
            selected=stream;break
        if selected is None:time.sleep(.2)
    try:yield
    finally:
        fcntl.flock(selected,fcntl.LOCK_UN);selected.close()


def file_sha(path):
    import hashlib
    digest=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()
