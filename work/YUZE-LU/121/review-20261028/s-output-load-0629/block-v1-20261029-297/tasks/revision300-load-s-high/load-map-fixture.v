module revision300_load_map(input clk,d,output q0,q1);
DFF_X1 f0(.CK(clk),.D(d),.Q(q0));
DFF_X1 f1(.CK(clk),.D(d),.Q(q1));
endmodule
