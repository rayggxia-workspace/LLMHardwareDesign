module layout_proof(input [8:0] word_index,a_words,input [1:0] lane,input [2:0] cols,output same);
 function automatic [10:0] flat(input [8:0] word_index,input [1:0] lane);
  flat=(11'(word_index)-11'(a_words))*4+11'(lane);
 endfunction
 function automatic [10:0] div3_exact(input [10:0] index);
  reg [20:0] product;
  begin product=index*21'd683;div3_exact={1'b0,product[20:11]};end
 endfunction
 function automatic [2:0] mod3_exact(input [10:0] index);
  reg [10:0] q,r;
  begin q=div3_exact(index);r=index-(q+(q<<1));mod3_exact=r[2:0];end
 endfunction
 function automatic [10:0] row_of(input [10:0] index);
  case(cols)1:row_of=index;2:row_of=index>>1;3:row_of=div3_exact(index);default:row_of=index>>2;endcase
 endfunction
 function automatic [2:0] col_of(input [10:0] index);
  case(cols)1:col_of=0;2:col_of={2'd0,index[0]};3:col_of=mod3_exact(index);default:col_of={1'b0,index[1:0]};endcase
 endfunction
 function automatic [13:0] layout(input [8:0] word_index,input [1:0] lane);
  reg [10:0] index0,base_row;
  reg [2:0] row_step,lane_col,lane_sum;
  begin
   index0=flat(word_index,2'b00);base_row=row_of(index0);lane_sum=3'd0;
   case(cols)
    1:begin row_step={1'b0,lane};lane_col=3'd0;end
    2:begin row_step={2'd0,lane[1]};lane_col={2'd0,lane[0]};end
    3:begin
     lane_sum=mod3_exact(index0)+{1'b0,lane};
     row_step=lane_sum>=3'd3?3'd1:3'd0;
     lane_col=lane_sum>=3'd3?lane_sum-3'd3:lane_sum;
    end
    default:begin row_step=3'd0;lane_col={1'b0,lane};end
   endcase
   layout={base_row+11'(row_step),lane_col};
  end
 endfunction
wire [13:0] gold={row_of(flat(word_index,lane)),col_of(flat(word_index,lane))};
assign same=gold==layout(word_index,lane);
endmodule
