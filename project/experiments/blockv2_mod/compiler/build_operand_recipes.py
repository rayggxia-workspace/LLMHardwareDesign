import json,sys
from pathlib import Path
from collections import Counter
from operand_recipes import lower
from value_layout import build
from verify_operand_recipes import verify
g=json.loads(Path(sys.argv[1]).read_text());layouts=build(g);result=lower(g,layouts)
proof=verify(g,result)
out=Path(sys.argv[2]);out.mkdir()
(out/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
(out/'operand-recipes.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'value-layout.json').write_text(json.dumps(layouts,indent=2)+'\n')
report={'source_tasks':len(g['tasks']),'lowered_tasks':len(result['tasks']),
        'tiles_by_kind':dict(Counter({kind:sum(len(t['tiles']) for t in result['tasks'] if t['kind']==kind) for kind in {t['kind'] for t in result['tasks']}})),
        'machine_package_complete':False}
assert [t['id'] for t in g['tasks']]==[t['id'] for t in result['tasks']]
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
