"""Conservative source-name seeds only; no receiver-cone inference or spatial inference."""
import re
PREFIX='u_slice/u_mxu/'
def norm(s):return s.replace('\\[','[').replace('\\]',']')
def classify(name):
 s=norm(name)
 if not s.startswith(PREFIX):return None
 s=s[len(PREFIX):]
 patterns=[
  (r'g_ask\[(\d+)\]\.g_p\[(\d+)\]\.u_pe[./]', 'PE',lambda m:f'PE[{m[1]},{m[2]}]'),
  (r'g_ask\[(\d+)\]\.g_p\[(\d+)\]\.u_a[./]', 'INPUT_ALIGN',lambda m:f'ACT_SKEW[{m[1]},{m[2]}]'),
  (r'g_wsk\[(\d+)\]\.u_w[./]', 'INPUT_ALIGN',lambda m:f'WEIGHT_SKEW[{m[1]}]'),
  (r'g_col_end\[(\d+)\]\.u_ce[./]', 'COLUMN_END',lambda m:f'COLUMN_END[{m[1]}]'),
  (r'g_col_end\[(\d+)\]\.(u_bm|u_f|u_dsk)[./]', 'COLUMN_ALIGN',lambda m:f'COL_ALIGN[{m[1]}]:{m[2]}'),
  (r'g_fd\[(\d+)\]\.u_fd[./]', 'WEIGHT_FIFO',lambda m:f'WEIGHT_FIFO[{m[1]}]'),
  (r'u_fs([01])[./]', 'SCALE_FIFO',lambda m:f'SCALE_FIFO[{m[1]}]'),
  (r'g_rfm\[(\d+)\][./]', 'RESULT_FIFO',lambda m:f'RESULT_FIFO_COPY[{m[1]}]'),
  (r'g_lane\[(\d+)\]\.u_l[./]', 'FP_EPILOGUE',lambda m:f'FP_EPILOGUE[{m[1]}]'),
  (r'g_rmw\[(\d+)\]\.u_y[./]', 'ACC_RMW',lambda m:f'ACC_RMW[{m[1]}]'),
  (r'(u_tl|u_ts)[./]', 'COLUMN_ALIGN',lambda m:'RESULT_METADATA_ALIGN'),
  (r'u_lm[./]', 'FP_EPILOGUE',lambda m:'EPILOGUE_METADATA'),
  (r'(u_rw|u_rwh)[./]', 'ACC_RMW',lambda m:'RMW_METADATA'),
 ]
 for pat,group,leaf in patterns:
  if m:=re.match(pat,s):return group,leaf(m),'RETAINED_HIERARCHY'
 stem=re.split(r'\[|\$_',s)[0]
 states={
  'INPUT_PREP':'m0 cu0 rs0 wf0 pr0 hi0 M0 wd dlo1 dhi1 vlo1 vhi1 da1 hi1 bm2 sw1 sap1',
  'SCALE_RESPONSE':'tgm tg_t tg_h tg_n tg1 rv1 ln1 r_sw',
  'WEIGHT_FIFO_CONTROL':'f_head f_tail f_count f_rd f_rdl f_tl occ',
  'SCALE_FIFO_CONTROL':'s_head s_tail s_count s_rd',
  'RESULT_FIFO':'rf_q rf_t rf_n rf_hs rh0 rh1 rowp',
  'RESULT_PACK':'rowi rsa rsw rv',
  'DRAIN':'drow dad dj ncnt dg dg1 d_last d_fin rf_nz rl_nz dln dal',
  'FP_EPILOGUE':'p1 p1_x p1_sa p1_sw lo lo_ad lo_col lvm ln_n',
  'ACC_RMW':'r0 r1 rA rx xo alr rmw_n rwh',
  'POSTPROCESS_STATE':'alpha al_st al_i mx_i mk mx_have mx_done mxl mxm mx_go',
  'CONTROL_SHARED':'h n q_n pop_q pn pop_e ck cg cl_ld c_left rows_live rows_p p_G p_M act_grp act_hi t_raddr t_ren',
 }
 for group,words in states.items():
  if stem in words.split():return group,group,'RTL_NAMED_STATE'
 if re.match(r'i_|c_|pf_|st_',stem) or stem in 'row_addr chunk_addr srow_addr srow_next scale_addr'.split():
  return 'CONTROL_SHARED','CONTROL_SHARED','RTL_NAMED_STATE'
 return 'INTERNAL_UNCLASSIFIED','INTERNAL_UNCLASSIFIED','NO_INTERNAL_SOURCE_ANCHOR'
