"""Original main native electrical/rule anchors; never changed to fit a result."""
import hashlib
from pathlib import Path

PLATFORM = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
LIB = PLATFORM/"lib/NangateOpenCellLibrary_typical.lib"
DECK = PLATFORM/"drc/FreePDK45.lydrc"
LIB_SHA = "8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1"
DECK_SHA = "4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147"


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def check():
    assert sha(LIB) == LIB_SHA, "original Nangate45 Liberty differs"
    assert sha(DECK) == DECK_SHA, "original full FreePDK45 rule deck differs"
    return dict(liberty_sha256=LIB_SHA, full_deck_sha256=DECK_SHA,
        source="Main accepted M mapping receipt and main release-six/M/evidence/drc/five-macro-drc.json")
