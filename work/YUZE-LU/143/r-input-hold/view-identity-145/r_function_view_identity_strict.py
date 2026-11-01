"""Bind independent actual exports without accepting any graph/proof difference."""
import copy
import hashlib
import json
from pathlib import Path


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024**2),b''):digest.update(chunk)
    return digest.hexdigest()


def identity(original,selected,expected_original_sha):
    assert sha(original)==expected_original_sha
    left=json.loads(original.read_text());right=json.loads(selected.read_text())
    assert left['passed'] and right['passed']
    for proof in (left,right):
        path=Path(proof['full_view'])
        assert path.name=='physical-functional.v'
        assert sha(path)==proof['full_view_sha256']
    a=copy.deepcopy(left);b=copy.deepcopy(right)
    a.pop('full_view');b.pop('full_view')
    assert a==b,'Independent exports differ beyond the output pathname'
    return dict(passed=True,original_proof_sha256=sha(original),selected_proof_sha256=sha(selected),
                physical_view_sha256=left['full_view_sha256'],
                original_view=left['full_view'],selected_view=right['full_view'],
                equal_all_fields_except_output_path=True,
                scope='Both actual exports rehashed; entire proofs exactly equal except full_view pathname. No source, graph, projection or connectivity difference accepted.')
