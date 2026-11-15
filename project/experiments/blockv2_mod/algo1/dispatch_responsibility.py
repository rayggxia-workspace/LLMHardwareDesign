"""Attribute native admission failures to their implementation boundary."""


def responsibilities(hardware):
    spec = hardware["event_model"]
    contracts = hardware.get("native_provider_contracts", {})
    records = []
    for section, issues in spec.get("native_dispatch_issues", {}).items():
        for name, reason in sorted(issues.items()):
            candidate = spec[section][name]
            providers = candidate.get("native_providers", {})
            participants = candidate.get("finite_loop", {}).get("participants", {})
            targets = {p["control"] for p in participants.values()} or set(providers)
            missing = sorted(target for target in targets
                             if providers.get(target) not in contracts)
            if "missing RTL service route inventory" in reason:
                owner = "algo1_base_adapter"
                repair = "Resolve the candidate target against the actual RTL instance inventory."
            elif not providers or missing:
                owner = "algo1_native_codegen"
                repair = "Implement and register the selected candidate's native encoder contract."
            elif "no RTL completion" in reason or "no RTL service route" in reason:
                owner = "blockv2_mod_dispatch"
                repair = "Connect the exact descriptor to its RTL provider and committed completion."
            else:
                owner = "algo1_base_adapter"
                repair = "Bind the candidate requirements to the RTL interfaces."
            records.append({
                "section": section, "candidate": name, "owner": owner,
                "reason": reason, "repair": repair,
                "native_providers": providers,
                "missing_encoder_targets": missing,
                "additional_repairs": [
                    {"owner": "algo1_native_codegen", "target": target,
                     "repair": "Implement the semantic native encoder; a route registration alone cannot encode this candidate."}
                    for target in missing],
                "validation": "Compile this candidate and execute its emitted commands on the target RTL.",
            })
    return records
