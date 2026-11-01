"""Add declared port pi RC while preserving all extracted native parasitics.

Only the pinned OpenRCX grammar is accepted. Native coupling terms, including
cross-net references to top ports, move to the internal side of each new wire.
This is a sensitivity model, not a twelve-layer extraction or process model.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for raw in iter(lambda:stream.read(1024*1024),b''):h.update(raw)
    return h.hexdigest()


def inventory(path,costs):
    found={};mode=None;net=None;units={}
    with Path(path).open()as stream:
        for line in stream:
            tokens=line.split()
            if not tokens:continue
            if tokens[0]in ('*C_UNIT','*R_UNIT'):units[tokens[0]]=tokens[1:]
            if tokens[0]=='*D_NET':net=tokens[1];mode=None
            elif tokens[0]=='*CONN':mode='conn'
            elif tokens[0]in ('*CAP','*RES','*END'):mode=None
            elif mode=='conn'and tokens[0]=='*P':
                assert len(tokens)>=3 and re.fullmatch(r'\*\d+',net)
                literal=tokens[1];name=re.sub(r'\\(.)',r'\1',literal)
                assert name in costs and name not in found
                assert not any(v['net']==net for v in found.values()),'Aliased top ports are unsupported'
                found[name]=dict(net=net,literal=literal,internal=net+':999999999',direction=tokens[2],**costs[name])
    assert units=={'*C_UNIT':['1','PF'],'*R_UNIT':['1','OHM']},units
    assert set(found)==set(costs),('Missing real boundary ports',set(costs)-set(found))
    return found


def augment(original,target,costs):
    """Each cost has wire_cap_ff and series_r_ohm; no receiver load here."""
    original=Path(original);target=Path(target);assert original.resolve()!=target.resolve()
    before=digest(original);ports=inventory(original,costs)
    bynet={v['net']:v for v in ports.values()};replace={v['literal']:v['internal']for v in ports.values()}
    internal=set(replace.values())
    current=None;mode=None;cap_index=0;res_index=0;modified_caps=0;modified_res=0
    with original.open()as source,target.open('w')as dest:
        for line in source:
            tokens=line.split()
            if not tokens:dest.write(line);continue
            assert not any(t in internal for t in tokens),'New internal-node ID collision'
            if tokens[0]=='*D_NET':
                assert len(tokens)==3
                current=bynet.get(tokens[1]);mode=None;cap_index=0;res_index=0
                if current:
                    cap=Decimal(str(current['wire_cap_ff']))/1000
                    assert cap>0 and Decimal(str(current['series_r_ohm']))>0
                    tokens[2]=str(Decimal(tokens[2])+cap);line=' '.join(tokens)+'\n'
            elif tokens[0]=='*CAP':mode='cap'
            elif tokens[0]=='*RES':
                if current:
                    assert mode=='cap'and cap_index>0
                    half=Decimal(str(current['wire_cap_ff']))/2000
                    dest.write('%d %s %s\n'%(cap_index+1,current['literal'],half))
                    dest.write('%d %s %s\n'%(cap_index+2,current['internal'],half))
                mode='res'
            elif tokens[0]=='*END':
                if current:
                    assert mode=='res'and res_index>0
                    dest.write('%d %s %s %s\n'%(res_index+1,current['literal'],current['internal'],current['series_r_ohm']))
                current=None;mode=None
            elif mode in ('cap','res'):
                assert tokens[0].isdigit()
                if mode=='cap':
                    assert len(tokens)in(3,4);cap_index=max(cap_index,int(tokens[0]));node_fields=range(1,len(tokens)-1)
                else:
                    assert len(tokens)==4;res_index=max(res_index,int(tokens[0]));node_fields=(1,2)
                changed=False
                for i in node_fields:
                    if tokens[i]in replace:tokens[i]=replace[tokens[i]];changed=True
                if changed:
                    line=' '.join(tokens)+'\n'
                    if mode=='cap':modified_caps+=1
                    else:modified_res+=1
            dest.write(line)
    assert digest(original)==before
    audit(original,target,ports)
    return dict(passed=True,ports=ports,port_count=len(ports),native_spef_sha256=before,
        modified_spef_sha256=digest(target),native_parasitics_preserved=True,
        rewritten_native_cap_records=modified_caps,rewritten_native_res_records=modified_res,
        scope='All real top ports including clock. Two added half-C nodes and one series R per port; native ground/coupling/resistors retained at internal side. New coupling and calibrated process/remote drivers are not modeled.')


def audit(original,target,ports):
    """Independent line-pair inverse: no native record may vanish or change."""
    bynet={v['net']:v for v in ports.values()};inverse={v['internal']:v['literal']for v in ports.values()}
    external={v['literal']for v in ports.values()}
    current=None;mode=None;cap_index=0;res_index=0;count=0
    with Path(original).open()as source,Path(target).open()as stream:
        for native in source:
            a=native.split();b=stream.readline().split()
            if not a:assert not b;continue
            if a[0]=='*D_NET':
                current=bynet.get(a[1]);mode=None;cap_index=0;res_index=0
                assert a[:2]==b[:2]
                assert Decimal(b[2])-Decimal(a[2])==(Decimal(str(current['wire_cap_ff']))/1000 if current else 0)
                continue
            if a[0]=='*RES':
                if current:
                    half=Decimal(str(current['wire_cap_ff']))/2000
                    for index,node in [(cap_index+1,current['literal']),(cap_index+2,current['internal'])]:
                        assert b[:2]==[str(index),node]and len(b)==3 and Decimal(b[2])==half
                        b=stream.readline().split()
                mode='res'
            elif a[0]=='*END':
                if current:
                    assert b[:3]==[str(res_index+1),current['literal'],current['internal']]
                    assert len(b)==4 and Decimal(b[3])==Decimal(str(current['series_r_ohm']))
                    b=stream.readline().split();count+=1
                current=None;mode=None
            elif a[0]=='*CAP':mode='cap'
            elif mode in ('cap','res'):
                assert a[0].isdigit()and b[0]==a[0]and len(a)==len(b)
                assert all(t not in external for t in b[1:-1]),'Native parasitic left at new external boundary'
                if mode=='cap':cap_index=max(cap_index,int(a[0]))
                else:res_index=max(res_index,int(a[0]))
                b=[inverse.get(t,t)for t in b]
            assert a==b,('Native parasitic record changed',a,b)
        assert not stream.read()and count==len(ports)


def fixtures(folder):
    """Structural positive and actual cross-net/added-R corruption controls."""
    folder=Path(folder);folder.mkdir(exist_ok=True)
    text='''*SPEF "ieee 1481-1999"
*DESIGN "revision300_rc_fixture"
*DATE "fixed research fixture"
*VENDOR "research"
*PROGRAM "explicit pi control"
*VERSION "1"
*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER []
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
*NAME_MAP
*1 d
*2 q
*3 clk
*D_NET *1 0.01
*CONN
*P d I
*I ff:D I
*CAP
1 d 0.004
2 ff:D 0.005
3 d q 0.001
*RES
1 d ff:D 0.1
*END
*D_NET *2 0.01
*CONN
*P q O
*I ff:Q O
*CAP
1 q 0.004
2 ff:Q 0.005
3 q d 0.001
*RES
1 q ff:Q 0.1
*END
*D_NET *3 0.01
*CONN
*P clk I
*I ff:CK I
*CAP
1 clk 0.005
2 ff:CK 0.005
*RES
1 clk ff:CK 0.1
*END
'''
    original=folder/'fixture.spef';original.write_text(text)
    costs={p:dict(wire_cap_ff=20,series_r_ohm=10)for p in ('d','q','clk')}
    report=augment(original,folder/'positive.spef',costs)
    assert report['port_count']==3
    raw=(folder/'positive.spef').read_text();rejected=[]
    for label,bad in [('wrong-series-r',raw.replace('10\n','11\n',1)),
                      ('missing-half-c',raw.replace('5 *1:999999999 0.01\n','')),
                      ('native-coupling-left-outside',raw.replace('3 *2:999999999 *1:999999999 0.001','3 *2:999999999 d 0.001'))]:
        assert bad!=raw
        p=folder/(label+'.spef');p.write_text(bad)
        try:audit(original,p,report['ports'])
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Altered real SPEF accepted: '+label)
    return dict(passed=True,structural_only=True,rejected=rejected,positive=report)
