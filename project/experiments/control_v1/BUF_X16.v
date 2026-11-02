// Boolean simulation of the explicitly instantiated Nangate45 BUF_X16.
// Mapping/formal/timing use the actual Liberty cell, never this module.
module BUF_X16(input wire A,output wire Z);
 assign Z=A;
endmodule
