"""Namespace supplied physical/electrical cells without changing their contents.

Names match the cells in assemble_gds.py. Pin names, geometric coordinates and
all electrical values remain unchanged. The resulting source/target hashes
and mappings are recorded; this never changes a drive limit to pass timing.
"""
import argparse
import json
from pathlib import Path
import re
from native_inventory import sha


def generate(config,template,out):
    out.mkdir(parents=True);prefix='SRC_'+template+'_';views={'lefs':[],'liberties':[]};mapping={}
    for kind in ('lefs','liberties'):
        for i,ref in enumerate(config[kind]):
            source=Path(ref['path']);assert sha(source)==ref['sha256']
            raw=source.read_text()
            if kind=='lefs':
                names=re.findall(r'(?m)^MACRO\s+(\S+)',raw)
                if not names:continue # Global technology is loaded separately.
                for name in names:
                    raw=re.sub(r'(?m)^(MACRO\s+)'+re.escape(name)+r'(?=\s|$)',lambda m:m[1]+prefix+name,raw)
                    raw=re.sub(r'(?m)^(END\s+)'+re.escape(name)+r'(?=\s|$)',lambda m:m[1]+prefix+name,raw)
                    mapping[name]=prefix+name
            else:
                raw=re.sub(r'(\blibrary\s*\(\s*")([^"\n]+)("\s*\))',lambda m:m[1]+prefix+m[2]+m[3],raw)
                raw=re.sub(r'(\blibrary\s*\(\s*)([^\s"()]+)(\s*\))',lambda m:m[1]+prefix+m[2]+m[3],raw)
                raw=re.sub(r'(\bcell\s*\(\s*")([^"\n]+)("\s*\))',lambda m:m[1]+prefix+m[2]+m[3],raw)
                raw=re.sub(r'(\bcell\s*\(\s*)([^\s"()]+)(\s*\))',lambda m:m[1]+prefix+m[2]+m[3],raw)
            # OpenDB identifies a LEF library by the file basename, even when
            # its macros have distinct names. Keep those identities unique too.
            path=out/(prefix+str(i)+'-'+source.name);path.write_text(raw)
            views[kind].append({'path':str(path),'sha256':sha(path),'source':ref})
    result={'template':template,'master_aliases':mapping,'views':views,
            'modification':'cell/library identifiers only; all geometry and electrical values retained'}
    (out/'views.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path);p.add_argument('template');p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(generate(json.loads(a.config.read_text()),a.template,a.output)))
