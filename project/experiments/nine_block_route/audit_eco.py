"""Check that the ECO changes only named output drivers and preserves signal pins."""
from pathlib import Path
import re
import sys

original,final,original_lef,final_lef,ports=map(Path,sys.argv[1:6])
midpoint="--midpoint" in sys.argv[6:]
def read_netlist(path):
    cells={}
    text=path.read_text()
    for m in re.finditer(r"^\s+(\w+)\s+(\S+)\s*\((.*?)\);",text,re.S|re.M):
        typ,name,body=m.groups()
        args=dict((p,n.strip()) for p,n in re.findall(r"\.(\w+)\(([^()]*)\)",body))
        if args:
            if name in cells:
                raise ValueError(f"duplicate instance {name}")
            cells[name]=(typ,args)
    assigns=sorted(re.findall(r"^\s*assign\s+([^;]+);",text,re.M))
    return cells,assigns

def signal_pins(path):
    pins={}
    for m in re.finditer(r"^\s+PIN (\S+)\s*\n(.*?)^\s+END \1\s*$",path.read_text(),re.M|re.S):
        name,body=m.groups()
        if re.search(r"USE (POWER|GROUND)",body):
            continue
        pins[name]=(re.search(r"DIRECTION\s+(\w+)",body)[1],
                    tuple(re.findall(r"(LAYER\s+\w+\s*;|RECT\s+[\d. -]+;)",body)))
    return pins

before,pre_assign=read_netlist(original)
after,post_assign=read_netlist(final)
assert pre_assign==post_assign, "assignments changed"
wanted=[line.split()[0].strip("{}") for line in ports.read_text().splitlines()]
for index,name in enumerate(wanted):
    relay=f"eco_relay_{index}"
    cell,pins=after.pop(relay)
    assert cell=="BUF_X32" and pins["Z"]==name,(relay,cell,pins)
    drivers=[key for key,(kind,ios) in before.items() if kind=="BUF_X4" and ios.get("Z")==name]
    assert len(drivers)==1,(name,drivers)
    before[drivers[0]][1]["Z"]=pins["A"]
if midpoint:
    assert after.pop("upper_valid_repeater")==("BUF_X32",{"A":"upper_valid_in","Z":"upper_valid_out"})
missing=sorted(set(before)-set(after))
extra=sorted(set(after)-set(before))
changes=sorted(k for k in set(before)&set(after) if before[k]!=after[k])
assert not (missing or extra or changes),(missing[:12],extra[:12],changes[:12])
p0,p1=signal_pins(original_lef),signal_pins(final_lef)
if midpoint:
    for name,direction in (("upper_valid_in","INPUT"),("upper_valid_out","OUTPUT")):
        actual,geometry=p1.pop(name)
        assert actual==direction and geometry[0]=="LAYER metal10 ;",(name,actual,geometry)
assert p0==p1,[(k,p0.get(k),p1.get(k)) for k in set(p0)|set(p1) if p0.get(k)!=p1.get(k)][:6]
print(f"{len(before)} original cell bindings, {len(wanted)+midpoint} ECO repeaters, {len(p0)} unchanged native signal pins")
