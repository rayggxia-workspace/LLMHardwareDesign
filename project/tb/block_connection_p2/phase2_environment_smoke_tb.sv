`timescale 1ns/1ps
module phase2_environment_smoke_tb;
  initial begin
    if ($signed(16'hffff) != -1) $fatal(1, "signed expression mismatch");
    #1;
    $display("PASS_P2_ENVIRONMENT_SMOKE real SystemVerilog simulator");
    $finish;
  end
endmodule
