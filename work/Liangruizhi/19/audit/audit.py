"""Independent selected-data audit. No production parser/validator imports.
Intentionally supports the actual line-oriented generated Liberty and LEF
profiles only; any unsupported interface form aborts the audit.
"""
import argparse
import collections
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

CHECKS = 0
def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def same(a,b,message):
    check(a == b, message)

def cleaned(text):
    # Mask strings/comments with equal-length spaces while retaining line breaks.
    token = re.compile(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*')
    return token.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), text)

def liberty_groups(data):
    text=data.decode('ascii'); masked=cleaned(text)
    groups=[];stack=[];syntax_gaps=[]
    for line,(original,visible) in enumerate(zip(text.splitlines(),masked.splitlines()),1):
        opens,closes=visible.count('{'),visible.count('}')
        if opens:
            check(opens==1 and closes==0,'unhandled Liberty group line')
            m=re.fullmatch(r'\s*(\w+)\s*\(([^()]*)\)\s*{\s*',original)
            check(m is not None,'unsupported generated group header')
            g={'kind':m[1],'arg':m[2].strip().strip('"'),'line':line,'attrs':{},'children':[],
               'parent':stack[-1] if stack else None}
            if stack:stack[-1]['children'].append(g)
            groups.append(g);stack.append(g)
        elif closes:
            check(closes==1 and len(stack)>0,'unbalanced Liberty group')
            stack.pop()
        elif stack:
            m=re.fullmatch(r'\s*(\w+)\s*:\s*(.*?)\s*;\s*',original)
            if m:
                check(m[1] not in stack[-1]['attrs'],'duplicate attribute')
                stack[-1]['attrs'][m[1]]={'raw':m[2],'value':m[2].strip('"'),'line':line}
            elif re.match(r'\s*\w+\s*:',original):
                area=re.fullmatch(r'\s*area\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*',original)
                check(stack[-1]['kind']=='cell' and area is not None,'unhandled unterminated attribute')
                next_line=text.splitlines()[line]
                check(re.fullmatch(r'\s*is_macro_cell\s*:\s*true\s*;\s*',next_line) is not None,'area follower differs')
                syntax_gaps.append({'kind':'cell_area_missing_semicolon','line':line,'value':area[1],'raw_line':original})
    check(not stack,'Liberty ended with unclosed group')
    cells=[g for g in groups if g['kind']=='cell']; same(len(cells),1,'cell count')
    types={g['arg']:g for g in groups if g['kind']=='type'}
    result={};buses={}
    for g in groups:
        if g['kind']=='bus':
            t=types[g['attrs']['bus_type']['value']]
            first,last,width=(int(t['attrs'][k]['value']) for k in ('bit_from','bit_to','bit_width'))
            same(abs(first-last)+1,width,'type range width')
            buses[g['arg']]={'indices':set(range(min(first,last),max(first,last)+1)),'seen':set(),'node':g}
        if g['kind'] not in ('pin','pg_pin'):continue
        check(g['arg'] not in result,'duplicate literal pin')
        parent=g['parent']; bus=parent if parent['kind']=='bus' else None
        # These frozen libraries use explicit one-bit pins; ranges must be
        # audited by another independent profile rather than guessed here.
        check(':' not in g['arg'],'range pin outside audit profile')
        direct=g['attrs'].get('direction')
        inherited=None if bus is None else bus['attrs'].get('direction')
        direction=(direct or inherited or {}).get('value')
        if bus:
            m=re.fullmatch(re.escape(bus['arg'])+r'\[(\d+)\]',g['arg'])
            check(m is not None,'bus child name mismatch')
            b=buses[bus['arg']];index=int(m[1])
            check(index in b['indices'] and index not in b['seen'],'bus pin outside/duplicate')
            b['seen'].add(index)
        result[g['arg']]={'direction':direction,'line':g['line'],'attrs':g['attrs'],'bus':bus}
    for b in buses.values():same(b['indices'],b['seen'],'bus coverage')
    return cells[0]['arg'],result,buses,len(text.splitlines()),syntax_gaps

