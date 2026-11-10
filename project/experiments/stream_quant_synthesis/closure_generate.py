"""Extend the frozen SystemC trace with explicit candidate contracts/costs."""
from pathlib import Path
from generate import once


def extend(folder):
    folder=Path(folder);p=folder/'model.cpp';s=p.read_text()
    s=once(s,' int bn_release=0;',' int cl_mode=0,cl_issue=1,cl_banks=2,cl_head_group=128;\n int bn_release=0;')
    s=once(s,'std::array<Calendar,6> weight_store','std::array<Calendar,24> weight_store')
    s=s.replace('weight_store[2*b->group+b->operand_bank]','weight_store[(cfg.cl_mode>=5?8:2)*b->group+b->operand_bank]')
    s=once(s,'b->operand_bank>=0&&b->operand_bank<2','b->operand_bank>=0&&b->operand_bank<cfg.cl_banks')
    s=s.replace('weight_store[2*worker+p->bank]','weight_store[(cfg.cl_mode>=5?8:2)*worker+p->bank]')
    s=once(s,'issue_free=issue+C;','issue_free=issue+C/U(cfg.cl_issue);')
    s=once(s,' void run(){','#include "closure_service.inc"\n void run(){')
    s=once(s,'for(int w=0;w<cfg.mcount;++w)buffers.emplace_back',
           'for(int w=0;w<cfg.mcount;++w)cl_buffers.emplace_back(new CLBuffer(cfg.cl_banks));for(int w=0;w<cfg.mcount;++w)buffers.emplace_back')
    s=once(s,'while(cache.size()>=192)', 'while(cache.size()>=(cl_active?128U:192U))')
    s=once(s,'require(cache.size()*64+4096<=16384,','require(cache.size()*64+4096+(cl_active?4096:0)<=16384,')
    s=once(s,'if(o.kind=="Dot"){const Op lowered=',
           'if(cl_ffn_match(i)){cl_ffn(i);i+=5;family="FFN_closure";}\n    else if(o.kind=="Dot"){const Op lowered=')
    old='const U micro=o.kind=="SiLU"?41:o.kind=="RoPE"?3:128;'
    s=once(s,old,old+'\n  const bool cl_g=cfg.cl_mode&&o.kind=="SiLU";')
    s=once(s,'U cost=cfg.vecpipe?(ceildiv(n,cfg.vector_lanes)+5)*micro:ceildiv(n,4)*cfg.ewise*micro;',
           'U cost=cl_g?ceildiv(n,2)+3+ceildiv(n,4)+1:(cfg.vecpipe?(ceildiv(n,cfg.vector_lanes)+5)*micro:ceildiv(n,4)*cfg.ewise*micro);\n'
           '   if(cl_g){cl_G_values+=n;cl_G_cycles+=cost;}')
    s=once(s,'  c.bn_release=sq_integer(',
           '  c.cl_mode=sq_integer("CL_MODE",0);c.cl_issue=sq_integer("CL_ISSUE",1);c.cl_banks=sq_integer("CL_BANKS",2);c.cl_head_group=sq_integer("CL_HEAD_GROUP",128);\n'
           '  if(c.cl_head_group!=32&&c.cl_head_group!=128)throw std::invalid_argument("head group");\n'
           '  if(c.cl_mode<0||c.cl_mode>6||(c.cl_issue!=1&&c.cl_issue!=2&&c.cl_issue!=4)||(c.cl_banks!=2&&c.cl_banks!=4&&c.cl_banks!=8)||(c.cl_mode<5&&c.cl_banks!=2))throw std::invalid_argument("CL mode/ports/banks");\n'
           '  c.bn_release=sq_integer(')
    s=once(s,' Study s("study",c,argv[1]);',
           ' if(c.cl_mode){if(c.sq_abits!=16||c.mcount!=3||c.beat!=64)throw std::invalid_argument("closure requires A16/3P/64B");c.k=128;}\n Study s("study",c,argv[1]);')
    begin=s.index('   // Two passes establish one common activation scale')
    end=s.index('   flush(target);',begin)
    s=s[:begin]+'''   // Finite per128 power-of-two normalization, explicit max/RNE/metadata.
   for(U offset=0;offset<input.elements;offset+=128){
    const U n=std::min<U>(128,input.elements-offset);
    read_range(source,offset*(input.bits/8),n*(input.bits/8));
    const U cost=2*ceildiv(n,4)+2;e_work+=cost*C;cycles(cost);sq_quant_values+=n;
    write_range(target,offset*(cfg.sq_abits/8),n*(cfg.sq_abits/8));
    cycles(1); // scale descriptor write; one byte stored per group
   }
'''+s[end:]
    # Off mode must preserve the exact two-pass original path.
    original=p.read_text();a=original.index('   // Two passes establish one common activation scale');b=original.index('   flush(target);',a)
    newbegin=s.index('   // Finite per128');newend=s.index('   flush(target);',newbegin)
    s=s[:newbegin]+'   if(cfg.cl_mode){\n'+s[newbegin:newend]+'   }else{\n'+original[a:b]+'   }\n'+s[newend:]
    s=once(s,'  U start=now();\n  U send=',
           '  if(cfg.cl_mode&&weight&&cfg.cl_mode<4){\n'
           '   CLJob j{o.in[1],p->col,p->ki,o.k,false,false};\n'
           '   for(int offset=0;offset<p->k;offset+=128){j.kk=p->ki+offset;mem.transfer(worker,cl_meta_address(j),16,false,detail::WEIGHT,p->bank);cl_metadata+=16;}\n'
           '   cycles(2);adapter_work+=2*C;\n'
           '  }\n  if(cfg.cl_mode>=4&&weight){const bool head32=cfg.cl_head_group==32&&o.cols==151936&&o.k==2048;const U extra=head32?4:0;cycles(2+extra);adapter_work+=(2+extra)*C;cl_metadata+=head32?64:16;}\n  U start=now();\n  U send=')
    # Carry scales in the same finite queued record, not a serial 16B DRAM
    # transaction on the consumer's critical path. Old modes remain unchanged.
    for name in ('matrix.inc','context_worker.inc'):
        path=folder/name;text=path.read_text()
        if name=='matrix.inc':
            text=once(text,'      load(addr,bbytes,detail::WEIGHT);',
                      '      if(cfg.cl_mode>=4){require(k==128&&n==8,"CL packed shape");load(cl_packed_address(o.in[1],col,kk,o.k),1088,detail::WEIGHT);}else load(addr,bbytes,detail::WEIGHT);')
        else:
            old='       if(cfg.queued)pending.push_back(mem.submit(worker,address,bbytes,false,detail::WEIGHT,bbank));'
            text=once(text,old,
                      '       if(cfg.cl_mode>=4){require(k==128&&n==8,"CL packed context shape");pending.push_back(mem.submit(worker,cl_packed_address(o.in[1],col,kk,o.k),1088,false,detail::WEIGHT,bbank));}\n'
                      '       else if(cfg.queued)pending.push_back(mem.submit(worker,address,bbytes,false,detail::WEIGHT,bbank));')
        path.write_bytes(text.encode())
    emit=r'''std::cout<<",\"closure\":{\"mode\":"<<cfg.cl_mode<<",\"issue_lanes_per_channel\":"<<cfg.cl_issue
      <<",\"FFNs\":"<<cl_ffns<<",\"scale_metadata_bytes\":"<<cl_metadata
      <<",\"partial_read_bytes\":"<<cl_partial_read<<",\"partial_write_bytes\":"<<cl_partial_write
      <<",\"link_payload_bytes\":"<<cl_link_bytes<<",\"G_values\":"<<cl_G_values<<",\"G_cycles\":"<<cl_G_cycles
      <<",\"bank_peak\":"<<cl_peak_b<<",\"S_peak\":"<<cl_peak_s<<",\"waves\":"<<cl_wave_count
      <<",\"A_tile_register_bytes_per_P\":"<<(cfg.cl_mode>=3?256:0)
      <<",\"projection_partial_register_bytes_per_P\":"<<(cfg.cl_mode>=4?2048:0)
      <<",\"packed_weight_scales\":"<<(cfg.cl_mode>=4?"true":"false")
      <<",\"full_A_register_bytes_per_P\":"<<(cfg.cl_mode>=5?4096:0)
      <<",\"weight_banks_per_P\":"<<cfg.cl_banks
      <<",\"extra_B_and_result_bytes_per_P\":"<<((cfg.cl_banks-2)*(1088+128))
      <<",\"head_weight_group\":"<<cfg.cl_head_group
      <<",\"quality_profile\":\"W8A16-g128-G32\",\"physical_qualified\":false,\"energy_J_token\":null}";
    std::cout<<"}\n";'''
    s=once(s,'std::cout<<"}\\n";',emit)
    p.write_bytes(s.encode())
    (folder/'closure_service.inc').write_bytes((Path(__file__).parent/'closure_service.inc').read_bytes())
    return folder
