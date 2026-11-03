from pathlib import Path
P=Path(__file__).resolve().parents[3]
s=(P/'project/experiments/r_architecture/test_r_stream.cpp').read_text().replace('Vr_stream','Vr_stream_local')
s=s.replace('ck(argc==2,','ck(argc>=2,')
s=s.replace('d.rd_bank=0;tick();','d.rd_bank=0;d.rd_valid=0;d.rd_rsp_ready=0;tick();')
s=s.replace('ck(d.load_ready,"load not ready");','for(unsigned w=0;!d.load_ready;++w){ck(w<100,"load wait");tick();}')
s=s.replace('ck(d.cmd_ready,"pass not ready");','for(unsigned w=0;!d.cmd_ready;++w){ck(w<100,"command wait");tick();}')
s=s.replace('ck(latency==expected,"pass latency mismatch");','ck(latency>=expected,"response before original minimal latency");')
a=s.index(' auto readbank=');b=s.index(' std::vector<std::vector<int32_t>>states;',a)
s=s[:a]+''' auto readbank=[&](unsigned bank,std::vector<int32_t>&v,unsigned start,unsigned count){
  d.rd_bank=bank;
  for(unsigned i=0;i<count;i+=4){
   d.rd_index=i/4;d.rd_valid=1;d.eval();
   for(unsigned w=0;!d.rd_ready;++w){ck(w<100,"read request wait");tick();}
   tick();d.rd_valid=0;d.eval();
   for(unsigned w=0;!d.rd_rsp_valid;++w){ck(w<100,"read response wait");tick();}
   std::array<uint32_t,4> hold;for(unsigned j=0;j<4;++j)hold[j]=d.rd_data[j];
   for(unsigned w=0;w<(i/4)%3;++w){tick();ck(d.rd_rsp_valid,"response lost under backpressure");for(unsigned j=0;j<4;++j)ck(hold[j]==d.rd_data[j],"response changed under backpressure");}
   for(unsigned j=0;j<4&&i+j<count;++j)v[start+i+j]=int32_t(d.rd_data[j]);checks+=4;
   d.rd_rsp_ready=1;tick();d.rd_rsp_ready=0;d.eval();
  }
 };
'''+s[b:]
(P/'project/experiments/r_local_state/test_engine.cpp').write_text(s)
