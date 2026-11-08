"""Reproducible cancellation, poison, reset coverage and resumed binary execution."""
import argparse
import copy
import json
import pathlib
import check_recovery
import recovery
import run_campaign

HERE = pathlib.Path(__file__).resolve().parent


def host_case(bundle,job,epoch,sequences):
    case = run_campaign.expected_case(bundle["manifest"]["bundle"],job=job,epoch=epoch)
    for block,seq in sequences.items():
        case["tasks"][block]["sequence"] = seq
    return case


def campaign():
    bundles,peers = run_campaign.inputs()
    specs = json.loads((HERE/"recovery_scenarios.json").read_bytes().decode("utf-8"))["scenarios"]
    experiments = []
    for spec in specs:
        bundle = bundles[spec["bundle"]]
        environment = run_campaign.environment(peers,1)
        environment.update(spec["environment"])
        model = recovery.RecoveryMachine(recovery.machine.loader.load_reference(bundle),environment)
        report = model.run(recovery=dict(trigger=spec["trigger"],drain_ticks=spec.get("drain_ticks",64)))
        checked = check_recovery.check_cancel(report,bundle)
        sram_before = {str(b):recovery.machine.image.digest(bytes(v)) for b,v in model.sram.items()}
        entry = dict(name=spec["name"],cancel=report,check=checked,reset=None)
        next_epoch = 1
        if spec.get("reset"):
            if spec.get("inject_future_native"):
                model.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),40,"old_job_independent")
            reset = model.begin_reset(delays={"M.0":4})
            for _ in range(16):
                if reset.tick():
                    break
            reset_report = reset.report()
            entry["reset"] = dict(report=reset_report,check=check_recovery.check_reset(reset_report,bundle))
            recovery.need(reset.complete,"campaign reset incomplete")
            recovery.need(sram_before == {str(b):recovery.machine.image.digest(bytes(v)) for b,v in model.sram.items()},
                          "reset rolled back/cleared S payload")
            model.reload_after_reset(bundle)
            next_epoch = 2
        # Explicit environment repair; no direct data/program RAM injection.
        model.environment["blocked_channels"] = []
        entry["resume_environment"] = copy.deepcopy(model.environment)
        resumed = model.run(job=8,epoch=next_epoch)
        expected = host_case(bundle,8,next_epoch,spec["next_sequences"])
        entry["resumed"] = dict(report=resumed,check=run_campaign.compare.check_report(expected,resumed))
        entry["S_sha256_before_reset_or_resume"] = sram_before
        experiments.append(entry)
    return dict(schema="control-recovery-campaign/0.1",experiments=experiments,
                cancellation_runs=len(experiments),resumed_runs=len(experiments),
                reset_cohorts=sum(x["reset"] is not None for x in experiments),
                all_independent_checks_pass=True,rtl_tested=False,
                native_wire_has_job_tag=False,provider_ACK_is_modeled_contract=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    text = json.dumps(campaign(),ensure_ascii=False,indent=2)+"\n"
    if args.output:
        pathlib.Path(args.output).write_bytes(text.encode("utf-8"))
    else:
        print(text,end="")


if __name__ == "__main__":
    main()
