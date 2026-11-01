module api_fixture (i,
    o);
 input i;
 output o;


 BUF_X4 b (.A(i),
    .Z(o));
endmodule
