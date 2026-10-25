// Same complete original driver; do not call RTL-only register injection methods.
#define main original_r99_driver_main
#include "r_sim.cpp"
#undef main
int main(int argc,char**argv){try{need(argc==5,"args checkpoint-image out stall head");Sim s(argv[1],argv[2],std::stoi(argv[3]),std::stoi(argv[4]));s.reset();s.scratch();s.finish("checkpoint-restore",2,0);need(s.d.status==0,"checkpoint restore");s.finish("checkpoint-step",1,0);need(s.d.status==0,"checkpoint numeric rejection");s.canary();std::cout<<"PASS_CHECKPOINT_DRIVER rows="<<s.record<<"\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