def lef_pins(data):
    lines=data.decode('ascii').splitlines()
    pins={};pin=None;port=None;layer=None;dbu=None;macro=None
    for line,raw in enumerate(lines,1):
        words=raw.strip().split()
        if not words:continue
        if words[:2]==['DATABASE','MICRONS']:dbu=int(words[2])
        if words[0]=='MACRO':macro=words[1]
        if words[0]=='PIN':
            check(pin is None and words[1] not in pins,'duplicate/nested LEF pin')
            pin={'name':words[1],'line':line,'ports':[]};pins[words[1]]=pin
        elif pin is not None:
            if words[0]=='DIRECTION':pin['direction']=words[1]
            elif words[0]=='USE':pin['use']=words[1]
            elif words[0]=='PORT':
                check(port is None,'nested PORT')
                port=[];pin['ports'].append(port);layer=None
            elif words[0]=='LAYER':
                check(port is not None,'layer outside PORT');layer=words[1]
            elif words[0]=='RECT':
                check(port is not None and layer is not None and words[-1]==';','RECT profile')
                coords=words[1:5]
                values=[Decimal(x)*dbu for x in coords]
                check(all(x==x.to_integral_value() for x in values),'noninteger DBU')
                port.append({'layer':layer,'rect_um':coords,'rect_dbu':[int(x) for x in values],'line':line})
            elif words[0]=='END':
                if len(words)==1:
                    check(port is not None,'bare END outside PORT');port=None;layer=None
                else:
                    same(words[1],pin['name'],'pin END mismatch');pin=None
    check(pin is None and port is None,'unclosed LEF pin')
    return macro,pins,dbu,len(lines)

