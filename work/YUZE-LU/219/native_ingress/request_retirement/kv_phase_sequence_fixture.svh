    // The real KV receipt controls phase completion. This fixture supplies
    // the independent page terminal and token fields as protocol peers.
    logic seq_ready,seq_page_valid,seq_page_done_ready,seq_kv_ready,seq_token_ready;
    logic phase_terminal_valid,phase_terminal_error;
    logic [31:0] seq_generation,phase_terminal_job,phase_terminal_step;
    logic [31:0] phase_terminal_length,phase_terminal_token;
    logic seq_finished_page;
    wire real_phase=phase_job==1;
    wire kv_forward_ready=receipt_ready && (!real_phase || seq_kv_ready);
    native_phase_page_sequence phase_sequencer(
        .clk,.reset,.phase_valid(phase_valid && phase_ready && real_phase),.phase_ready(seq_ready),
        .phase_job_tag(phase_job),.phase_step,.phase_required_kv(phase_row.end_position),
        .phase_input_token(32'd0),.phase_page_count(32'd1),
        .page_valid(seq_page_valid),.page_ready(1'b1),.page_job_tag(),.page_step(),.page_index(),
        .page_generation(seq_generation),.page_input_token(),
        .page_done_valid(seq_page_done_ready && !seq_finished_page),.page_done_ready(seq_page_done_ready),
        .page_done_generation(seq_generation),.page_done_error(1'b0),
        .kv_valid(receipt_valid && receipt_ready && real_phase),.kv_ready(seq_kv_ready),
        .kv_job_tag(receipt_job),.kv_step(receipt_step),.kv_length(receipt_length),.kv_error(receipt_error),
        .token_valid(seq_page_done_ready && !seq_finished_page),.token_ready(seq_token_ready),
        .token_job_tag(phase_job),.token_step(phase_step),.token_value(32'd81917),.token_error(1'b0),
        .phase_done_valid(phase_terminal_valid),.phase_done_ready(1'b1),
        .phase_done_job_tag(phase_terminal_job),.phase_done_step(phase_terminal_step),
        .phase_done_kv_length(phase_terminal_length),.phase_done_token(phase_terminal_token),
        .phase_done_error(phase_terminal_error));

    always @(posedge clk) begin
        if(reset) seq_finished_page<=0;
        else begin
            if(phase_valid && phase_ready && real_phase) begin
                assert(seq_ready);
                seq_finished_page<=0;
            end
            if(seq_page_done_ready && !seq_finished_page) begin
                assert(seq_token_ready && !receipt_valid && !phase_terminal_valid);
                seq_finished_page<=1;
            end
            if(phase_terminal_valid) begin
                assert(!phase_terminal_error && phase_terminal_job==phase_job &&
                       phase_terminal_step==phase_step && phase_terminal_length==32'(phase_first)+1 &&
                       phase_terminal_token==81917 && rows_done==(phase_step-32'(FIRST_STEP)+1)*STREAMS &&
                       acks==8*rows_done);
                $display("KV_SEQUENCE_COMMIT step=%0d length=%0d rows=%0d acks=%0d cycle=%0d",
                         phase_terminal_step,phase_terminal_length,rows_done,acks,cycle);
            end
        end
    end
