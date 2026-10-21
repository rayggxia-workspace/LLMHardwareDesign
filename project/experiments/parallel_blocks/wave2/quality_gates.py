"""Strict report gates: a tolerance-filtered violation count cannot replace slack."""
import math
import re


def report_cap_slack(report):
    match = re.search(r'finish max_capacitance_check_slack\s*\n-+\s*\n([^\n]+)', report)
    return float(match[1]) if match else None


def nonnegative(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def electrical_gates(quality, final, route, report):
    return dict(
        setup_nonnegative=nonnegative(quality.get('setup_ws_ns')) and final.get('finish__timing__setup__tns') == 0,
        hold_nonnegative=nonnegative(quality.get('hold_ws_ns')) and final.get('finish__timing__hold__tns') == 0,
        antenna_zero=route.get('detailedroute__antenna__violating__nets') == 0 and route.get('detailedroute__antenna__violating__pins') == 0,
        max_cap_zero=quality.get('max_cap') == 0,
        worst_cap_slack_nonnegative=nonnegative(report_cap_slack(report)),
        cap_slack_ratio_nonnegative=nonnegative(final.get('finish__timing__drv__max_cap_limit')),
        max_slew_zero=quality.get('max_slew') == 0,
        slew_slack_ratio_nonnegative=nonnegative(final.get('finish__timing__drv__max_slew_limit')),
        max_fanout_zero=quality.get('max_fanout') == 0,
        fanout_slack_ratio_nonnegative=nonnegative(final.get('finish__timing__drv__max_fanout_limit')))
