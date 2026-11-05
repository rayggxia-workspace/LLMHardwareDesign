from pathlib import Path
p=Path(__file__).parent
s=(p/'control162-audit650.py').read_text(encoding='utf-8')
s=s.replace('audit-650','audit-674').replace('[6360,6361]','[6560,6561,6562,6563,6720]')
s=s.replace("fields[15]=='2';fields[15]=str(8 if seed==6360 else 32)","fields[10]=='1';fields[10]=str({6560:4,6561:8,6562:16,6563:32,6720:0}[seed])")
s=s.replace('nonpreferred_direction_cost','global_congestion_scale')
s=s.replace("[(95155,5,'dynamic-03/node5',[6360]),(95101,6,'dynamic-02/node6',[6361])]","[(95341,2,'dynamic-05/node2',[6560]),(95098,3,'dynamic-02/node3',[6561]),(95204,25,'dynamic-04/node25',[6562]),(95391,4,'dynamic-05/node4',[6563]),(95101,6,'dynamic-02/node6',[6720])]")
a=s.index("r.update(passed=True,scope=")
z=s.index('\nexcept BaseException',a)
s=s[:a]+"r.update(passed=True,scope='Actual five own16CPU pools and80 real inputs checked; only global congestion scale differs5890:4/8/16/32/0(default256 at h256). Actual CPU affinity, UID, command, memory admission checked. Actual655 and671 regression receipts bound separately. No convergence or physical acceptance claim.')"+s[z:]
compile(s,'audit674','exec');(p/'control162-audit674.py').write_bytes(s.encode())
s=(p/'control162-config651-remote.py').read_text(encoding='utf-8').replace('audit-651','audit-675')
s=s.replace("[('sready635-directional-bidirectional-controls',[6360,6361])]","[('sready655-global-congestion-controls',[6560,6561,6562,6563]),('sready671-default-congestion-control',[6720])]")
s=s.replace('6360/6361 and14','6560/6561/6562/6563/6720 and35')
compile(s,'config675','exec');(p/'control162-config675-remote.py').write_bytes(s.encode())
