"""Flatten placed native DEF patches and real upper routes into one backend DEF.

Supports the routed OpenROAD DEF subset used by the resource library. Unknown
counted sections fail explicitly. Components stay independent, including the
standard cells implementing local control. Native wires are translated only.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

from native_inventory import sha
from resource_base import load_library


SECTIONS=('VIAS','COMPONENTS','PINS','BLOCKAGES','SPECIALNETS','NETS','FILLS')


def sections(text):
    result={}
    found=set(re.findall(r'(?m)^(\w+)\s+\d+\s*;\s*$',text))
    if found-set(SECTIONS):raise ValueError('unsupported native DEF sections: '+str(found-set(SECTIONS)))
    for name in SECTIONS:
        match=re.search(r'(?ms)^'+name+r'\s+(\d+)\s*;\s*\n(.*?)^END '+name+r'\s*$',text)
        if not match:result[name]=[];continue
        body=match[2];records=re.findall(r'(?ms)^\s*(-\s+.*?;)(?=\s*(?:-|$))',body)
        assert len(records)==int(match[1]),('DEF record count',name,len(records),match[1])
        result[name]=records
    return result


def identity(record):return record.split()[1]


def first_name(record,name):return re.sub(r'^(\s*-\s+)\S+',lambda m:m[1]+name,record,count=1)


def shift_pairs(text,dx,dy):
    def replace(m):
        a,b=m[1],m[2];tail=m[3] or ''
        return '( '+(a if a=='*' else str(int(a)+dx))+' '+(b if b=='*' else str(int(b)+dy))+tail+' )'
    return re.sub(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(\s+-?\d+)?\s*\)',replace,text)


def shift_placement(record,dx,dy):
    return re.sub(r'(\+\s+(?:PLACED|FIXED|COVER)\s+)\(\s*(-?\d+)\s+(-?\d+)\s*\)',
                  lambda m:m[1]+'( '+str(int(m[2])+dx)+' '+str(int(m[3])+dy)+' )',record)


def assemble(base,library,binding,upper_def,out):
    out.mkdir();emitted={s:[] for s in SECTIONS};rows=[];grouped=defaultdict(list);removed=set();joins={};proof=[]
    for name,net in binding['nets'].items():
        root='UPPER_'+name
        for endpoint in [net['driver']]+net['sinks']:
            component=base['endpoints'][endpoint]['native_net']
            assert component not in joins or joins[component]==root,'physical component short'
            joins[component]=root;removed.add(endpoint)
    def net_name(group,name):return joins.get(group+'/'+name,group+'/'+name)
    for assembly in base['assemblies']:
        group,template=assembly['id'],assembly['template'];resource=library[template]
        source=Path(resource['views']['odb']['path']).with_suffix('.def')
        assert sha(source)==resource['inventory']['files']['native/6_final.def']['sha256']
        text=source.read_text();parts=sections(text);dx,dy=assembly['translation_dbu']
        units=int(re.search(r'UNITS DISTANCE MICRONS\s+(\d+)',text)[1]);assert units==base['dbu_per_micron']
        vias={identity(v):group+'__'+identity(v) for v in parts['VIAS']}
        master_names={r.split()[2] for r in parts['COMPONENTS']}
        master_alias={n:'SRC_'+template+'_'+n for n in master_names}
        for line in re.findall(r'(?m)^ROW\s+.*?;',text):
            f=line.split();f[1]=group+'__'+f[1];f[3]=str(int(f[3])+dx);f[4]=str(int(f[4])+dy);rows.append(' '.join(f))
        for record in parts['VIAS']:emitted['VIAS'].append(first_name(record,vias[identity(record)]))
        for record in parts['COMPONENTS']:
            name,master=record.split()[1:3]
            record=first_name(record,group+'/'+name)
            if master in master_alias:
                record=re.sub(r'^(\s*-\s+\S+\s+)'+re.escape(master)+r'(?=\s)',lambda m:m[1]+master_alias[master],record,count=1)
            emitted['COMPONENTS'].append(shift_placement(record,dx,dy))
        for record in parts['PINS']:
            pin=identity(record)
            if group+'/'+pin in removed:
                # Internalizing a port must retain its actual frozen metal.
                # DEF wire RECT preserves it without an external electrical
                # port or an invented active cell, including wide M10 landings.
                meta=resource['inventory']['terms'][pin]
                for shape in meta['shapes']:
                    a,b,c,d=shape['rect'];a+=dx;c+=dx;b+=dy;d+=dy
                    x,y=(a+c)//2,(b+d)//2
                    grouped[net_name(group,meta['native_net'])].append(
                        ' + ROUTED %s ( %d %d ) RECT ( %d %d %d %d )'%(shape['layer'],x,y,a-x,b-y,c-x,d-y))
                continue
            record=first_name(record,group+'/'+pin)
            record=re.sub(r'(\+\s+NET\s+)(\S+)',lambda m:m[1]+net_name(group,m[2]),record)
            emitted['PINS'].append(shift_placement(record,dx,dy))
        for section in ('NETS','SPECIALNETS'):
            for record in parts[section]:
                name=identity(record);body=record[record.index(name)+len(name):].rstrip().removesuffix(';')
                def connection(m):
                    inst,pin=m[1],m[2]
                    if inst=='PIN':
                        return '' if group+'/'+pin in removed else '( PIN '+group+'/'+pin+' )'
                    if inst=='*':
                        # A source's PG wildcard must not connect every other
                        # source patch after flattening. Enumerate actual ODB
                        # owners instead of guessing which cells have PG pins.
                        owners={(o['instance'],o['pin']) for t in resource['inventory']['terms'].values()
                                if t['native_net']==name for o in t.get('drivers',[])+t.get('sinks',[])
                                if o['pin']==pin}
                        assert owners,('PG wildcard lacks actual source ODB owners',group,name,pin)
                        return ' '.join('( '+group+'/'+i+' '+p+' )' for i,p in sorted(owners))
                    return '( '+group+'/'+inst+' '+pin+' )'
                # DEF connection tuples precede physical routing options.
                at=re.search(r'\+\s+(?:ROUTED|FIXED|COVER|SHIELD)\b',body)
                head,tail=(body[:at.start()],body[at.start():]) if at else (body,'')
                head=re.sub(r'\(\s*(\S+)\s+(\S+)\s*\)',connection,head)
                tail=shift_pairs(tail,dx,dy)
                tail=re.sub(r'\S+',lambda m:vias.get(m[0],m[0]),tail)
                body=head+tail
                if section=='SPECIALNETS':emitted[section].append('- '+group+'/'+name+body+' ;')
                else:grouped[net_name(group,name)].append(body)
        for section in ('BLOCKAGES','FILLS'):
            for record in parts[section]:
                record=re.sub(r'(\+\s+COMPONENT\s+)(\S+)',lambda m:m[1]+group+'/'+m[2],record)
                emitted[section].append(shift_pairs(record,dx,dy))
        proof.append({'group':group,'native_def_sha256':sha(source),'components':len(parts['COMPONENTS']),
                      'translation_dbu':[dx,dy],'native_master_aliases':master_alias})
    upper=sections(upper_def)
    assert not upper['COMPONENTS'] and not upper['VIAS'],'upper view unexpectedly contains active instances or DEF vias'
    for record in upper['NETS']:
        name=identity(record);body=record[record.index(name)+len(name):].rstrip().removesuffix(';')
        body=re.sub(r'\(\s*PIN\s+\S+\s*\)','',body)
        grouped['UPPER_'+name].append(body)
    for name,bodies in sorted(grouped.items()):
        # DEF connections must precede routing. Joined components may have
        # independent ROUTED clauses; express them as one route with NEW paths.
        heads=[];paths=[]
        for body in bodies:
            body=re.sub(r'\+\s+USE\s+\w+','',body)
            at=re.search(r'\+\s+ROUTED\b',body)
            if at:
                heads.append(body[:at.start()])
                paths.append(re.sub(r'\+\s+ROUTED\b','NEW',body[at.start():]))
            else:heads.append(body)
        routing=' '.join(paths)
        if routing:routing=re.sub(r'^NEW\b','+ ROUTED',routing,count=1)
        emitted['NETS'].append('- '+name+' '+' '.join(heads)+' + USE SIGNAL '+routing+' ;')
    header=('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN routed_resource_assembly ;\n'
            'UNITS DISTANCE MICRONS %d ;\nDIEAREA ( %d %d ) ( %d %d ) ;\n')%(base['dbu_per_micron'],*base['bounds_dbu'])
    with (out/'assembled.def').open('x') as f:
        f.write(header+'\n'.join(rows)+'\n')
        for section in SECTIONS:
            records=emitted[section]
            if records:f.write(section+' '+str(len(records))+' ;\n'+'\n'.join(records)+'\nEND '+section+'\n')
        f.write('END DESIGN\n')
    result={'schema_version':'flat-native-def-assembly/1','sources':proof,
            'counts':{s:len(v) for s,v in emitted.items()},'joined_native_components':joins,
            'removed_internal_boundary_ports':sorted(removed),'assembled_def_sha256':sha(out/'assembled.def'),
            'physical_qualified':False,'scope':'actual native components and wires plus routed upper nets; ODB/GDS/connectivity/RC gates remain required'}
    (out/'assembly.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','library','binding','upper_def','output'):p.add_argument(n,type=Path)
    a=p.parse_args();read=lambda p:json.loads(p.read_text())
    print(json.dumps(assemble(read(a.base),load_library(a.library),read(a.binding),a.upper_def.read_text(),a.output)))
