    // Test-only bridge. The trial SRAM ACK is one bit. Carry source service
    // identity in the injector to exercise the existing ACK guard before release.
    localparam int EARLY=1, DUPLICATE=2, STALE_JOB=3, WRONG_JOB=4, WRONG_EPOCH=5,
                   WRONG_TASK=6, WRONG_SERVICE=7, DROP_ACK=8, STALE_RESET=9, REPEAT_JOB=10;
    int ack_case=0;
    int attempts=0, commits=0, rejected_acks=0;
    reg response_seen=0, early_sent=0;
    wire [127:0] outgoing_identity[2];
    reg [127:0] active_identity, previous_identity;
    reg previous_valid=0;
    wire arm = link_valid[0] && link_ready[1] && accept_request;
    wire store_commit = link_ack[1] && !response_seen;
    wire stale = (ack_case==STALE_JOB || ack_case==STALE_RESET) && previous_valid;
    wire wrong = ack_case>=WRONG_JOB && ack_case<=WRONG_SERVICE;
    wire two_attempts = stale || wrong || ack_case==DUPLICATE;
    wire inject_early = ack_case==EARLY && offers>transfers && !response_seen && !early_sent;
    wire send_ack = link_ack[1] && response_seen && accept_ack && ack_case!=DROP_ACK &&
                    attempts < (two_attempts ? 2 : 1);
    wire [127:0] mismatch_mask = 128'd1 << (32*(WRONG_SERVICE-ack_case));
    wire [127:0] wire_identity = attempts==0 && stale ? previous_identity :
                                  attempts==0 && wrong ? active_identity ^ mismatch_mask :
                                  active_identity;
    wire arm_ready, ack_ready, done_valid, rejected, guard_busy;
    wire guarded_ack = done_valid && (ack_case!=DUPLICATE || attempts==2);
    wire release_word = guarded_ack && link_ack_ready[0];
    wire expects_reject = ack_case==EARLY || ack_case==DUPLICATE || stale || wrong;

    p_stored_ack_guard #(.ID_BITS(128)) ack_guard(
        .clk(clk_i),.reset(!rst_ni),.arm_valid(arm),.arm_ready,
        .arm_identity(outgoing_identity[0]),.store_commit,
        .ack_valid(inject_early || send_ack),.ack_ready,.ack_identity(wire_identity),
        .done_valid,.done_ready(release_word),.rejected,.busy(guard_busy));

    always @(posedge clk_i) begin
        if (!rst_ni) begin
            attempts<=0; commits<=0; rejected_acks<=0;
            response_seen<=0; early_sent<=0;
        end else begin
            if (arm) begin
                if (!arm_ready) $fatal(1,"reused pending ACK slot");
                active_identity<=outgoing_identity[0];
            end
            if (store_commit) begin
                if (offers!=transfers+1 || !guard_busy)
                    $fatal(1,"destination SRAM responded without a current offer");
                response_seen<=1;
                commits<=commits+1;
                if (force_no_ack) begin
                    previous_identity<=active_identity;
                    previous_valid<=1;
                end
            end
            if (inject_early && ack_ready) early_sent<=1;
            if (send_ack && ack_ready) begin
                if (stale && attempts==0 && previous_identity==active_identity)
                    $fatal(1,"stale ACK test reused current identity");
                attempts<=attempts+1;
            end
            if (rejected) rejected_acks<=rejected_acks+1;
            if (release_word) begin
                if (!response_seen || !link_ack[1])
                    $fatal(1,"source released before actual destination response");
                if (ack_case==STALE_JOB && transfers==0) begin
                    previous_identity<=active_identity;
                    previous_valid<=1;
                end
                attempts<=0;
                response_seen<=0;
                early_sent<=0;
            end
        end
    end
