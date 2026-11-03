"""Materialized fixed-pin geometry exercises the upstream corner-cache path."""
from pathlib import Path
import hashlib,json,shutil,subprocess

def definitions(out):
 lef=out/'fixed-control.lef'
 lef.write_text('''VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
MACRO R166_GC_FIXED
 CLASS CORE ;
 ORIGIN 0 0 ;
 SIZE 4 BY 4 ;
 PIN P
  DIRECTION OUTPUT ;
  USE SIGNAL ;
  PORT
   LAYER metal2 ;
   RECT 1 1 1.2 3 ;
  END
 END P
 PIN Q
  DIRECTION OUTPUT ;
  USE SIGNAL ;
  PORT
   LAYER metal2 ;
   RECT 2 1 2.2 3 ;
  END
 END Q
END R166_GC_FIXED
END LIBRARY
''')
 base='''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN r166_fixed_control ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 20000 20000 ) ;
GCELLGRID X 0 DO 2 STEP 20000 ;
GCELLGRID Y 0 DO 2 STEP 20000 ;
COMPONENTS 2 ;
- u0 R166_GC_FIXED + FIXED ( 0 0 ) N ;
- u1 R166_GC_FIXED + FIXED ( 8000 0 ) N ;
END COMPONENTS
NETS 2 ;
- a ( u0 P ) ( u1 P ) ;
- b ( u0 Q ) ( u1 Q ) ROUTE ;
END NETS
END DESIGN
'''
 return lef,{'fixed_positive':(base.replace(' ROUTE',''),None),'fixed_short':(base.replace('ROUTE','+ USE SIGNAL + ROUTED metal2 ( 2200 1000 ) ( 2200 7000 )'),'Short')}

if __name__=='__main__':
 out=Path.cwd()/'fixed-controls';out.mkdir(exist_ok=False);lef,fixtures=definitions(out)
 tech='/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef';rows={}
 for name,(definition,expected)in fixtures.items():
  (out/(name+'.def')).write_text(definition)
  script=out/(name+'.tcl');script.write_text('set_thread_count 16\nread_lef {'+tech+'}\nread_lef {'+str(lef)+'}\nread_def {'+str(out/(name+'.def'))+'}\ndrt::check_drc_cmd '+name+'.rpt 0 0 0 0 '+name+'\n')
  with(out/(name+'.log')).open('w')as f:subprocess.run(['openroad','-no_init','-exit',str(script)],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
  text=(out/(name+'.rpt')).read_text();assert (not text.strip())if expected is None else('violation type: '+expected)in text
  rows[name]=dict(passed=True,expected=expected,report_sha256=hashlib.sha256((out/(name+'.rpt')).read_bytes()).hexdigest())
 (out/'receipt.json').write_text(json.dumps(dict(passed=True,controls=rows,scope='Actual fixed LEF pins, two pins per net/layer; positive and foreign routing short, original checker. No hardware qualification.'),indent=2)+'\n')
