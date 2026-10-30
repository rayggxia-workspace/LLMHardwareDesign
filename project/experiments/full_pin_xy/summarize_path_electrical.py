"""Bounded-memory statistics of native OpenSTA JSON path observations.

Values in this JSON interface are SI seconds/farads, not the text report's ns/pF.
Only reported path points are observed; this is not all-net electrical coverage.
"""
from pathlib import Path
import argparse,hashlib,json,math

def checks(path):
    decoder=json.JSONDecoder()
    with Path(path).open() as f:
        buf='';eof=False
        while '[' not in buf:
            part=f.read(65536);assert part,'Missing checks array';buf+=part
        buf=buf.split('[',1)[1:][0]
        while True:
            buf=buf.lstrip(' \r\n\t,')
            if buf.startswith(']'):return
            try:obj,end=decoder.raw_decode(buf)
            except json.JSONDecodeError:
                part=f.read(262144)
                if not part:raise ValueError('Truncated native JSON: '+str(path))
                buf+=part;continue
            yield obj;buf=buf[end:]

def summarize(path):
    stats={k:{'observed_path_points':0,'capacitance_observations':0,'slew_observations':0,
       'maximum_observed_capacitance_F':None,'maximum_observed_slew_s':None} for k in ['data','source_clock','target_clock']}
    count=0
    for check in checks(path):
        count+=1
        for source,group in [('source_path','data'),('source_clock_path','source_clock'),('target_clock_path','target_clock')]:
            for point in check.get(source,[]):
                s=stats[group];s['observed_path_points']+=1
                for key,field in [('capacitance','maximum_observed_capacitance_F'),('slew','maximum_observed_slew_s')]:
                    if key not in point:continue
                    value=float(point[key]);assert math.isfinite(value)
                    s[key+'_observations']+=1
                    if s[field] is None or value>s[field]:s[field]=value;s[field+'_at_pin']=point.get('pin')
    return {'reported_checks':count,'path_observations':stats,
       'scope':'Maxima over native reported path-point observations, including repeated points; not complete all-net load/slew coverage, not a system qualification. Native JSON SI F/s; displayed values can be converted to fF/ps.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('json');p.add_argument('--out',required=True);a=p.parse_args();r=summarize(a.json)
    h=hashlib.sha256()
    with open(a.json,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    r['source']=a.json;r['sha256']=h.hexdigest();Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print('PATH_ELECTRICAL_OBSERVATIONS',r['reported_checks'])
