"""Audit modern OpenRCX table coverage without changing fitted coefficients.

Pinned OpenROAD 6ea4ca: extmeasure_res.cpp queries RESOVER context 0;
extBench.cpp::linesDiagUnderBench generates only separations 1..4. Both
unused empty-table classes also occur in the unmodified Nangate45 model.
"""
from collections import Counter
import math
import re


def audit(text, layer_count=12):
    assert re.search(r'(?m)^LayerCount %d\s*$'%layer_count,text)
    assert re.search(r'(?m)^DIAGMODEL ON\s*$',text)
    sections={};tables={};section=None;context=None;active=None
    for line in text.splitlines():
        words=line.split()
        if not words:continue
        if words[0]=='Metal':
            assert active is None,'Unterminated distance table'
            metal=int(words[1]);assert 1<=metal<=layer_count
            if len(words)==3:
                section=(metal,words[2]);context=None
                assert section not in sections,'Duplicate section'
                sections[section]=None
            else:
                assert section and section[0]==metal
                context=tuple(words[2:])
            continue
        if words[:2]==['WIDTH','Table']:
            assert section and context is None
            widths=tuple(map(float,words[4:]));assert len(widths)==int(words[2])
            assert len(set(widths))==len(widths)and all(w>0 for w in widths)
            sections[section]=widths
        if words[:2]==['DIST','count']:
            assert section and context and active is None
            assert words[3]=='width'
            key=(section,context,float(words[4]));assert key not in tables
            assert key[2]in sections[section]
            tables[key]=[];active=(key,int(words[2]))
            continue
        if words==['END','DIST']:
            assert active and len(tables[active[0]])==active[1]
            active=None;continue
        if active:
            values=tuple(map(float,words));assert len(values)==4
            assert all(math.isfinite(v)and v>=0 for v in values)
            tables[active[0]].append(values)
    assert active is None
    expected=set();unused=set()
    for metal in range(1,layer_count+1):
        for family in ['RESOVER','OVER','OVER0','OVER1','UNDER','UNDER0','UNDER1','DIAGUNDER','OVERUNDER','OVERUNDER0','OVERUNDER1']:
            if family.startswith('OVERUNDER')and metal in (1,layer_count):continue
            section=(metal,family);assert section in sections,section
            widths=sections[section];assert widths is not None
            if family.startswith('UNDER')or family=='DIAGUNDER':
                contexts=[(family,str(upper))for upper in range(metal+1,layer_count+1)]
            elif family.startswith('OVERUNDER'):
                contexts=[('OVER',str(lower),'UNDER',str(upper))
                          for lower in range(1,metal)for upper in range(metal+1,layer_count+1)]
            else:contexts=[(family,str(lower))for lower in range(metal)]
            assert bool(widths)==bool(contexts),(section,widths)
            for context in contexts:
                for width in widths:
                    key=(section,context,width);expected.add(key)
                    assert key in tables,('Missing distance table',key)
                    optional=(family=='RESOVER'and int(context[1])!=0)or(
                        family=='DIAGUNDER'and int(context[1])-metal>4)
                    if optional and not tables[key]:unused.add(key)
                    else:assert tables[key],('Empty required table',key)
    assert set(tables)==expected,'Unexpected or unaccounted tables'
    return dict(schema='block-v1-model-coverage/1',layer_count=layer_count,
                table_count=len(tables),nonempty_tables=len(tables)-len(unused),
                unused_empty_by_family=dict(Counter(key[0][1]for key in unused)),
                required_empty_tables=0,
                unused_empty_policy='RESOVER lower context >0; DIAGUNDER layer separation >4 only')
