#!/usr/bin/env python3
"""Render all actual native instance/route rows; creates pictures only, never writes an ODB."""
from pathlib import Path
import os,json,gzip,csv,hashlib,datetime,concurrent.futures,collections,math,sys
os.environ.update(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",NUMEXPR_NUM_THREADS="1")
import numpy as np
from PIL import Image,ImageDraw,ImageFont
N=Path('/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z')
OUT=Path(__file__).resolve().parent
SIZE=1024; SMALL=380
COLORS=['#d94c4c','#2785bf','#d89822','#429b55','#9959ba','#35a5a5','#c86d38','#bd4b93']
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def table(p):
 with gzip.open(p,'rt',newline='')as f:yield from csv.DictReader(f,delimiter='\t')
def savejson(p,j):
 with p.open('x')as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def record(p):
 b=p.read_bytes();return {'name':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_sha':hashlib.sha1(b'blob '+str(len(b)).encode()+bytes([0])+b).hexdigest()}
def pix(box,domain,size):
 x0,y0,x1,y1=box;a,b,c,d=domain
 if x1<a or x0>c or y1<b or y0>d:return None
 fx=size/(c-a);fy=size/(d-b)
 return (max(0,min(size-1,int((x0-a)*fx))),max(0,min(size-1,int((d-y1)*fy))),max(0,min(size-1,math.ceil((x1-a)*fx)-1)),max(0,min(size-1,math.ceil((d-y0)*fy)-1)))
def image_save(im,path):
 assert not path.exists()
 im.save(path,optimize=True)
 with Image.open(path)as z:z.verify()
 return record(path)
def caption(im,title,subtitle):
 panel=Image.new('RGB',(im.width+40,im.height+90),'white');panel.paste(im,(20,65));d=ImageDraw.Draw(panel)
 d.text((20,14),title,fill='#172335',font_size=20)
 d.text((20,40),subtitle,fill='#39495b',font_size=13)
 return panel
def render(item):
 name,v=item;dest=OUT/'files';view=Path(v['source_access_receipt']).parent
 receipt=json.loads((view/'execution.json').read_text())
 assert receipt['status']=='pass_full_interface_additive_m8_geometry_only' and receipt['inputs_unchanged']
 native=view/'native'; inputs={}
 for fn in ['metadata','instances','shapes','shape_counts']:
  p=native/(fn+'.tsv.gz');expected=receipt['artifacts']['native/'+p.name]['sha256']
  actual=digest(p);assert actual==expected,(name,fn)
  inputs[fn]={'path':str(p),'sha256':actual,'bytes':p.stat().st_size}
 assert receipt['artifacts']['extend/extended.odb']['sha256']==v['child_database_sha256']
 meta={z['key']:z['value']for z in table(native/'metadata.tsv.gz')};assert meta['complete']=='true'
 domain=list(map(int,meta['die_box'].split()));dbu=int(meta['dbu_per_um'])
 expected=collections.Counter()
 for z in table(native/'shape_counts.tsv.gz'):
  expected[(z['kind'],z['sig_type'],z['layer'],z['layer_type'])]+=int(z['count'])
 placement=Image.new('RGB',(SIZE,SIZE),'#f4f6f8');pd=ImageDraw.Draw(placement)
 cells=collections.Counter();count=0;best=None;center=((domain[0]+domain[2])/2,(domain[1]+domain[3])/2)
 for z in table(native/'instances.tsv.gz'):
  box=tuple(int(z[k])for k in ['x0','y0','x1','y1']);rect=pix(box,domain,SIZE)
  cls='memory_macro'if z['master_type']=='BLOCK'else('state_cell'if any(t in z['master']for t in ['DFF','SDFF','LATCH','DLH','DLL'])else'logic_cell')
  cells[cls]+=1;count+=1
  if rect:pd.rectangle(rect,fill={'memory_macro':'#aa57ae','state_cell':'#d98f22','logic_cell':'#3987b6'}[cls])
  if cls=='state_cell':
   cx=(box[0]+box[2])/2;cy=(box[1]+box[3])/2;dist=(cx-center[0])**2+(cy-center[1])**2
   if best is None or dist<best[0]:best=(dist,cx,cy,z['name'],z['master'])
 assert count==int(meta['instance_count'])
 if best is None:raise ValueError('No actual state cell for reproducible zoom')
 half=12*dbu;zoom=[int(best[1]-half),int(best[2]-half),int(best[1]+half),int(best[2]+half)]
 zoom=[max(domain[0],zoom[0]),max(domain[1],zoom[1]),min(domain[2],zoom[2]),min(domain[3],zoom[3])]
 pd.rectangle(pix(zoom,domain,SIZE),outline='#ff1616',width=3)
 figures=[image_save(caption(placement,name+' | actual cell placement',f'{count:,} instances; blue=logic, amber=state, purple=memory; red box=zoom'),dest/(name+'-cells.png'))]
 masks=[Image.new('1',(SIZE,SIZE),0)for _ in range(8)]
 pgs=[Image.new('1',(SIZE,SIZE),0)for _ in range(8)]
 draws=[ImageDraw.Draw(z)for z in masks];pgdraws=[ImageDraw.Draw(z)for z in pgs]
 zoom_imgs=[Image.new('RGB',(SMALL,SMALL),'white')for _ in range(8)]
 zd=[ImageDraw.Draw(z)for z in zoom_imgs];zoom_cells=[]
 for z in table(native/'instances.tsv.gz'):
  box=tuple(int(z[k])for k in ['x0','y0','x1','y1']);rect=pix(box,zoom,SMALL)
  if rect:
   for dr in zd:dr.rectangle(rect,fill='#f5f5f5',outline='#b4bac2',width=1)
   zoom_cells.append({'name':z['name'],'master':z['master'],'bbox':box})
 actual=collections.Counter();layer_counts=collections.Counter();zoom_counts=collections.Counter();shapes=0
 for z in table(native/'shapes.tsv.gz'):
  kind,sig,layer,ltype=z['kind'],z['sig_type'],z['layer'],z['layer_type']
  actual[kind,sig,layer,ltype]+=1;shapes+=1
  box=tuple(int(z[k])for k in ['x0','y0','x1','y1'])
  if ltype=='CUT':
   rect=pix(box,zoom,SMALL)
   if rect:
    try:idx=int(layer.removeprefix('via'))-1
    except ValueError:continue
    for ll in [idx,idx+1]:
     if 0<=ll<8:zd[ll].rectangle(rect,outline='#151515',width=1)
   continue
  if ltype!='ROUTING' or kind=='BLOCK_OBS':continue
  if not layer.startswith('metal'):raise ValueError('Unexpected routing layer '+layer)
  level=int(layer[5:]);assert 1<=level<=8,('Reserved M9/M10 is not empty',layer)
  idx=level-1;pg=sig in ['POWER','GROUND']
  rect=pix(box,domain,SIZE)
  if rect:(pgdraws[idx]if pg else draws[idx]).rectangle(rect,fill=1)
  rect=pix(box,zoom,SMALL)
  if rect:
   zd[idx].rectangle(rect,fill='#a7adb5'if pg else COLORS[idx])
   zoom_counts[layer]+=1
  layer_counts[layer,'PG'if pg else'SIGNAL_CLOCK']+=1
 assert actual==expected,('Incomplete shape census',name,actual-expected,expected-actual)
 combined=Image.new('RGB',(SIZE,SIZE),'white')
 for z in pgs:combined.paste('#b4bac2',(0,0),z)
 for i,z in enumerate(masks):combined.paste(COLORS[i],(0,0),z)
 figures.append(image_save(caption(combined,name+' | actual routed metal',f'All {shapes:,} native rows read; per-layer views disambiguate overlaps; overview pixels are conservative'),dest/(name+'-routes.png')))
 sheet=Image.new('RGB',(4*(SMALL+20),2*(SMALL+55)+65),'white');sd=ImageDraw.Draw(sheet)
 sd.text((15,10),name+' | real routed geometry by layer',fill='#172335',font_size=20)
 sd.text((15,37),'M1-M8; colors=signal/clock metal and via landings; grey=power; no invented connections',fill='#39495b',font_size=13)
 detail=Image.new('RGB',sheet.size,'white');dd=ImageDraw.Draw(detail)
 dd.text((15,10),name+' | local cells + real metal/vias',fill='#172335',font_size=20)
 dd.text((15,37),f'Window: {zoom[0]/dbu:.3f},{zoom[1]/dbu:.3f} to {zoom[2]/dbu:.3f},{zoom[3]/dbu:.3f} um; grey outlines=cells',fill='#39495b',font_size=13)
 for i in range(8):
  x=(i%4)*(SMALL+20)+10;y=(i//4)*(SMALL+55)+95
  panel=Image.new('RGB',(SIZE,SIZE),'white');panel.paste('#b4bac2',(0,0),pgs[i]);panel.paste(COLORS[i],(0,0),masks[i])
  panel=panel.resize((SMALL,SMALL),Image.Resampling.NEAREST)
  sheet.paste(panel,(x,y));sd.text((x,y-23),'M'+str(i+1),fill=COLORS[i],font_size=18)
  detail.paste(zoom_imgs[i],(x,y));dd.text((x,y-23),'M'+str(i+1)+' / '+str(zoom_counts['metal'+str(i+1)])+' shapes',fill=COLORS[i],font_size=16)
 figures.append(image_save(sheet,dest/(name+'-layers.png')))
 figures.append(image_save(detail,dest/(name+'-detail.png')))
 output={'block':name,'native_source_database':v['child_database'],'native_source_database_sha256':v['child_database_sha256'],'source_receipt':{'path':str(view/'execution.json'),'sha256':digest(view/'execution.json')},'inputs':inputs,'instances':count,'cell_categories':dict(cells),'all_native_shape_rows':shapes,'shape_census_matches_closed_native_export':True,'layer_counts':{a+'/'+b:c for(a,b),c in layer_counts.items()},'zoom_domain_dbu':zoom,'zoom_reference_actual_state':{'instance':best[3],'master':best[4]},'zoom_cells':zoom_cells,'figures':figures,'limits':['Visual export only; no new DRC/connectivity/function/timing check.','All exported cell rectangles and routing/cut rows are consumed and counted; finite pixels merge subpixel shapes.','Masters are LEF/OpenDB cell/macro outlines, not transistor schematic or transistor-internal metal.','OBS is not painted as conductor. Non-M1-M8 cut geometry is counted but not fabricated into routing.','Archived candidate snapshot; not the latest internal repair version or a frozen base.']}
 savejson(OUT/(name+'-result.json'),output)
 print(json.dumps({'finished':name,'instances':count,'rows':shapes,'png_bytes':sum(x['bytes']for x in figures)}),flush=True)
 return output
def main():
 assert int(os.environ['SLURM_CPUS_PER_TASK'])==4 and len(os.sched_getaffinity(0))==4
 views=json.loads((N/'runs/union-native-placement-r01-timing-repair-4c-01/expected_placement.json').read_text())['source_views']
 (OUT/'files').mkdir()
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:result=list(pool.map(render,list(views.items())))
 manifest={'status':'PASS_VISUAL_EXPORT_CENSUS_ONLY','started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'allocated_cpus':4,'actual_max_worker_processes':4,'threads_per_worker':1,'code_sha256':digest(Path(__file__)),'Pillow_version':__import__('PIL').__version__,'numpy_version':np.__version__,'all_blocks':result,'original_inputs_modified':False,'new_physical_implementation':False,'base_frozen':False}
 savejson(OUT/'render_execution.json',manifest)
 print('PASS_VISUAL_EXPORT_CENSUS_ONLY',flush=True)
if __name__=='__main__':main()
