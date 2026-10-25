#include "Vshared106.h"
#include "verilated.h"
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vshared106 d;d.reset=1;d.clk=0;d.eval();d.clk=1;d.eval();return 0;}