def inspect(folder,out):
    global CHECKS
    folder=Path(folder);inp=folder/'inputs'
    manifest=json.loads((folder/'manifest.json').read_bytes())
    capture=json.loads((inp/'capture.json').read_bytes())
    cfg=json.loads((inp/'inputs.json').read_bytes())
    views=json.loads((folder/'views.json').read_bytes())
    graph=json.loads((folder/'graph.json').read_bytes())
    summary=json.loads((folder/'summary.json').read_bytes())
    same(set(manifest['files']),{p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}-{'manifest.json'},'run members')
    for name,info in manifest['files'].items():
        data=(folder/name).read_bytes()
        same(len(data),info['bytes'],'file bytes '+name);same(sha(data),info['sha256'],'file sha '+name)
    same(sha((inp/'capture.json').read_bytes()),manifest['input_manifest_sha256'],'capture SHA')
    same(sha((inp/'contract.json').read_bytes()),cfg['upstream']['contract_sha256'],'pinned contract SHA')
    same(capture['reused_lef16_archive_sha256'],cfg['lef16']['archive_sha256'],'LEF archive SHA')
    independently_parsed={};report={'macros':{},'source_commit':manifest['provenance']['source_commit']}
    for m in cfg['macros']:
        candidate=m['id'];view=views[candidate]
        elab=json.loads((inp/candidate/'elab.json').read_bytes())
        rawports=elab['modules'][m['macro']]['ports']
        cell,lib,buses,liblines,syntax_gaps=liberty_groups((inp/candidate/(m['macro']+'_typ.lib')).read_bytes())
        macro,lef,dbu,leflines=lef_pins((inp/(candidate+'.lef')).read_bytes())
        same(cell,m['macro'],'Liberty cell');same(macro,m['macro'],'LEF macro')
        if syntax_gaps:
            meta=view['liberty_metadata']
            same(meta['syntax_strict'],False,'strict Liberty gap remains explicit')
            same(meta['syntax_recovery_count'],len(syntax_gaps),'recovery count')
            recovered=[d for d in meta['diagnostics'] if d['kind']=='missing_cell_area_semicolon_compatibility']
            same(len(recovered),len(syntax_gaps),'recovery diagnostic count')
            for actual,expected in zip(recovered,syntax_gaps):
                same(actual['line'],expected['line'],'recovery line')
                same(actual['raw_value'],expected['value'],'recovery raw value')
                same(actual['next_field'],'is_macro_cell','recovery boundary field')
                same(actual['next_field_line'],expected['line']+1,'recovery next line')
        same(set(lib),set(lef),'raw Lib/LEF names')
        for key,source in [('elab.json',inp/candidate/'elab.json'),('boundary.sv',inp/candidate/'boundary.sv'),('liberty',inp/candidate/(m['macro']+'_typ.lib')),('lef',inp/(candidate+'.lef'))]:
            same(view['source_hashes'][key],sha(source.read_bytes()),'view source SHA '+key)
        logical={};ids=collections.defaultdict(list);constants=[]
        for name,port in rawports.items():
            width=len(port['bits'])
            same(port.get('offset',0),0,'selected zero offset')
            same(port.get('upto',0),0,'selected descending declaration')
            bits=[name] if width==1 else [name+'['+str(i)+']' for i in range(width)]
            same(view['ports'][name]['bits'],bits,'expanded port bits')
            same(view['ports'][name]['width'],width,'port width')
            same(view['ports'][name]['direction'],port['direction'],'port direction')
            for i,(bit,bitid) in enumerate(zip(bits,port['bits'])):
                logical[bit]={'direction':port['direction'],'yosys_bit':bitid,'port':name,'position':i}
                if isinstance(bitid,int):ids[bitid].append(bit)
                else:constants.append({'bit_name':bit,'value':bitid})
        same(set(logical),set(view['bits']),'logical bit membership')
        rawsignals={n for n,p in lef.items() if p['use'] in ('SIGNAL','CLOCK')}
        same(set(logical),rawsignals,'LEF signal membership')
        aliases=[{'yosys_bit':key,'bit_names':names} for key,names in sorted(ids.items()) if len(names)>1]
        same(view['aliases'],aliases,'aliases');same(view['constants'],constants,'constants')
        for name,expected in logical.items():
            row=view['bits'][name];l=lib[name];p=lef[name]
            same(row['bit_name'],name,'row name')
            same(row['yosys_bit'],expected['yosys_bit'],'raw Yosys bit')
            same(row['position_lsb_first'],expected['position'],'LSB position')
            same(row['yosys_pointer'],'/modules/'+m['macro']+'/ports/'+expected['port']+'/bits/'+str(expected['position']),'Yosys JSON pointer')
            same(row['direction'],expected['direction'],'logical direction')
            same(l['direction'],expected['direction'],'Liberty direction')
            same(p['direction'].lower(),expected['direction'],'LEF direction')
            same(row['liberty']['line'],l['line'],'Liberty raw line')
            same(row['liberty']['raw_name'],name,'Liberty raw name')
            same(row['liberty']['effective_direction'],l['direction'],'Liberty parsed direction')
            same(set(row['liberty']['fields']),set(l['attrs']),'Liberty field set')
            for key,value in l['attrs'].items():
                for field in ('raw','value','line'):
                    same(row['liberty']['fields'][key][field],value[field],'Liberty field '+key)
            same(row['lef']['line'],p['line'],'LEF PIN line')
            same(row['lef']['use'],p['use'],'LEF USE')
            same([x['rects'] for x in row['lef']['ports']],p['ports'],'LEF PORT RECTs')
            same(row['legal_access_verified'],False,'access scope')
        pgs={x['bit_name']:x for x in view['power']}
        pg_direction_mismatches=[]
        same(set(pgs),set(lef)-rawsignals,'PG membership')
        for name,row in pgs.items():
            same(row['lef']['line'],lef[name]['line'],'PG source line')
            same(row['liberty']['raw_name'],name,'PG library name')
            same(row['liberty']['line'],lib[name]['line'],'PG library line')
            same(row['liberty']['effective_direction'],lib[name]['direction'],'PG library direction')
            matches=lib[name]['direction']==lef[name]['direction'].lower()
            same(row['direction_match'],matches,'PG mismatch flag')
            if not matches: pg_direction_mismatches.append({'name':name,'liberty_direction':lib[name]['direction'],'lef_direction':lef[name]['direction'],'liberty_line':lib[name]['line'],'lef_line':lef[name]['line']})
            same([x['rects'] for x in row['lef']['ports']],lef[name]['ports'],'PG raw geometry')
            same(row['classification'],lef[name]['use'].lower(),'PG classification')
            same(row['supply_connectivity_verified'],False,'PG scope')
        report['macros'][candidate]={'signal_bits':len(logical),'pg_pins':len(pgs),'port_count':len(rawports),
            'liberty_buses':len(buses),'raw_liberty_lines':liblines,'raw_lef_lines':leflines,
            'liberty_strict_syntax_valid':False if syntax_gaps else 'not independently validated',
            'liberty_syntax_gaps':syntax_gaps,
            'constant_bits':constants,'alias_groups':aliases,'pg_direction_mismatches':pg_direction_mismatches}
        independently_parsed[candidate]=logical
    contract=json.loads((inp/'contract.json').read_bytes())['tasks']['top-contract']['validation']['top_contract']
    nets=collections.defaultdict(set);connections=[]
    for group in contract['connections']:
        width=group['width']
        an,mn=group['act_port'],group['mxu_port']
        for i in range(width):
            a=an if width==1 else an+'['+str(i)+']'
            m=mn if width==1 else mn+'['+str(i)+']'
            key=('external:' if mn=='computing' else 'interface:')+m
            nets[key].update({('ACT20',a),('MXU20',m)})
            connections.append((a,m))
    for port,desc in contract['external_ports'].items():
        for i in range(desc['width']):
            name=port if desc['width']==1 else port+'['+str(i)+']'
            net=nets['external:'+name];net.add(('TOP',name))
            for candidate,logical in independently_parsed.items():
                if name in logical:net.add((candidate,name))
    same({n['name'] for n in graph['nets']},set(nets),'net membership')
    for net in graph['nets']:
        same({(e['candidate'],e['name']) for e in net['endpoints']},nets[net['name']],'net endpoint membership')
        same(len(net['endpoints']),len(nets[net['name']]),'no duplicate terminals')
        drivers=[]
        for e in net['endpoints']:
            if e['candidate']=='TOP':
                expected=contract['external_ports'][e['port']]['direction']
                role='driver' if expected=='input' else 'sink'
            else:
                expected=independently_parsed[e['candidate']][e['name']]['direction']
                role='driver' if expected=='output' else 'sink'
            same(e['direction'],expected,'endpoint direction');same(e['role'],role,'endpoint role')
            if role=='driver':drivers.append((e['candidate'],e['name']))
        same(len(drivers),1,'boundary driver count')
        same((net['driver']['candidate'],net['driver']['name']),drivers[0],'selected driver')
    same([(r['act']['name'],r['mxu']['name']) for r in graph['connections']],connections,'existing contract bit pairs')
    bitrows=list(csv.DictReader((folder/'bits.csv').open(encoding='utf-8',newline='')))
    same(len(bitrows),sum(len(x) for x in independently_parsed.values()),'CSV bit count')
    same({(r['candidate'],r['bit_name']) for r in bitrows},{(c,n) for c,v in independently_parsed.items() for n in v},'CSV exact keys')
    connrows=list(csv.DictReader((folder/'connections.csv').open(encoding='utf-8',newline='')))
    same(len(connrows),len(connections),'CSV connection count')
    check(all(value is False for value in summary['limitations'].values()),'unproven gates remain false')
    same(summary['status'],'SIGNAL_INTERFACE_CHECKED_WITH_RECORDED_INPUT_DIAGNOSTICS','qualified summary scope')
    report.update({'status':'PASS','checks':CHECKS,'net_count':len(nets),'connection_bits':len(connections),
        'script_sha256':sha(Path(__file__).read_bytes()),'run_manifest_sha256':sha((folder/'manifest.json').read_bytes()),
        'scope':'Independent raw-text interface/geometry and boundary-graph audit; no production parsers imported; observed Liberty missing semicolons remain recorded; no full Liberty grammar, timing/functional/legal-access proof'})
    Path(out).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--out',required=True);a=p.parse_args()
    inspect(a.run,a.out)
