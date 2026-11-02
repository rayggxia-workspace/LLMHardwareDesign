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


def identity(original,selected,expected_original_sha,liberty=None):
    assert sha(original)==expected_original_sha
    left=json.loads(original.read_text());right=json.loads(selected.read_text())
    assert left['passed'] and right['passed']
    assert left['full_view_sha256']==right['full_view_sha256'],'Actual physical netlist bytes differ'
    for proof in (left,right):
        path=Path(proof['full_view'])
        assert path.name=='physical-functional.v'
        assert sha(path)==proof['full_view_sha256']
    a=copy.deepcopy(left);b=copy.deepcopy(right)
    a.pop('full_view');b.pop('full_view')
    normalized=0
    if a!=b:
        # Yosys embeds the input pathname in attributes.src, including inside
        # the exact graph digests. Never discard those digests: rebuild the
        # complete real projection on the actual graph with only that exact
        # source filename rebound, and require the original proof verbatim.
        assert liberty is not None,'Metadata rebind requires the actual Liberty and parsed graph'
        from native_logic_projection import project
        from structural_view import digest
        graph_path=Path(right['full_view']).with_name('physical-functional.json')
        graph=json.loads(graph_path.read_text())
        assert digest(graph)==right['input_only_projection']['original_graph_sha256']
        projected,rebuilt=project(graph,Path(liberty).read_text())
        assert rebuilt==right['input_only_projection']
        del projected,rebuilt
        old=right['full_view']+':'
        new=left['full_view']+':'
        def rebind(value):
            nonlocal normalized
            if isinstance(value,dict):
                attributes=value.get('attributes')
                if isinstance(attributes,dict):
                    src=attributes.get('src')
                    if isinstance(src,str) and src.startswith(old):
                        attributes['src']=new+src[len(old):];normalized+=1
                for child in value.values():rebind(child)
            elif isinstance(value,list):
                for child in value:rebind(child)
        rebind(graph)
        assert normalized>0
        projected,rebuilt=project(graph,Path(liberty).read_text())
        assert rebuilt==left['input_only_projection'],'Source-filename rebind does not reconstruct the original exact graph proof'
        del projected,graph
        b['input_only_projection']=rebuilt
    assert a==b,'Independent exports differ beyond the proven source/output pathname rebind'
    return dict(passed=True,original_proof_sha256=sha(original),selected_proof_sha256=sha(selected),
                physical_view_sha256=left['full_view_sha256'],
                original_view=left['full_view'],selected_view=right['full_view'],
                normalized_src_attributes=normalized,
                exact_original_projection_reconstructed=True,
                equal_all_fields_after_proven_path_rebind=True,
                scope='Actual netlist bytes identical. Exact real parsed-graph/project proofs rechecked when src paths differ; only the full input filename in attributes.src is rebound, reconstructing the original entire graph/projection proof. All other proof fields equal.')
