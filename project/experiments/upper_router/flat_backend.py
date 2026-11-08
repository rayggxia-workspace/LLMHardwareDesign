"""Prepare one flat placed/routed OpenDB without composite Block hard macros."""
import argparse
import json
from pathlib import Path
from alias_views import generate
from def_assembly import assemble
from native_inventory import sha
from resource_base import load_library


def prepare(base,library,binding,upper_def,configs,technology,vias,out):
    out.mkdir();physical=out/'physical'
    proof=assemble(base,library,binding,Path(upper_def).read_text(),physical)
    aliased={}
    for template,config in sorted(configs.items()):aliased[template]=generate(config,template,out/'views'/template)
    owners=set()
    for name,net in binding['nets'].items():
        for endpoint in [net['driver']]+net['sinks']:
            group,local=endpoint.split('/',1)
            assembly=next(a for a in base['assemblies'] if a['id']==group)
            resource=library[assembly['template']];p=resource['inventory']['terms'][local]
            for kind,direction in [('drivers','OUTPUT'),('sinks','INPUT')]:
                for owner in p[kind]:
                    owners.add(('UPPER_'+name,direction,group+'/'+owner['instance'],
                                'SRC_'+assembly['template']+'_'+owner['master'],owner['pin']))
    (out/'expected-owners.tsv').write_text(''.join('\t'.join(r)+'\n' for r in sorted(owners)))
    tcl=['read_lef {'+str(technology)+'}','read_lef {'+str(vias)+'}']
    for template,views in sorted(aliased.items()):
        for ref in views['views']['lefs']:tcl.append('read_lef {'+ref['path']+'}')
        for ref in views['views']['liberties']:tcl.append('read_liberty {'+ref['path']+'}')
    tcl+=['read_def {'+str(physical/'assembled.def')+'}',
          'set block [ord::get_db_block]',
          'if {[llength [$block getInsts]] != '+str(proof['counts']['COMPONENTS'])+'} {error "native component count changed"}',
          'write_db {'+str(out/'assembled.odb')+'}',
          'set physical_cells {}',
          'foreach lib [[ord::get_db] getLibs] { foreach master [$lib getMasters] {',
          'set signal 0; foreach term [$master getMTerms] { if {[$term getSigType] ni {POWER GROUND}} {set signal 1} }',
          'if {!$signal} {lappend physical_cells [$master getName]}',
          '} }',
          'write_verilog -remove_cells $physical_cells {'+str(out/'assembled.v')+'}']
    (out/'ingest.tcl').write_text('\n'.join(tcl)+'\n')
    (out/'views.json').write_text(json.dumps(aliased,indent=2)+'\n')
    (out/'source-proof.json').write_text(json.dumps({'base':base,'definition':proof,
         'technology':{'path':str(technology),'sha256':sha(technology)},
         'upper_vias':{'path':str(vias),'sha256':sha(vias)}},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','library','binding','upper_def','configs','technology','vias','output'):p.add_argument(n,type=Path)
    a=p.parse_args();read=lambda p:json.loads(p.read_text())
    prepare(read(a.base),load_library(a.library),read(a.binding),a.upper_def,read(a.configs),a.technology,a.vias,a.output)
