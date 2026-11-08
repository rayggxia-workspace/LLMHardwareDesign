import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from def_assembly import assemble,sections,shift_pairs
from alias_views import generate


DEF='''VERSION 5.8 ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 100 100 ) ;
COMPONENTS 1 ;
- buffer BUF_X1 + PLACED ( 10 20 ) N ;
END COMPONENTS
PINS 2 ;
- out + NET out + DIRECTION OUTPUT + PORT + LAYER metal10 ( -2 -2 ) ( 2 2 ) + FIXED ( 20 20 ) N ;
- in + NET in + DIRECTION INPUT + PORT + LAYER metal10 ( -2 -2 ) ( 2 2 ) + FIXED ( 60 20 ) N ;
END PINS
NETS 2 ;
- out ( PIN out ) ( buffer Z ) + USE SIGNAL + ROUTED metal10 ( 10 20 ) ( 20 * ) ;
- in ( PIN in ) ( buffer A ) + USE SIGNAL + ROUTED metal10 ( 60 20 ) ( 70 * ) ;
END NETS
END DESIGN
'''


class DefTest(unittest.TestCase):
    def test_physical_port_metal_survives_internalization(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=p/'native.def';source.write_text(DEF)
            inv={'files':{'native/6_final.def':{'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}},
                 'terms':{n:{'native_net':n,'shapes':[{'layer':'metal10','rect':r}]} for n,r in [('out',[18,18,22,22]),('in',[58,18,62,22])]}}
            library={'v':{'views':{'odb':{'path':str(p/'native.odb')}},'inventory':inv}}
            base={'dbu_per_micron':2000,'bounds_dbu':[0,0,300,100],
                  'assemblies':[{'id':g,'template':'v','translation_dbu':[x,0]} for g,x in [('first',0),('second',200)]],
                  'endpoints':{'first/out':{'native_net':'first/out'},'second/in':{'native_net':'second/in'}}}
            binding={'nets':{'n000':{'driver':'first/out','sinks':['second/in']}}}
            upper='NETS 1 ;\n- n000 ( PIN a ) ( PIN b ) + USE SIGNAL + ROUTED metal11 ( 20 20 ) ( 260 20 ) ;\nEND NETS\n'
            result=assemble(base,library,binding,upper,p/'out')
            raw=(p/'out/assembled.def').read_text();part=sections(raw)
            self.assertEqual(len(part['COMPONENTS']),2);self.assertEqual(len(part['PINS']),2)
            self.assertIn('second/buffer SRC_v_BUF_X1 + PLACED ( 210 20 ) N',raw)
            joined=next(r for r in part['NETS'] if r.split()[1]=='UPPER_n000')
            self.assertIn('( first/buffer Z )',joined);self.assertIn('( second/buffer A )',joined)
            self.assertIn('( 20 20 ) RECT ( -2 -2 2 2 )',joined)
            self.assertIn('( 260 20 ) RECT ( -2 -2 2 2 )',joined)
            self.assertNotIn('PIN first/out',joined)
            self.assertLess(joined.index('( second/buffer A )'),joined.index('+ ROUTED'))
            self.assertEqual(joined.count('+ ROUTED'),1)
            self.assertEqual(shift_pairs('( 1 * ) ( * 2 0 )',10,20),'( 11 * ) ( * 22 0 )')

    def test_namespaced_views_preserve_geometry_and_electrical_values(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);lef=p/'cell.lef';lib=p/'cell.lib'
            lef.write_text('MACRO BUF_X1\n SIZE 1 BY 2 ;\n PIN A\n END A\nEND BUF_X1\n')
            lib.write_text('library ("original") { cell (BUF_X1) { max_capacitance : 17.5; pin (A) { capacitance : 1.1; } } }\n')
            ref=lambda p:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            result=generate({'lefs':[ref(lef)],'liberties':[ref(lib)]},'resource',p/'alias')
            newlef=Path(result['views']['lefs'][0]['path']).read_text()
            newlib=Path(result['views']['liberties'][0]['path']).read_text()
            self.assertIn('MACRO SRC_resource_BUF_X1',newlef);self.assertIn('END SRC_resource_BUF_X1',newlef)
            self.assertIn('cell (SRC_resource_BUF_X1)',newlib);self.assertIn('max_capacitance : 17.5',newlib)
            self.assertIn('pin (A) { capacitance : 1.1;',newlib)


if __name__=='__main__':unittest.main()
