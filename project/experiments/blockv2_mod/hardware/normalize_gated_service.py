"""Preserve the fetched CALL ticket through G32 service completion."""
def normalize(text):
    if 'output reg [31:0] service_done_ticket' in text:return text
    text=text.replace('output reg [127:0] service_done_owner,',
        'output reg [31:0] service_done_ticket,\n output reg [127:0] service_done_owner,')
    text=text.replace('wire unused=^{service_ticket,service_descriptor[1023:992]};',
        'wire unused=^service_descriptor[1023:992];')
    text=text.replace('endmodule',""" always @(posedge clk)begin
  if(reset)service_done_ticket<=0;
  else if(service_valid&&service_ready)service_done_ticket<=service_ticket;
 end
endmodule""")
    return text
if __name__=='__main__':
    from pathlib import Path
    p=Path(__file__).resolve().parents[1]/'rtl/services/gated_s32_service_controller.sv'
    p.write_text(normalize(p.read_text()))
