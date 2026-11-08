"""Namespace actual native SPEF networks into the flat physical assembly.

This is an identity transform of the native R/C records. Source interfaces
remain separate until stitch_rc joins them using the actual routed binding.
"""
import argparse
import json
from pathlib import Path
import re
from native_inventory import sha
from resource_base import load_library


def assemble(base,library,binding,output):
    joined={}
    for net,row in binding['nets'].items():
        for port in [row['driver']]+row['sinks']:
            component=base['endpoints'][port]['native_net']
            assert component not in joined or joined[component]=='UPPER_'+net
            joined[component]='UPPER_'+net
    sources={};name_map=[];port_lines=[];fingerprints=[];counter=0
    temporary=output.with_suffix('.body.tmp')
    with temporary.open('x') as stream:
        for assembly in base['assemblies']:
            group,template=assembly['id'],assembly['template'];resource=library[template]
            if template not in sources:
                path=Path(resource['views']['odb']['path']).with_suffix('.spef')
                assert sha(path)==resource['inventory']['files']['native/6_final.spef']['sha256']
                raw=path.read_text();header,*sections=re.split(r'(?m)^\*D_NET ',raw)
                assert '*C_UNIT 1 PF' in header and '*R_UNIT 1 OHM' in header
                before,maps=header.split('*NAME_MAP\n',1);maps,ports=maps.split('*PORTS\n',1)
                entries=re.findall(r'(?m)^(\*\d+) (\S+)\s*$',maps)
                sources[template]=(path,before,entries,ports,sections)
            path,before,entries,ports,sections=sources[template]
            indices={}
            for key,value in entries:
                counter+=1;new='*'+str(counter);indices[key]=new
                full=group+'/'+value
                name_map.append(new+' '+joined.get(full,group+r'\/'+value)+'\n')
            # Literal top-port references are not necessarily name-map tokens.
            literals={}
            for line in ports.splitlines():
                if not line.strip():continue
                fields=line.split();literal=fields[0];literals[literal]=group+r'\/'+literal
                port_lines.append(literals[literal]+' '+' '.join(fields[1:])+'\n')
            def token(value):
                if value in literals:return literals[value]
                key,separator,suffix=value.partition(':')
                if key in indices:return indices[key]+separator+suffix
                return value
            for section in sections:
                title,body=section.split('\n',1)
                key,total=title.split()
                stream.write('*D_NET '+indices[key]+' '+total+'\n')
                for line in body.splitlines(keepends=True):
                    fields=line.split()
                    if fields and fields[0]=='*I' and '*D' in fields:
                        model=fields.index('*D')+1
                        fields[model]='SRC_'+template+'_'+fields[model]
                        line=' '.join(fields)+'\n'
                    stream.write(re.sub(r'\S+',lambda m:token(m[0]),line))
            fingerprints.append({'group':group,'source':str(path),'sha256':sha(path)})
    prefix=re.sub(r'(?m)^\*DESIGN .*$', '*DESIGN "routed_resource_assembly"',next(iter(sources.values()))[1])
    with output.open('x') as stream:
        stream.write(prefix+'*NAME_MAP\n'+''.join(name_map)+'\n*PORTS\n'+''.join(port_lines)+'\n')
        with temporary.open() as body:
            for chunk in iter(lambda:body.read(4<<20),''):stream.write(chunk)
    # Keep the staged body and source manifest for forensic comparison.
    result={'sources':fingerprints,'name_map_entries':counter,'native_spef_sha256':sha(output),
            'scope':'native R/C identity transformation; upper geometry is not yet added'}
    output.with_suffix('.sources.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','library','binding','output'):p.add_argument(n,type=Path)
    a=p.parse_args();read=lambda p:json.loads(p.read_text())
    print(json.dumps(assemble(read(a.base),load_library(a.library),read(a.binding),a.output)))
