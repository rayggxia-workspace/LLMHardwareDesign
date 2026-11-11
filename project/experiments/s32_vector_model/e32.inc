 bool native_e32_eligible(const Op& o){
  if(!e32::enabled||tensors[o.out].bits!=32||o.elements%4||o.shift< -64||o.shift>63)return false;
  bool unary=o.kind=="Convert";
  if(!unary&&o.kind!="Add"&&o.kind!="Sub"&&o.kind!="Product"&&o.kind!="Maximum"&&o.kind!="Minimum")return false;
  if(o.in.size()!=(unary?1u:2u))return false;
  if(o.kind!="Product"&&!unary&&o.shift!=0)return false;
  for(int t:o.in)if(tensors[t].bits!=32||tensors[t].elements!=o.elements)return false;
  return true;
 }
 void native_e32_tile(const Op& o,size_t index,U offset,U n){
  for(int t:o.in)touch(t,offset*4,n*4,false);
  U old=cfg.vecpipe?ceildiv(n,4)+5:ceildiv(n,4)*cfg.ewise;
  optimization::vector_cost(old,old);e32::removed_vector+=old;
  e32::removed_s_subcycles+=(o.in.size()+1)*s_port_duration(cfg,3,n*4);
  // Native measurements include real S transactions and completion ACKs.
  // For a partial tile conservatively reserve the complete measured tile.
  U cost=e32::table[e32::depth==0?0:e32::depth==2?1:2][o.in.size()==1?0:1];
  pause_until(store[3].reserve(now(),cost*C));e_work+=cost*C;e32::native_cycles+=cost;
  ++e32::tiles;e32::values+=n;if(offset==0)++e32::ops;if(n!=64)++e32::partial_tiles;
  touch(o.out,offset*4,n*4,true);
  for(int t:o.in)if(last_use[t]==static_cast<int>(index))discard_range(t,offset*4,n*4);
 }
