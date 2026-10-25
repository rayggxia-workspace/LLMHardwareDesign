"""Exact one-buffer isolation and original sink preservation certificate."""
import copy,re
from decimal import Decimal
from common import *
from route_audit import incidence,same_wiring
from structure import signature_graph
from receive_physical import block

def audit_cap(stage,previous,before,after,lib):
 sm=artifacts(stage);plan=load(stage/'plan.json');need(plan['stage_manifest_sha256']==sha(previous/'manifest.json')and sm['plan_sha256']==sha(stage/'plan.json')and type(sm['buffer_count'])is int and type(plan['buffer_count'])is int and sm['buffer_count']==plan['buffer_count'],'frozen exact plan')
 canon=signature_graph(before,lib);clock=canon(before['ports']['clk']['bits'][0])[0];need(type(plan['target'])is int and plan['target']in(93,97)and plan['library_sha256']==sha(LIB)and plan['status']=='FROZEN_ACTUAL_RESIDUAL_CAP_CANDIDATE_NOT_EXECUTED','exact typed target and library plan');oldrefs,old_dirs,oldmeta=incidence(before);newrefs,new_dirs,newmeta=incidence(after);names={q['new_buffer_name']for q in plan['plan']};need(not names&set(before['cells'])and len({q['new_net_name']for q in plan['plan']})==len(plan['plan'])and not {q['new_net_name']for q in plan['plan']}&set(before['netnames']),'new instance and net names collision-free');need(len(names)==plan['buffer_count']and 0<len(names)<=64 and set(after['cells'])-set(before['cells'])==names and set(before['cells'])<=set(after['cells']),'exact added buffer set, no deleted cells')
 for n in before['cells']:need(oldmeta[n]==newmeta[n],'no resize/function/parameter/width change to any prior cell')
 log=(previous/'flow.log').read_text();part=block(block(log,'BEGIN_SCENARIO_10','END_SCENARIO_10'),'BEGIN_ELECTRICAL_REPORT','END_ELECTRICAL_REPORT').split('max capacitance',1)[1];drivers=set(re.findall(r'(?m)^(\S+)\s+[0-9.]+\s+[0-9.]+\s+-[0-9.]+\s+\(VIOLATED\)',part));need(drivers=={q['driver_pin']for q in plan['plan']},'all and only actual previous cap violations')
 virtual=copy.deepcopy(after);aliases={};proof=[]
 for q in plan['plan']:
  n,p=q['driver_pin'].rsplit('/',1);bn=q['new_buffer_name'];buf=after['cells'][bn];need(buf['type']=='BUF_X4'and lib[buf['type']]['transparent']==('wire','A','Z',0)and set(buf['connections'])=={'A','Z'},'fixed transparent buffer');a=buf['connections']['A'][0];z=buf['connections']['Z'][0];oldbit=before['cells'][n]['connections'][p][0];need(canon(oldbit)[0]!=clock,'no clock buffer candidate');dbit=after['cells'][n]['connections'][p][0];ref=n+':'+p;need(dbit==a and a!=z and newrefs[a]=={ref,bn+':A'},'old driver now drives only buffer input');need(newrefs[z]==oldrefs[oldbit]-{ref}|{bn+':Z'},'buffer output carries all and only original sinks');aliases[z]=a;del virtual['cells'][bn];proof.append({'driver_pin':q['driver_pin'],'buffer':bn,'original_sink_count':len(oldrefs[oldbit])-1,'new_driver_sink_count':1,'new_buffer_sink_count':len(newrefs[z])-1})
 for c in virtual['cells'].values():
  for p,bs in c['connections'].items():c['connections'][p]=[aliases.get(b,b)for b in bs]
 for p in virtual['ports'].values():p['bits']=[aliases.get(b,b)for b in p['bits']]
 identity=same_wiring(before,virtual);area=lib['BUF_X4']['area']*len(names);need(area==Decimal(plan['total_added_cell_area_um2']),'exact explicit inventory area')
 return {'status':'PASS_EACH_OLD_DRIVER_ISOLATED_ALL_OLD_SINKS_PRESERVED_AND_NO_OTHER_CHANGE','buffers':proof,'new_histogram':{'BUF_X4':len(names)},'explicit_added_area_um2':str(area),'collapsed_electrical_identity':identity}
