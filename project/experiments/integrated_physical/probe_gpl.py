"""Capture actual installed Tcl bodies where advertised help differs from parser."""
import argparse
from common import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'source':sources(),'resources':resource_snapshot()};s=a.out/'probe.tcl';s.write_text(tcl_script(['puts "BEGIN_GPL_BODY"','puts [info body global_placement]','puts "END_GPL_BODY"','puts "BEGIN_PPL_BODY"','puts [info body place_pins]','puts "END_PPL_BODY"']));command(a.out,'probe',[OR,'-exit',s],120);m['status']='ACTUAL_INSTALLED_TCL_CAPTURED';manifest(a.out,m)
