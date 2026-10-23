"""Integrate passive upper routes into the original frozen resource DEF."""
import json
from pathlib import Path
import re
from freeze_audit import section,audit

def routed_parts(row):
    return re.split(r'\+ (?:ROUTED|FIXED) |\n\s*NEW ',row)

def integrate(frozen,proxy,output,aliases=None):
    base=Path(frozen).read_text();new=Path(proxy).read_text()
    native={}
    count=0
    for row in section(new,'NETS'):
        parts=routed_parts(row)
        proxy_name=parts[0].split()[0]
        name=aliases[proxy_name] if aliases is not None else proxy_name
        paths=[]
        for path in parts[1:]:
            layer=re.match(r'metal(\d+)\s',path)
            assert layer and 8<=int(layer[1])<=10,'Proxy wrote outside custom metals'
            rest=re.sub(r'\([^)]*\)','',path).split()
            assert len(rest) in (1,2)
            if len(rest)==2:
                assert re.fullmatch(r'via[89](?:_\d+)?',rest[1]),'Proxy wrote non-custom via'
            paths.append(path.strip());count+=1
        native.setdefault(name,[]).extend(paths)
    assert native and count>0
    rows=[];matched=set()
    for row in section(base,'NETS'):
        parts=routed_parts(row);header=parts[0].strip();name=header.split()[0]
        paths=native.get(name,[])
        if name in native:matched.add(name)
        rows.append('    - '+header+'\n'+''.join('      + FIXED '+p.strip()+'\n' for p in parts[1:])+
            ''.join('      + ROUTED '+p+'\n' for p in paths)+'    ;\n')
    assert matched==set(native),'Proxy changed logical net names'
    m=re.search(r'^NETS \d+ ;\n.*?^END NETS',base,re.M|re.S)
    final=base[:m.start()]+'NETS '+str(len(rows))+' ;\n'+''.join(rows)+'END NETS'+base[m.end():]
    Path(output).write_text(final)
    result=audit(frozen,output,8,Path(output).with_suffix('.freeze-audit.json'),True)
    result.update(integrated_nets=len(native),custom_paths=count)
    Path(output).with_suffix('.integration.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
