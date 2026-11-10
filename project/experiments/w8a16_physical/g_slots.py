"""Two advisory I/O slots, restricted to this agent's new issue250 roots."""
from contextlib import contextmanager
import fcntl
from pathlib import Path
import re
import time


@contextmanager
def slot(base):
    base=Path(base).resolve()
    assert re.fullmatch(r"/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-\d{8}-\d{2}",str(base))
    selected=None
    while selected is None:
        for number in range(2):
            stream=(base/("yzl-g250-io-%d.lock"%number)).open("a")
            try:
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                stream.close()
                continue
            selected=stream
            break
        if selected is None:
            time.sleep(.2)
    try:
        yield
    finally:
        fcntl.flock(selected,fcntl.LOCK_UN)
        selected.close()
