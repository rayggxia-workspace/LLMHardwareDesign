"""Diagnose actual blocked search endpoints; no routing/DRC feasibility claim."""
import argparse,csv,gzip,hashlib,io,json
from pathlib import Path
from plan_upper_local_bypass import HALF,STEP,METAL_SPACE,CUT_SPACE,rect,gap,contains,box_wire

def audit(capture,out):
    capture=Path(capture);index=json.loads((capture/'capture.json').read_text(encoding='utf-8'))
    def raw(name):
        meta=next(r for r in index['records'] if r['name']==name)
        stored=(capture/(name+'.gz')).read_bytes();assert hashlib.sha256(stored).hexdigest()==meta['stored_sha256']
        data=gzip.decompress(stored);assert hashlib.sha256(data).hexdigest()==meta['sha256']
        return data
    rows=list(csv.DictReader(io.StringIO(gzip.decompress(raw('branch_access.tsv.gz')).decode()),delimiter='\t'))
    obs=[]
    for line in raw('after_branch.OBS.tsv').decode().splitlines():
        p=line.split();assert len(p)==5
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    results=[]
    for net,marker in [('src[248]',(4876190,5285740,4877790,5287340)),('src[206]',(4930590,5276140,4932190,5277740))]:
        hits=[r for r in rows if r['net']==net and r['kind']=='WIRE' and r['layer']=='metal11' and contains(rect(r),marker)];assert len(hits)==1
        original=hits[0];z=rect(original);a,b=(z[0]+HALF,z[1]+HALF),(z[2]-HALF,z[3]-HALF)
        item={'net':net,'original_wire':original,'endpoints':[]}
        for label,p in [('start',a),('end',b)]:
            square=box_wire(p,p);endpoint={'name':label,'center_DBU':list(p),'same_net_incident_exported_material':[],'immediate_moves':[]}
            for r in rows:
                if r['net']==net and r['kind'] in ['WIRE','VIA'] and contains(rect(r),(p[0],p[1],p[0],p[1])):endpoint['same_net_incident_exported_material'].append(r)
            for layer in [11,12]:
                for dx,dy in [(0,0),(STEP,0),(-STEP,0),(0,STEP),(0,-STEP)]:
                    wire=box_wire(p,(p[0]+dx,p[1]+dy));blocked=[]
                    for r in rows+obs:
                        if r['net']==net or r['layer']!='metal'+str(layer) or r['kind'] not in ['WIRE','VIA','OBS']:continue
                        z=rect(r);spacing=3000 if min(z[2]-z[0],z[3]-z[1])>=1800 else METAL_SPACE
                        distance=gap(wire,z)
                        if distance<spacing:blocked.append(dict(r,actual_square_gap_DBU=distance,screen_spacing_DBU=spacing))
                    endpoint['immediate_moves'].append({'layer':layer,'delta_DBU':[dx,dy],'metal_blockers':blocked})
            item['endpoints'].append(endpoint)
        results.append(item)
    result={'scope':'ACTUAL_EXPORTED_M11_M12_ENDPOINT_BLOCKERS_ONLY_NOT_NATIVE_DRC_OR_INFEASIBILITY_PROOF','full_qualification':False,'source_capture':index['source'],'source_receipt_SHA256':hashlib.sha256(raw('execution.json')).hexdigest(),'source_exported_branch_SHA256':hashlib.sha256(raw('branch_access.tsv.gz')).hexdigest(),'source_OBS_SHA256':hashlib.sha256(raw('after_branch.OBS.tsv')).hexdigest(),'DBU_per_um':2000,'grid_pitch_DBU':STEP,'screening_metal_spacing_DBU':METAL_SPACE,'wide_metal_spacing_DBU':3000,'RECT_patch_coverage':'NOT_YET_AUDITED','native_implementation':'NOT_EXECUTED','cut11_rule_not_evaluated_by_this_endpoint_metal_audit':True,'nets':results}
    out=Path(out);assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for n in results:
        print(n['net'],[(e['name'],e['center_DBU'],[(m['layer'],m['delta_DBU'],len(m['metal_blockers'])) for m in e['immediate_moves']]) for e in n['endpoints']])
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--capture',required=True);p.add_argument('--out',required=True);a=p.parse_args();audit(a.capture,a.out)
