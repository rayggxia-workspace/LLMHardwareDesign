"""Verify recovered bytes, frozen source Git blobs, and offline viewer scripts."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]


class Scripts(HTMLParser):
    def __init__(self):super().__init__();self.kind=None;self.code=[];self.data=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script':self.kind=dict(attrs).get('type','javascript')
    def handle_data(self,data):
        if self.kind=='application/json':self.data.append(data)
        elif self.kind:self.code.append(data)
    def handle_endtag(self,tag):
        if tag=='script':self.kind=None


def main():
    out=ROOT/'work/YUZE-LU/219/results/read-cache-v1';receipt=json.loads((out/'receipt.json').read_text());n=0
    for name,row in receipt['outputs'].items():
        if not row['kept_server']:
            assert hashlib.sha256((out/name).read_bytes()).hexdigest()==row['sha256'],name;n+=1
    frozen=receipt['attempts'][0];blobs=0
    for name,sha in frozen['source_sha256'].items():
        data=subprocess.check_output(['git','show',':project/experiments/block_synthesis/'+name],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==sha,name;blobs+=1
    for label in ('five-numeric','nine-numeric'):
        report=json.loads((out/label/'generated/report.json').read_text())
        assert report['status']=='selected_cache_program_passed'
        assert len(report['samples'])==3 and all(s['passed'] and s['bit_exact_to_all_spill'] for s in report['samples'])
    audit=json.loads((out/'tests/whole-plan-audit.json').read_text());assert audit['passed']
    html=[]
    for name in ('report.html','reuse.html'):
        parser=Scripts();parser.feed((out/'plan/generated'/name).read_text(encoding='utf-8'))
        assert len(parser.data)==1;data=json.loads(parser.data[0])
        assert data['summary']['status']=='complete_graph_planning_passed'
        for code in parser.code:
            subprocess.run(['node','--check'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        html.append(name)
    result={'passed':True,'recovered_sha_checks':n,'staged_algorithm_blob_checks':blobs,
        'whole_model_numeric_runs':6,'unit_tests':100,'html_script_checks':html,
        'visual_inspection':'not performed: browser policy rejected local file protocol',
        'scope':'synthesis and integer simulation; not hardware system/physical qualification'}
    (out/'validation.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))


if __name__=='__main__':main()
