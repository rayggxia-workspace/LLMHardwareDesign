"""Bounded operand capture for unresolved arithmetic; no simulated clock events."""
from collections import Counter
import importlib
import json
import math
from arithmetic_observation import ArithmeticObservation


def plain(value):
    if hasattr(value, 'tolist'):
        return plain(value.tolist())
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('nonfinite arithmetic observation')
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    raise TypeError('unsupported arithmetic observation type: ' + str(type(value)))


class OperatorObservation(ArithmeticObservation):
    def __init__(self, execution):
        super().__init__(execution)
        self.operator_counts = Counter()
        self.operator_samples = []
        for site, unit in enumerate(execution.e):
            unit.op_observer = self
            unit.op_site = site
        # Each module imports the reference by value; wrap every actual binding.
        self.softmax_bindings = []
        for name in ('native_tlm_attention', 'pr272_native_attention', 'attention_compact', 'attention_wide'):
            module = importlib.import_module(name)
            if hasattr(module, 'reference'):
                module.reference = self.softmax(module.reference, name)
                self.softmax_bindings.append(name)

    def op_record(self, kind, site, shape, inputs, outputs):
        window = self.window(self.execution.clock.now)
        key = '{}:{}:site{}:{}'.format(window, kind, site, json.dumps(shape, sort_keys=True))
        self.operator_counts[key] += 1
        if self.operator_counts[key] <= 2:
            self.operator_samples.append(dict(kind=kind, site=site, window=window, signature=key,
                shape=plain(shape), clock_ps=self.execution.clock.now, inputs=plain(inputs), outputs=plain(outputs)))

    def op_output(self, kind, site, shape, inputs, output):
        self.op_record(kind, site, shape, inputs, {'result': output})
        return output

    def softmax(self, reference, module):
        def observe(scores, coefficients):
            result = reference(scores, coefficients)
            self.op_record('softmax', 0, {'elements':len(scores), 'implementation':module},
                           {'scores':scores}, {'exponents':result[0], 'probabilities':result[1]})
            return result
        return observe

    def write(self, destination):
        super().write(destination)
        result = dict(scope='actual frozen TLM operands/results and complete call counts; no new RTL or energy acceptance',
            sampling='first two per window/operator/site/shape signature; not a statistical confidence bound',
            counts=self.operator_counts, samples=self.operator_samples, softmax_bindings=self.softmax_bindings)
        destination.with_name('operator-observation.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
