module spare_bank (
    input b0_A, b1_A, b2_A, b3_A,
    output b0_Z, b1_Z, b2_Z, b3_Z
);
  BUF_X32 b0 (.A(b0_A), .Z(b0_Z));
  BUF_X32 b1 (.A(b1_A), .Z(b1_Z));
  BUF_X32 b2 (.A(b2_A), .Z(b2_Z));
  BUF_X32 b3 (.A(b3_A), .Z(b3_Z));
endmodule
