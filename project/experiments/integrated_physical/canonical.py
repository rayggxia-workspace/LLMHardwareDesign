"""Independently re-export admitted map cut, then freeze actual Verilog cell names."""
import collections
from common import *

def canonical_cut(prepared,out):
 out.mkdir(exist_ok=False)
 raw=load(prepared/'cut-source.json')['modules']['chain93'];metadata={n:c for n,c in raw['cells'].items()if c['type']=='$scopeinfo'}
 need(len(metadata)==5,'exact93 five Yosys scope metadata objects')
 for n,c in metadata.items():need(c['connections']=={}and c['port_directions']=={}and c['parameters']=={'TYPE':'module'},'nonfunctional scope metadata only')
 ys=out/'independent-export.ys'
 ys.write_text(f'read_json {prepared}/cut-source.json\nwrite_verilog -noattr -noexpr {out}/cut-source.v\nhilomap -singleton -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\ncheck -assert\nwrite_json {out}/tied-raw.json\nwrite_verilog -noattr -noexpr {out}/cut.v\ndesign -reset\nread_liberty -lib {LIB}\nread_verilog {out}/cut.v\nhierarchy -top chain93\ncheck -assert\nwrite_json {out}/canonical.json\n')
 command(out,'independent-export',['yosys','-s',ys],300)
 for stem in('cut-source.v','cut.v'):need(sha(out/stem)==sha(prepared/stem),'exact independently reexported source bytes '+stem)
 need(load(out/'tied-raw.json')==load(prepared/'cut.json'),'all original raw tied cells/ports/nets exact')
 before=load(out/'canonical.json')['modules']['chain93'];tied=load(prepared/'cut.json')['modules']['chain93'];expected=collections.Counter(c['type']for c in tied['cells'].values()if c['type']!='$scopeinfo');actual=collections.Counter(c['type']for c in before['cells'].values());need(expected==actual,'no functional cell omitted by source export')
 put(out/'certificate.json',{'status':'PASS_ORIGINAL_MAP_CUT_REEXPORT_BYTES_AND_FUNCTIONAL_CELL_INVENTORY','raw_metadata_exclusions':metadata,'functional_cell_count':len(before['cells']),'canonical_json_sha256':sha(out/'canonical.json'),'reexport_sha256':{n:sha(out/n)for n in('cut-source.v','cut.v')},'method':'Source map cut is independently reconstructed by caller. Exact Yosys re-export byte check binds hidden-name canonicalization; only five empty $scopeinfo objects omitted. Subsequent pin/FF/port graph certificate uses actual exported names.'})
 return before
