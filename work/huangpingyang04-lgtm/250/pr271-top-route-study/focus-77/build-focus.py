"""Add the focused empty-board phase to the existing scarce-first driver."""
from pathlib import Path
import sys


text=Path(sys.argv[1]).read_text()
edits=[
    ('struct Stub {Route route; Range shapes{}; bool active=false;};',
     'struct Stub {Route route; Range shapes{}; bool active=false;};\n#include "focus-route.inc"'),
    ('const vector<vector<PinAccess>>& access,Board& board,int density)',
     'const vector<vector<PinAccess>>& access,Board& board,int density,int mode)'),
    ('    int held=0,requested=0;', '    route_focus(nets,board,stubs,mode,28,1450);\n    int held=0,requested=0;'),
    ('        if(done[n.id][pin])return;', '        if(done[n.id][pin]||stubs[n.id][pin].active||has_route(board.routes[n.id]))return;'),
    ('reserve(nets,tasks,access,board,density);','reserve(nets,tasks,access,board,density,mode);'),
    ('        left[n.id]=int(n.pins.size())-1;',
     '        left[n.id]=has_route(board.routes[n.id])?0:int(n.pins.size())-1;\n'
     '        if(!left[n.id])fill(completed[n.id].begin(),completed[n.id].end(),true);'),
    ('    int attempted=0,done_branches=0,done_nets=0,early_multi=0,early_short=0;',
     '    int attempted=0,done_branches=0,done_nets=route_count(board),early_multi=0,early_short=0;'),
    ('        const auto& full=nets[id];',
     '        const auto& full=nets[id];\n        if(!left[id]) {++attempted;continue;}'),
]
for before,after in edits:
    assert text.count(before)==1, before
    text=text.replace(before,after,1)
if len(sys.argv)==4:
    extra=Path(sys.argv[3]).read_text()
    marker='void route_focus('
    assert extra.count(marker)==1
    extra=extra.replace(marker,'#include "focus-stems.inc"\n\n'+marker,1)
    marker='chosen=move(picked.route); attempts=picked.attempts;'
    assert extra.count(marker)==1
    extra=extra.replace(marker,marker+'\n            if(!has_route(chosen))chosen=try_legal_entries(original,board,wide);',1)
    Path('focus-route-stems.inc').write_text(extra)
    text=text.replace('#include "focus-route.inc"','#include "focus-route-stems.inc"',1)
Path(sys.argv[2]).write_text(text)
