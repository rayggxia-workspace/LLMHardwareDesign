"""Report-bound relocation controls; no physical qualification is implied."""
import copy
import json
from pathlib import Path
import re
import sys
from native_escape_relocate import relocate
from native_escape_audit import upper_shorts


def main(source,destination):
    assert not destination.exists()
    a=next(r for r in json.loads(source.read_text())['run157']if r['policy']=='a')
    plans={}
    for name in ['write_data[54]','write_data[55]']:
        pin=tuple(map(int,re.search(r'\+ FIXED \( (\d+) (\d+) \)',a['pins'][name]).groups()))
        text,plan=relocate(a['nets'][name],pin,(pin[0],pin[1]+160)if name=='write_data[54]'else pin)
        assert text!=a['nets'][name];plans[name]=plan
    rejected=[]
    name='write_data[54]';text=a['nets'][name];pin=(3390,1961740)
    for label,bad in [('missing-via8',text.replace('via8_0','via7_0')),
                      ('multiple-via9',text.replace('NEW metal8 ( 3390 1964940 ) via8_0','NEW metal9 ( 3390 1964940 ) via9_0'))]:
        try:relocate(bad,pin,(3390,1961900))
        except (AssertionError,ValueError):rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    for label,rows in [('metal-touch',{'a':[('metal10','wire',(0,0,10,10))],'b':[('metal10','wire',(10,0,20,10))]}),
                       ('cross-layer-cut',{'a':[('via9','wire-via',(0,0,10,10))],'b':[('metal10','wire',(5,5,20,20))]})]:
        assert not upper_shorts(rows)['passed'];rejected.append(label)
    assert upper_shorts({'a':[('metal9','wire',(0,0,10,10))],'b':[('metal10','wire',(0,0,10,10))]})['passed']
    destination.write_text(json.dumps(dict(passed=True,plans=plans,rejected=rejected,scope='Actual route syntax and unchanged-lower-stack controls plus synthetic complete upper audit; no EDA qualification'),indent=2)+'\n')


if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
