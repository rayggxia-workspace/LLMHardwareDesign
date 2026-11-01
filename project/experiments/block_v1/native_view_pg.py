"""Supply-only, exactly reversible correction to native timing-model output.

The raw model is retained. All bytes outside the two verified ordinary supply
pin groups are unchanged, including every signal pin and timing table.
"""
import hashlib
import re
from native_cell_gate import group


def convert(text):
    assert not re.search(r'\bpg_pin\s*\(',text),'Unexpected pre-existing PG model'
    edits=[];result=text
    for name,kind in [('VDD','primary_power'),('VSS','primary_ground')]:
        body=group(text,'pin',name)
        assert re.fullmatch(r'\s*direction\s*:\s*input\s*;\s*capacitance\s*:\s*0(?:\.0+)?\s*;\s*max_transition\s*:\s*(?:\d+(?:\.\d*)?|\.\d+)\s*;\s*',body),'Supply pin has unexpected semantics'
        match=re.search(r'(?<![\w])pin\s*\(\s*"?'+name+r'"?\s*\)\s*\{',text)
        original=text[match.start():match.end()]+body+'}'
        replacement='pg_pin("'+name+'") {\n      voltage_name : "'+name+'";\n      pg_type : '+kind+';\n    }'
        assert text.count(original)==1 and result.count(original)==1
        result=result.replace(original,replacement,1)
        edits.append(dict(name=name,pg_type=kind,original=original,replacement=replacement))
    inverse=result
    for edit in reversed(edits):
        assert inverse.count(edit['replacement'])==1
        inverse=inverse.replace(edit['replacement'],edit['original'],1)
    assert inverse==text
    for edit in edits:
        assert not re.search(r'(?<![\w])pin\s*\(\s*"?'+edit['name']+r'"?\s*\)',result)
        assert group(result,'pg_pin',edit['name']).strip()
    digest=lambda value:hashlib.sha256(value.encode()).hexdigest()
    return result,dict(schema='block-v1-supply-model-correction/1',passed=True,
        original_sha256=digest(text),corrected_sha256=digest(result),edits=edits,
        exact_inverse_reconstruction=True,all_other_model_bytes_unchanged=True,
        scope='Only original zero-capacitance VDD/VSS pseudo-input groups become typed primary_power/primary_ground pg_pin; signal arcs unchanged; no boundary accuracy qualification')


def checked_timing_view(physical,source_receipt):
    """Select the received actual ODB export, never the filtered flow Verilog."""
    formal=physical['mapped_to_final_lec'];assert formal['passed']is True
    view=formal['physical_functional_view']
    assert view['passed']is True and view['schema']=='block-v1-physical-functional-view/1'
    assert view['source_antenna_count']==0
    projection=view['input_only_projection']
    assert projection['passed']is True and projection['removed_count']>0
    assert projection['allowed_master']=='ANTENNA_X1'and projection['exact_inverse_reconstruction']is True
    assert source_receipt['outputs']['physical-functional.v']==view['full_view_sha256']
    return view
