"""Text-only fixture extension; pointer and target oracle sees actual CALLs."""

def extend(s):
    s=s.replace('  reg [127:0] input_image', '''  integer check_ptr=0,expect_ready=-1,check_targets=0;
  reg [63:0] ptr_start=0,ptr_stride=128;
  reg [7:0] oracle_targets[0:4095];
  string targets_path;
  reg [127:0] input_image''')
    marker="        if(task_packet_o[16+:8]==0) begin"
    assert marker in s
    s=s.replace(marker,marker+'''
          if(check_ptr!=0) assert(task_packet_o[256+:64]==ptr_start+64'(calls)*ptr_stride)
            else $fatal(1,"CALL pointer differs from fully unrolled oracle at %0d",calls);
          if(check_targets!=0) assert(task_target_o==oracle_targets[calls])
            else $fatal(1,"CALL target differs from fully unrolled oracle at %0d",calls);''')
    marker='    n=$value$plusargs("EXPECTED=%d",expect_status);'
    assert marker in s
    s=s.replace(marker,'''    n=$value$plusargs("CHECK_PTR=%d",check_ptr);n=$value$plusargs("PTR_START=%d",ptr_start);
    n=$value$plusargs("PTR_STRIDE=%d",ptr_stride);n=$value$plusargs("EXPECT_READY=%d",expect_ready);
    check_targets=$value$plusargs("TARGETS_FILE=%s",targets_path);
    if(check_targets!=0) $readmemh(targets_path,oracle_targets,0,expected_calls-1);
'''+marker)
    marker='    $display("PASS mother calls='
    assert marker in s
    s=s.replace(marker,'''    if(expect_ready>=0) assert(ready_count==expect_ready)else $fatal(1,"repeated READY count");
'''+marker)
    return s
