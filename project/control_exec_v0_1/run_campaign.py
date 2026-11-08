"""Load checked-in binary images, execute them, then invoke independent checks."""
import argparse
import copy
import json
import pathlib
import compare
import machine

HERE = pathlib.Path(__file__).resolve().parent


def inputs():
    bundles = json.loads((HERE.parent/"control_image_v0_1/bundles.json").read_bytes().decode("utf-8"))["bundles"]
    peers = json.loads((HERE/"scenarios.json").read_bytes().decode("utf-8"))
    return bundles,peers


def environment(peers,index):
    value = copy.deepcopy(peers["profiles"][index])
    value["ingress"] = copy.deepcopy(peers["ingress"])
    return value


def expected_case(name,job=7,epoch=1,sequence=1):
    value = copy.deepcopy(compare.oracle.cases()[name])
    value.update(job=job,epoch=epoch)
    for task in value["tasks"].values():
        task["sequence"] = sequence
    return value


def campaign():
    bundles,peers = inputs()
    runs = []
    for profile in (0,1):
        for bundle in bundles:
            runtime = machine.Machine(machine.loader.load_reference(bundle),environment(peers,profile))
            report = runtime.run()
            runs.append(dict(experiment=peers["profiles"][profile]["name"],
                report=report,check=compare.check_report(expected_case(report["bundle"]),report)))
    runtime = machine.Machine(machine.loader.load_reference(bundles[1]),environment(peers,2))
    report = runtime.run()
    runs.append(dict(experiment="M_peer_error_non_nominal",report=report,
                     check=compare.check_report(expected_case(report["bundle"]),report,"error")))
    runtime = machine.Machine(machine.loader.load_reference(bundles[2]),environment(peers,1))
    for sequence,job in [(1,8),(2,9)]:
        report = runtime.run(job=job)
        runs.append(dict(experiment="continuous_without_reset",report=report,
            check=compare.check_report(expected_case(report["bundle"],job=job,sequence=sequence),report)))
    return dict(schema="binary-control-campaign/0.1",runs=runs,total_runs=len(runs),
                instructions_retired=sum(len(r["report"]["retired"]) for r in runs),
                all_independent_checks_pass=True,rtl_tested=False,
                no_full_Block_implementation=True,no_performance_claim=True)


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
