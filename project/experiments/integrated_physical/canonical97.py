"""Independently re-export admitted map cut, then freeze actual Verilog cell names."""
import collections,copy,sys
from common import *
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import library,certificate

def canonical_cut(prepared,out):
 out.mkdir(exist_ok=False)
 raw=load(prepared/'cut-source.json')['modules']['chain97'];metadata={n:c for n,c in raw['cells'].items()if c['type']=='$scopeinfo'}
 need(len(metadata)==6,'exact97 six Yosys scope metadata objects')
 for n,c in metadata.items():need(c['connections']=={}and c['port_directions']=={}and c['parameters']=={'TYPE':'module'},'nonfunctional scope metadata only')
 ys=out/'independent-export.ys'
 ys.write_text(f'read_json {prepared}/cut-source.json\nwrite_verilog -noattr -noexpr {out}/cut-source.v\nhilomap -singleton -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\ncheck -assert\nwrite_json {out}/tied-raw.json\nwrite_verilog -noattr -noexpr {out}/cut.v\ndesign -reset\nread_liberty -lib {LIB}\nread_verilog {out}/cut.v\nhierarchy -top chain97\ncheck -assert\nwrite_json {out}/canonical.json\n')
 command(out,'independent-export',['yosys','-s',ys],300)
 for stem in('cut-source.v','cut.v'):need(sha(out/stem)==sha(prepared/stem),'exact independently reexported source bytes '+stem)
 base=copy.deepcopy(raw);lib=library(LIB)
 for n in metadata:del base['cells'][n]
 tie_certificates={}
 for label,path in [('producer',prepared/'cut.json'),('independent',out/'tied-raw.json')]:
  tied_raw=load(path)['modules']['chain97']
  for n,c in metadata.items():need(tied_raw['cells'].pop(n)==c,'metadata unchanged')
  tie_certificates[label]=certificate(base,tied_raw,lib)
  need(tie_certificates[label]['added_histogram']=={'LOGIC0_X1':1,'LOGIC1_X1':1},'exact two explicitly costed tie cells')
 put(out/'tie-certificates.json',tie_certificates)
 before=load(out/'canonical.json')['modules']['chain97'];tied=load(prepared/'cut.json')['modules']['chain97'];expected=collections.Counter(c['type']for c in tied['cells'].values()if c['type']!='$scopeinfo');actual=collections.Counter(c['type']for c in before['cells'].values());need(expected==actual,'no functional cell omitted by source export')
 put(out/'certificate.json',{'status':'PASS_ORIGINAL_MAP_CUT_REEXPORT_BYTES_AND_FUNCTIONAL_CELL_INVENTORY','raw_metadata_exclusions':metadata,'functional_cell_count':len(before['cells']),'canonical_json_sha256':sha(out/'canonical.json'),'reexport_sha256':{n:sha(out/n)for n in('cut-source.v','cut.v')},'method':'Source map cut is independently reconstructed by caller. Exact Yosys re-export byte check binds hidden-name canonicalization; only six empty $scopeinfo objects omitted. Subsequent pin/FF/port graph certificate uses actual exported names.'})
 return before
