"""Exact Liberty logic/state contract for explicitly sized cells, not STA/formal signoff."""
import hashlib,re


def groups(text, keyword):
    pattern=re.compile(r'\b'+keyword+r'\s*\(\s*([^)]*)\)\s*\{')
    for match in pattern.finditer(text):
        depth=1;quote=False;escape=False;i=match.end()
        while depth:
            c=text[i]
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quote=not quote
            elif not quote and c=='{':depth+=1
            elif not quote and c=='}':depth-=1
            i+=1
        yield match.group(1).strip('" '),text[match.end():i-1]


def contract(text, name):
    found=[body for cell,body in groups(text,'cell') if cell==name]
    assert len(found)==1,('Liberty cell not uniquely found',name)
    body=found[0]
    keys=['direction','function','three_state','next_state','clocked_on','clocked_on_also',
          'clear','preset','clear_preset_var1','clear_preset_var2','enable','data_in']
    def fields(part):
        return sorted((key,re.sub(r'\s+','',value)) for key,value in
                      re.findall(r'\b('+'|'.join(keys)+r')\s*:\s*("(?:[^"\\]|\\.)*"|[^;]+)\s*;',part))
    pins=sorted((pin,fields(part)) for pin,part in groups(body,'pin'))
    state=sorted((kind,args,fields(part)) for kind in ['ff','latch'] for args,part in groups(body,kind))
    assert pins and all(any(k=='direction' for k,v in f) for p,f in pins)
    return {'pins':pins,'state':state}


def check_pair(liberties, old, new, reader=None):
    found=[]
    for path in liberties:
        text=reader(path) if reader else path.read_text()
        if not re.search(r'\bcell\s*\(\s*"?'+re.escape(old)+r'"?\s*\)',text):continue
        a,b=contract(text,old),contract(text,new);assert a==b,('Liberty logic/state contract differs',old,new,str(path))
        found.append({'liberty':str(path),'liberty_sha256':hashlib.sha256(text.encode()).hexdigest(),
                      'old_master':old,'new_master':new,'exact_logic_state_contract':a})
    assert len(found)==1,('Ambiguous/missing Liberty pair',old,new)
    return found[0]
