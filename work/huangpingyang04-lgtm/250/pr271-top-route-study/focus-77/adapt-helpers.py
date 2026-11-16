"""Point the existing transactional, mix and diagnosis runners at this layout."""
from pathlib import Path


def replace(path, changes):
    p=Path(path); text=p.read_text()
    for before,after in changes:
        assert text.count(before)==1,(path,before)
        text=text.replace(before,after,1)
    p.write_text(text)


for name in ('run-scarce-group.sh','run-mix.sh','run-diagnose.sh','run-last.sh','classify.py','run-group.sh'):
    p=Path(name); text=p.read_text()
    assert 'precheck-final' in text
    p.write_text(text.replace('precheck-final','focus-layout'))

replace('run-scarce-group.sh',[
    ('GROUP_PROBES="$probes/path-options.tsv"', 'GROUP_PROBES="$seed/path-options.tsv" FOCUS_TARGETS="$probes/targets.tsv"'),
    ('cp "$input/graph.txt" .','cp "$input/graph.txt" "$GROUP_PROBES" .'),
])
replace('group-priority.inc',[
    ('    auto rank=[&](int id) {',
     '    vector<bool> focus(nets.size());\n'
     '    ifstream priority(getenv("FOCUS_TARGETS"));\n'
     '    int kind; size_t records=0;\n'
     '    while(priority>>i>>pin>>kind){ focus.at(i)=true; ++records; }\n'
     '    if(!priority.eof()||records!=77)throw runtime_error("Bad focus targets in group pass");\n'
     '    auto rank=[&](int id) {'),
    ('return make_tuple(fewest[id],cover,tiebreak,id);','return make_tuple(!focus[id],fewest[id],cover,tiebreak,id);'),
])
replace('run-mix.sh',[
    ('clean-*.log|group-*.log', 'focus-a-*.log|focus-b-*.log|focus-c-*.log|group-*.log'),
])
