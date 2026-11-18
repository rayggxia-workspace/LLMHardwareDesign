"""Patch only document.xml in a copy of the accepted DAC combined table."""
from pathlib import Path
from hashlib import sha256
import json,zipfile
from lxml import etree
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]
SRC=REPO/'output/docx/seven-model-dac-combined-table.docx'
OUT=REPO/'output/docx/seven-model-200mhz-dac-table.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def main():
    assert sha256(SRC.read_bytes()).hexdigest()=='cbcb2d94925054f2a0b7a0398222896056f033d91dfed7176f43d45ac3e61167'
    data=json.loads((ROOT/'results-200mhz.json').read_text(encoding='utf8'))
    assert not data['missing_models'] and len(data['models'])==7
    z=zipfile.ZipFile(SRC);xml=etree.fromstring(z.read('word/document.xml'))
    rows=xml.xpath('//w:tbl/w:tr',namespaces=NS);assert len(rows)==5
    expected=[]
    for i,r in enumerate(data['models']):
        for j,phase in enumerate(('prefill','decode')):
            col=1+2*i+j
            values=['{:.3f}'.format(r['speed']['estimated_input_tok_s_to_logits' if phase=='prefill' else 'decode_tok_s'])]+['{:.4f}'.format(r['windows'][phase]['scopes'][s]['energy_j_per_token'][0]) for s in ('on_chip','on_chip_plus_ddr')]
            for ri,value in enumerate(values,2):
                ts=rows[ri].findall('w:tc',NS)[col].xpath('.//w:t',namespaces=NS)
                ts[0].text=value
                for t in ts[1:]:t.text=''
                expected.append(value)
    for t in xml.xpath('//w:body/w:p//w:t',namespaces=NS):
        if t.text and 'Seven-Model Throughput' in t.text:t.text='Seven-Model Estimated Throughput and Covered Energy at 200 MHz'
        elif t.text and t.text.startswith('* Prefill throughput'):
            t.text='* Core: 200 MHz; DDR period: 630 ps. Throughput is estimated from paired 300/200 MHz representative-layer replays. Prefill uses 512 input tokens with one final output head; decode uses the retirement-to-retirement window after 512 positions of history. Full-window and full-512-token prediction errors remain unvalidated.'
        elif t.text and t.text.startswith('All energy values'):
            t.text='Energy values are the lower calibration endpoints after frequency and residency reintegration using the original netlists. Both scopes are covered subtotals; read DMA, uncalibrated arithmetic, remaining control/clock/interconnect, DDR PHY and board energy are excluded. Wire parasitics are omitted.'
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():out.writestr(item,etree.tostring(xml,encoding='UTF-8',xml_declaration=True,standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
    new=zipfile.ZipFile(OUT)
    assert all(z.read(n)==new.read(n) for n in z.namelist() if n!='word/document.xml')
    (ROOT/'word-table-checks.json').write_text(json.dumps({'source_sha256':sha256(SRC.read_bytes()).hexdigest(),'output_sha256':sha256(OUT.read_bytes()).hexdigest(),'expected_numeric_cells':expected,'unmodified_package_parts_verified':True},indent=2))
    print(OUT)
if __name__=='__main__':main()
