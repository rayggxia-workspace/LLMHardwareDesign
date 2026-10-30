"""All13507 current actual ports: measured first-hop metal/cut risk inventory.

Read only, complete actual signal export plus native PG/OBS. No candidate
replacement, native DRC, parent AP or manufacturing qualification is claimed.
Spatially indexed points avoid repeating a huge scan for each failing port.
"""
from pathlib import Path
from collections import defaultdict,Counter
from bisect import bisect_left,bisect_right
import csv,datetime,gzip,json,math,os,re,sys,traceback
from run_exports import ROOT,sha
DRIVER=Path(__file__).resolve().parent

def run(revision):
    source=ROOT/'llsys_wire_pin_retention/r01';q=json.loads((source/'execution.json').read_text());assert q.get('completed_utc') and q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and q['all_closed_sources_unchanged']
    geo=source/'whole_access.tsv.gz';pins=source/'after.pins.tsv';odb=source/'routed.odb'
    for p in [geo,pins,odb]:assert sha(p)==q['files'][p.name]['sha256']
    native=ROOT/'llsys_residual_access_preflight/r01';n=json.loads((native/'execution.json').read_text());assert n.get('completed_utc') and n['native_readonly_returncode']==0 and n['all_closed_sources_unchanged'] and n['source_SHA'][str(odb)]==sha(odb)
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text());assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
    files=[source/'execution.json',geo,pins,odb,native/'execution.json',native/'actual_first_hop_vias.tsv',native/'actual_high_PG_OBS.tsv',tech]
    for p in files:
        if p.parent==native and p.name!='execution.json':assert sha(p)==n['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in files};out=ROOT/'all_llsys_first_hop_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ALL13507_REAL_FIRST_HOP_GEOMETRIC_RISK_READONLY_NOT_PARENT_AP_OR_FULL_DRC',
      'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'full_qualification':False,'actual_edit_route_RC_STA':'NOT_EXECUTED_READONLY','not_checked':['Entire access stack','End-of-line, enclosure and complete rule interactions','Parent OBS ownership and native AP','Full GDS rules and manufacturing qualification']}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    try:
        vias=defaultdict(dict)
        for r in csv.DictReader((native/'actual_first_hop_vias.tsv').open(),delimiter='\t'):vias[r['via']][r['layer']]=tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
        text=tech.read_text();rules={};maxgrow={}
        for layer in ['metal5','metal6','metal7','via5','via6']:
            block=re.search(r'^LAYER '+layer+r'\s.*?^END '+layer,text,re.M|re.S)[0]
            if layer.startswith('via'):rules[layer]=round(float(re.search(r'\bSPACING\s+([\d.]+)',block)[1])*2000);maxgrow[layer]=rules[layer]+400;continue
            table=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',block,re.S)[1].splitlines();prls=[round(float(x)*2000) for x in table[0].split()];rows=[]
            for line in table[1:]:
                p=line.split()
                if p and p[0]=='WIDTH':rows.append((round(float(p[1])*2000),[round(float(x)*2000) for x in p[2:]]))
            assert rows and all(len(v)==len(prls) for w,v in rows);rules[layer]=(prls,rows);maxgrow[layer]=max(max(v) for w,v in rows)+400
        def spacing(layer,a,b):
            if layer.startswith('via'):return rules[layer]
            width=max(min(a[2]-a[0],a[3]-a[1]),min(b[2]-b[0],b[3]-b[1]));dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
            prl=max(0,min(a[3],b[3])-max(a[1],b[1])) if dx and not dy else max(0,min(a[2],b[2])-max(a[0],b[0])) if dy and not dx else 0
            ps,rs=rules[layer];i=max(i for i,v in enumerate(ps) if v<=prl);return max((r for r in rs if r[0]<=width),key=lambda r:r[0])[1][i]
        ports=[];grid=defaultdict(list);BIN=64000
        for line in pins.open():
            p=line.split()
            if len(p)!=9 or p[2] in ['POWER','GROUND']:continue
            name,net=p[0].strip('{}'),p[3].strip('{}');layer=p[4];box=list(map(int,p[5:]));assert box[2]-box[0]==box[3]-box[1]==280 and layer in ['metal5','metal6']
            x,y=(box[0]+box[2])//2,(box[1]+box[3])//2;via='via5_0' if layer=='metal5' else 'via6_0'
            record={'pin':name,'net':net,'direction':p[1],'original_layer':layer,'box_DBU':box,'center_DBU':[x,y],'first_hop':via,'foreign_or_cut_spacing_risks':0,'examples':[],'own_next_layer_metal_intersections':0,'own_exact_first_hop_cut_present':0,'on_M6_X_grid':(x-190)%560==0,'on_first_hop_Y_grid':(y-140)%(560 if layer=='metal5' else 1600)==0}
            index=len(ports);ports.append(record)
            for ly,z in vias[via].items():grid[ly,x//BIN].append((y,index,tuple(v+x if j%2==0 else v+y for j,v in enumerate(z))))
        assert len(ports)==13507 and len({r['pin'] for r in ports})==13507
        ys={}
        for key,points in grid.items():points.sort();ys[key]=[p[0] for p in points]
        examined=0;matched=0
        def consume(reader):
            nonlocal examined,matched
            for r in reader:
                layer=r['layer']
                if layer not in maxgrow or r['kind']=='UNROUTED':continue
                examined+=1;b=tuple(int(r[k]) for k in ['x0','y0','x1','y1']);grow=maxgrow[layer]
                for ix in range((b[0]-grow)//BIN,(b[2]+grow)//BIN+1):
                    key=(layer,ix)
                    if key not in grid:continue
                    points=grid[key];lo=bisect_left(ys[key],b[1]-grow);hi=bisect_right(ys[key],b[3]+grow)
                    for cy,index,a in points[lo:hi]:
                        point=ports[index];same=r['net']==point['net'];cut=layer.startswith('via')
                        if same and not cut:
                            if layer!=point['original_layer'] and a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]:point['own_next_layer_metal_intersections']+=1
                            continue
                        if same and cut and a==b:point['own_exact_first_hop_cut_present']+=1;continue
                        dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0);need=spacing(layer,a,b)
                        if dx*dx+dy*dy>=need*need:continue
                        matched+=1;point['foreign_or_cut_spacing_risks']+=1
                        if len(point['examples'])<5:point['examples'].append({'actual_net':r['net'],'layer':layer,'kind':r['kind'],'actual_box_DBU':b,'needed_spacing_DBU':need,'same_net_cut':same})
        with gzip.open(str(geo),'rt') as f:consume(csv.DictReader(f,delimiter='\t'))
        with (native/'actual_high_PG_OBS.tsv').open() as f:consume(csv.DictReader(f,delimiter='\t'))
        counts=Counter()
        for r in ports:
            r['status']='FIRST_HOP_ACTUAL_GEOMETRY_RISK' if r['foreign_or_cut_spacing_risks'] else 'FIRST_HOP_SCREEN_CLEAR_NOT_NATIVE_AP_PASS'
            counts[r['status']]+=1
            if not r['on_M6_X_grid'] or not r['on_first_hop_Y_grid']:counts['not_on_actual_first_hop_cross_grid']+=1
        with (out/'all13507_actual_first_hop_risks.json').open('w') as f:json.dump(ports,f,indent=2);f.write('\n')
        rec.update(all_original_signal_pin_contracts_inventoried=13507,status_counts=dict(counts),actual_geometry_rows_examined=examined,exact_pair_risks=matched,
          actual_via_templates=vias,bit1011_actual=next(r for r in ports if r['pin']=='bit_1011'),neither_unverified_nor_risk_is_complete_native_DRC_verdict=True)
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
