"""Matched standard-cell mapping; deliberately excludes placement/clock claims."""
from collections import Counter
import json,re,shutil
from pathlib import Path
from prepare import sha

LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
LIB_SHA='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
def q(p):return '"'+str(p)+'"'
def area(repo,out,execute):
    assert sha(LIB)==LIB_SHA,'library drift'
    out.mkdir(exist_ok=False)
    yosys=Path(shutil.which('yosys')).resolve();abc=yosys.with_name('yosys-abc')
    assert abc.is_file(),'explicit ABC missing'
    allowed={a or b for a,b in re.findall(r'\bcell\s*\(\s*(?:"([^"]+)"|([^\s)]+))\s*\)',LIB.read_text())}
    receipt=dict(status='running',scope='E frontends, E cores and region sequencer; no SRAM/arbiter/N core/U glue/STA/P&R',
        library_sha256=LIB_SHA,tools={'yosys':sha(yosys),'abc':sha(abc)},modules={})
    versions={'yosys':execute([yosys,'-V'],'area/yosys-version.log',30).strip()}
    for key,top,source,param in [
        ('front_serial','pu_compact_e_service','project/rtl/pu_leaf_base/pu_compact_e_service.sv',None),
        ('front_q2','pu_queued_e_service','project/rtl/pu_leaf_base/pu_queued_e_service.sv',2),
        ('front_q4','pu_queued_e_service','project/rtl/pu_leaf_base/pu_queued_e_service.sv',4),
        ('e_legacy','block_v2_e','project/rtl/block_v2/block_v2_e.sv',None),
        ('e_pipeline','block_v2_e_pipeline','project/rtl/block_v2/block_v2_e_pipeline.sv',None),
        ('region','pu_nexp_region','project/rtl/pu_leaf_base/pu_nexp_region.sv',None)]:
        dest=out/key;dest.mkdir();flow=dest/'synth.ys'
        lines=['read_liberty -lib '+q(LIB),'read_verilog -sv '+q(repo/source)]
        if param is not None:lines+=['chparam -set DEPTH '+str(param)+' '+top]
        lines+=['hierarchy -check -top '+top,'synth -top '+top+' -flatten -noabc',
            'dfflibmap -liberty '+q(LIB),'abc -exe '+q(abc)+' -liberty '+q(LIB),'clean','check -assert',
            'tee -o '+q(dest/'stat.json')+' stat -json -liberty '+q(LIB),
            'write_json '+q(dest/'mapped.json'),'write_verilog -noattr '+q(dest/'mapped.v')]
        flow.write_text('\n'.join(lines)+'\n',encoding='utf8')
        execute([yosys,'-Q','-s',flow],'area/'+key+'/synthesis.log',1200)
        stats=json.loads((dest/'stat.json').read_bytes());match=[v for k,v in stats['modules'].items() if k.lstrip('\\')==top]
        assert len(match)==1,'missing unique top'
        mapped=json.loads((dest/'mapped.json').read_bytes())['modules'][top]
        counts=Counter(c['type'] for c in mapped['cells'].values())
        assert not set(counts)-allowed-{'$scopeinfo'},'unmapped cells'
        value=match[0].get('area',stats.get('design',{}).get('area'))
        assert isinstance(value,(int,float)) and value>0,'invalid area'
        receipt['modules'][key]=dict(standard_cell_um2=value,cells=dict(counts),source_sha256=sha(repo/source),SRAM_macros=0)
    receipt.update(status='passed',versions=versions)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');return receipt
