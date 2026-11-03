from pathlib import Path
import sys,tempfile,json,gzip,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fixed_clock_routes import audit,canonical_net,canonical_cell,records
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='r166-clock-audit-')as tmp:
 d=Path(tmp);p=d/'actual.def'
 text='''VERSION 5.8 ;
DESIGN r_stream_local ;
COMPONENTS 2 ;
- FF DFF_X1 + FIXED ( 10 20 ) N ;
- BUF BUF_X8 + FIXED ( 30 20 ) N ;
END COMPONENTS
NETS 2 ;
- clk ( PIN clk ) ( BUF A ) + USE CLOCK + FIXED metal1 ( 0 20 ) ( 30 20 ) ;
- leaf ( BUF Z ) ( FF CK ) + USE CLOCK + FIXED metal1 ( 30 20 ) ( 10 20 ) ;
END NETS
END DESIGN
''';p.write_text(text)
 nets=records(p,'NETS',{'clk','leaf'});cells=records(p,'COMPONENTS',{'FF','BUF'})
 baseline=dict(nets={n:canonical_net(r,'FIXED')[0]for n,r in nets.items()},cells={n:canonical_cell(r,True)for n,r in cells.items()},native_cells={n:n for n in cells})
 (d/'CLOCK_BASELINE.json.gz').write_bytes(gzip.compress(json.dumps(baseline).encode(),mtime=0));(d/'CLOCK_FIXED.def').write_text('exact overlay');(d/'CLOCK_LOCKED_CELLS.tsv').write_text('FF\nBUF\n')
 (d/'CLOCK_NATIVE_NAMES.tsv').write_text('FF\nBUF\n');(d/'clock_source_names.tcl').write_text('actual source inventory fixture')
 binding=dict(qualification_transferred=False,baseline_sha256=sha(d/'CLOCK_BASELINE.json.gz'),overlay_sha256=sha(d/'CLOCK_FIXED.def'),native_names_sha256=sha(d/'CLOCK_NATIVE_NAMES.tsv'),native_names_script_sha256=sha(d/'clock_source_names.tcl'));(d/'CLOCK_ROUTE_BINDING.json').write_text(json.dumps(binding))
 audit(d,p,'final')
 # Unordered complete terminal records remain equal; geometry stays exact.
 p.write_text(text.replace('( BUF Z ) ( FF CK )','( FF CK ) ( BUF Z )'));audit(d,p,'after-detail')
 p.write_text(text.replace('+ FIXED metal1','+ ROUTED metal1'));audit(d,p,'before-detail')
 mutants=[text.replace('( 0 20 )','( 1 20 )'),text.replace('( FF CK )','( FF D )'),text.replace('FF DFF_X1','FF DFF_X2'),text.replace('( 10 20 ) N','( 12 20 ) N'),text.replace('+ FIXED metal1','+ ROUTED metal1')]
 for i,mutant in enumerate(mutants):
  p.write_text(mutant)
  try:audit(d,p,'final')
  except AssertionError:pass
  else:raise AssertionError(('Clock mutation accepted',i))
 print('PASS: 3 positive native DEF cases and 5 real route/connection/master/position/flag negative controls')
