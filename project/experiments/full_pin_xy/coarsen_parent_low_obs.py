"""Conservatively aggregate low-layer abstract OBS, never real metal.

No interface/PDN pin may use an aggregated layer. The entire original OBS
envelope becomes forbidden to the parent. This adds forbidden space; it does
not open a hole or alter leaf wires, allowed layer sets or fabrication rules.
The same policy is required on both pin strategies for a fair comparison.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,re

def coarsen(source,dest,requested=('metal1','metal2','metal3','metal4')):
    source,dest=Path(source),Path(dest);assert not dest.exists()
    pin=None;use=None;obs=False;layer=None;bounds={};counts=Counter();pinlayers=set();pins={};current=[]
    for line in source.open():
        p=line.split()
        if not p:continue
        if p[0]=='PIN':pin=p[1];current=[]
        elif pin is not None:
            if p==['END',pin]:pins[pin]=current;pin=None
            else:
                current.append(' '.join(p))
                if p[0]=='LAYER':pinlayers.add(p[1])
        if p==['OBS']:obs=True
        elif obs and p[0]=='LAYER':layer=p[1]
        elif obs and p[0]=='RECT':
            counts[layer]+=1
            if layer in requested:
                assert len(p)==6
                z=[round(float(x)*2000) for x in p[1:5]]
                assert all(abs(float(v)*2000-i)<1e-5 for v,i in zip(p[1:5],z))
                if layer not in bounds:bounds[layer]=z
                else:
                    b=bounds[layer];bounds[layer]=[min(b[0],z[0]),min(b[1],z[1]),max(b[2],z[2]),max(b[3],z[3])]
        elif obs and p[0]=='POLYGON' and layer in requested:raise RuntimeError('Unsupported original polygon; never silently omit it')
        elif obs and p==['END']:obs=False
    selected=set(bounds)-pinlayers
    assert selected,'No low layer without a real signal/PG pin can be conservatively aggregated'
    before=hashlib.sha256();after=hashlib.sha256();obs=False;layer=None;emitted=set();written=Counter()
    with dest.open('x') as f:
        for line in source.open():
            p=line.split()
            if p==['OBS']:obs=True
            elif obs and p and p[0]=='LAYER':layer=p[1]
            elif obs and p==['END']:obs=False
            if obs and p and p[0]=='RECT' and layer in selected:
                if layer not in emitted:
                    z=bounds[layer];f.write('    RECT '+' '.join(format(x/2000.,'.4f') for x in z)+' ;\n');emitted.add(layer);written[layer]+=1
                continue
            before.update(line.encode());after.update(line.encode());f.write(line)
    assert before.hexdigest()==after.hexdigest() and emitted==selected
    # Re-read outside the selected RECT records, and all original pin lines.
    digest=hashlib.sha256();newpins={};pin=None;current=[];obs=False;layer=None
    for line in dest.open():
        p=line.split()
        if p and p[0]=='PIN':pin=p[1];current=[]
        elif pin is not None:
            if p==['END',pin]:newpins[pin]=current;pin=None
            else:current.append(' '.join(p))
        if p==['OBS']:obs=True
        elif obs and p and p[0]=='LAYER':layer=p[1]
        elif obs and p==['END']:obs=False
        if not (obs and p and p[0]=='RECT' and layer in selected):digest.update(line.encode())
    assert digest.hexdigest()==before.hexdigest() and newpins==pins
    return {'scope':'CONSERVATIVE_PARENT_ABSTRACTION_ONLY_NOT_ACTUAL_METAL_OR_PHYSICAL_ACCESS_PASS','aggregated_layers':sorted(selected),'not_aggregated_layers_with_any_actual_signal_or_PG_pin':sorted(set(requested)&pinlayers),'original_low_OBS_counts':{l:counts[l] for l in sorted(selected)},'new_low_OBS_counts':{l:1 for l in sorted(selected)},'original_OBS_envelope_DBU':{l:bounds[l] for l in sorted(selected)},'all_original_OBS_on_aggregated_layers_contained':True,'all_pin_including_PG_SIZE_and_other_OBS_text_unchanged':True,'outside_selected_RECT_content_SHA256':before.hexdigest(),'original_allowed_layer_set_and_technology_rules_unchanged':True,'parent_routes_on_selected_layers_over_envelope_are_more_restricted':True,'same_abstraction_policy_required_for_Aopt_and_C':True,'full_qualification':False}
