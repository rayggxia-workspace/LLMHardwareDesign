from pathlib import Path
p=Path(__file__).parent
for label,node,job,folder,tag in [(762,3,95098,'dynamic-02/node3',5191),(763,25,95204,'dynamic-04/node25',5192)]:
 s=(p/'control162-refill742-remote.py').read_text(encoding='utf-8').replace('sready742-pair-window-refill-node2','sready'+str(label)+'-small-window-refill-node'+str(node)).replace('sready736-pair-window-controls','sready761-weighted-pair-smallwindows').replace("len(tasks['tasks'])==15","len(tasks['tasks'])==14")
 s=s.replace("[(2, 95341, 'dynamic-05/node2', 5190, 'source-510', 0)]",repr([(node,job,folder,tag,'source-510',0)]))
 s=s.replace('r256-older-placement-live-readback-739','r256-older-placement-live-readback-760')
 start=s.index("reason='Reassign");end=s.index("')",start)
 s=s[:start]+"reason='Exact own older S4611 placement5191/5192 guard760/SHA/UID/job/host/PID/cmd/source/out/453graph verified. Reassign only this child step to already-regressed source735 full-chain margin4/16 candidates7580/7581 after actual736/745 pass. Actual757 completed prefix pairs did not show margin64 benefit; narrow window comparison not global conclusion. Preserve every original source/spec/failure/partial log. Eight parents36x16CPU unchanged; node3 1.2*192+16=246.4GiB and node25 1.2*224+16=284.8GiB fit760 actual MemAvailable above437GiB. Other tasks/CUGR3751/externalR untouched. All original final gates mandatory.'"+s[end+1:]
 compile(s,'guard'+str(label),'exec');(p/('control162-refill'+str(label)+'-remote.py')).write_bytes(s.encode())
