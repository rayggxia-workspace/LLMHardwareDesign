"""Mapped-cell evidence only. No placement/wire/STA values inferred."""
from pathlib import Path
from collections import Counter,deque
import re,json,hashlib,argparse,sys
from mapped_graph import load_graph
sys.setrecursionlimit(10000)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bodies(text,pattern):
    braces=re.compile('[{}]')
    for m in re.finditer(pattern,text):
        start=text.index('{',m.end());depth=1;pos=start+1
        while depth:
            t=braces.search(text,pos);assert t;pos=t.start();depth+=1 if text[pos]=='{'else-1;pos+=1
        yield m[1],text[start+1:pos-1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--map',required=True,type=Path);p.add_argument('--lib',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    receipt=json.loads((a.map/'receipt.json').read_text());assert receipt['passed']and sha(a.map/'mapped.json')==receipt['mapped_json_sha256']
    lib=a.lib.read_text();assert sha(a.lib)==receipt['liberty_sha256'];caps={};areas={}
    unit=re.search(r'capacitive_load_unit\s*\(\s*([\d.]+)\s*,\s*(\w+)\s*\)',lib).groups();ff=float(unit[0])*(1000 if unit[1]=='pf'else 1);assert unit[1]in('pf','ff')
    for cell,body in bodies(lib,r'\bcell\s*\(\s*(\w+)\s*\)'):
        areas[cell]=float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1])
        for pin,pbody in bodies(body,r'\bpin\s*\(\s*(\w+)\s*\)'):
            cap=re.search(r'\bcapacitance\s*:\s*([\d.]+)',pbody)
            if cap:caps[cell+'/'+pin]=float(cap[1])*ff
    cells,names,drivers,loads,netnames,ids,ports=load_graph(a.map);counts=Counter(c[0]for c in cells);root=ids['bank_role']
    def seq(i):return cells[i][0].startswith(('DFF','SDFF','DLH','DLL'))
    def outputs(i):return [(p,n)for p,n in cells[i][2].items()if p in('Q','QN','Z','ZN','CO')]
    def capacitance(n):return sum(caps[cells[i][0]+'/'+p]for i,p in loads[n])
    def info(n):return dict(bit=n,net=netnames.get(n,str(n)),direct_pins=len(loads[n]),nominal_input_capacitance_ff=capacitance(n),load_types=dict(Counter(cells[i][0]+'/'+p for i,p in loads[n])))
    top=[info(n)for n in sorted(loads,key=lambda n:len(loads[n]),reverse=True)[:20]]
    seen={root};comb=set();ends=set();q=deque([root])
    while q:
        n=q.popleft()
        for i,p in loads[n]:
            if seq(i):ends.add((i,p));continue
            if i in comb:continue
            comb.add(i)
            for p,b in outputs(i):
                if b not in seen:seen.add(b);q.append(b)
    memo={};visiting=set()
    def depth(n):
        if n not in drivers or seq(drivers[n][0]):return 0
        i,p=drivers[n]
        if i in memo:return memo[i]
        assert i not in visiting,('combinational cycle',cells[i][1]);visiting.add(i)
        ins=[b for pin,b in cells[i][2].items()if pin not in('Z','ZN','CO','Q','QN')]
        value=1+max((depth(b)for b in ins),default=0);memo[i]=value;visiting.remove(i);return value
    groups={'state_write_D':[],'operand_read_D':[]}
    for i,(typ,name,pins)in enumerate(cells):
        if not seq(i)or'D'not in pins:continue
        label=netnames.get(pins.get('Q',pins.get('QN')),'')
        if label.startswith(('bank0[','bank1[')):groups['state_write_D'].append(depth(pins['D']))
        elif label.startswith(('operand_a','operand_b','operand_state_base')):groups['operand_read_D'].append(depth(pins['D']))
    result=dict(task=receipt['task'],rtl_sha256=receipt['rtl_sha256'],mapped_json_sha256=receipt['mapped_json_sha256'],liberty_sha256=receipt['liberty_sha256'],cells=len(cells),area_um2=sum(areas[t]*c for t,c in counts.items()),counts=dict(counts),bank_role=info(root),top20=top,bank_role_reachability=dict(combinational_cells=len(comb),sequential_endpoint_pins=len(ends),reachable_input_pins=sum(len(loads[n])for n in seen),indirect_input_pins=sum(len(loads[n])for n in seen)-len(loads[root])),max_gate_depth_to_D_all_fanins={k:max(v,default=0)for k,v in groups.items()},STA='未测',placement='未测',wirelength='未测',electrical_violations='未测',scope='Depth counts all combinational fanins from nearest sequential boundary, not a sensitized path or time. Pin C is scalar Liberty sum only. Reachability is structural; indirect cap is not root load.')
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(task=result['task'],cells=result['cells'],area_um2=result['area_um2'],root_direct=len(loads[root]))))
if __name__=='__main__':main()
