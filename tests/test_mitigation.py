"""Tests for qc_compiler.mitigation module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.mitigation import (
    AdaptiveErrorMitigation,
    MitigationPlan,
    MitigationResult,
)


class TestMitigationPlan:
    def test_default_values(self):
        plan = MitigationPlan()
        assert plan.noise_scales == []
        assert plan.shots_per_scale == {}
        assert plan.subcircuit_sensitivity == {}
        assert plan.total_shots == 0
        assert plan.method == "zne"
        assert plan.segments == 0
        assert plan.shots_per_segment == {}
        assert plan.scales_per_segment == {}

    def test_total_noise_scales(self):
        plan = MitigationPlan(noise_scales=[1.0, 2.0, 3.0])
        assert plan.total_noise_scales == 3

    def test_total_noise_scales_empty(self):
        plan = MitigationPlan()
        assert plan.total_noise_scales == 0

    def test_avg_shots_per_scale(self):
        plan = MitigationPlan(shots_per_scale={10: 3000, 20: 2000, 30: 3192})
        assert abs(plan.avg_shots_per_scale - 2730.666666) < 1

    def test_avg_shots_per_scale_empty(self):
        plan = MitigationPlan()
        assert plan.avg_shots_per_scale == 0.0

    def test_max_sensitivity(self):
        plan = MitigationPlan(subcircuit_sensitivity={0: 0.2, 1: 0.6, 2: 0.2})
        assert abs(plan.max_sensitivity - 0.6) < 1e-10

    def test_min_sensitivity(self):
        plan = MitigationPlan(subcircuit_sensitivity={0: 0.2, 1: 0.6, 2: 0.2})
        assert abs(plan.min_sensitivity - 0.2) < 1e-10

    def test_sensitivity_empty(self):
        plan = MitigationPlan()
        assert plan.max_sensitivity == 0.0
        assert plan.min_sensitivity == 0.0


class TestMitigationResult:
    def test_default_values(self):
        result = MitigationResult()
        assert result.mitigated_value == 0.0
        assert result.raw_values == []
        assert result.noise_scales == []
        assert result.extrapolation_coefficients == []
        assert result.shots_used == 0
        assert result.method == "zne"

    def test_custom_values(self):
        result = MitigationResult(
            mitigated_value=0.92,
            raw_values=[0.85, 0.72, 0.58],
            noise_scales=[1.0, 2.0, 3.0],
            extrapolation_coefficients=[3.0, -3.0, 1.0],
            shots_used=8192,
            method="zne",
        )
        assert result.mitigated_value == 0.92
        assert len(result.raw_values) == 3
        assert len(result.extrapolation_coefficients) == 3


class TestAdaptiveErrorMitigationNoBackend:
    """Tests without a backend (default model)."""

    @pytest.fixture
    def mitigation(self):
        return AdaptiveErrorMitigation(cost_model=CostModel())

    def test_create_plan_zne(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, total_shots=8192)
        assert isinstance(plan, MitigationPlan)
        assert plan.method == "zne"
        assert plan.total_shots == 8192
        assert len(plan.noise_scales) > 0

    def test_create_plan_pec(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, total_shots=4096, method="pec")
        assert plan.method == "pec"
        assert plan.total_shots == 4096

    def test_create_plan_cdr(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, total_shots=4096, method="cdr")
        assert plan.method == "cdr"
        assert plan.total_shots == 4096

    def test_create_plan_invalid_method(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(ValueError, match="Unknown mitigation method"):
            mitigation.create_plan(qc, method="invalid")

    def test_create_plan_empty_circuit(self, mitigation):
        qc = QuantumCircuit(4)
        plan = mitigation.create_plan(qc)
        assert plan.total_shots > 0
        assert len(plan.noise_scales) >= 1

    def test_create_plan_ghz(self, mitigation, ghz_circuit):
        plan = mitigation.create_plan(ghz_circuit, total_shots=8192)
        assert plan.segments >= 1
        assert plan.total_shots == 8192
        assert len(plan.subcircuit_sensitivity) > 0

    def test_create_plan_qaoa(self, mitigation, qaoa_circuit):
        plan = mitigation.create_plan(qaoa_circuit, total_shots=8192)
        assert plan.segments >= 1
        assert plan.total_shots == 8192

    def test_execute_zne_with_raw_values(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, total_shots=8192)
        result = mitigation.execute(
            qc, plan, raw_values=[0.85, 0.72, 0.58]
        )
        assert isinstance(result, MitigationResult)
        assert result.method == "zne"
        assert result.shots_used == 8192
        assert result.mitigated_value != 0.0

    def test_execute_zne_single_scale(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = MitigationPlan(
            noise_scales=[1.0],
            total_shots=4096,
            method="zne",
        )
        result = mitigation.execute(qc, plan, raw_values=[0.85])
        assert result.mitigated_value == 0.85
        assert result.method == "zne"

    def test_execute_zne_two_scales(self, mitigation):
        qc = QuantumCircuit(2)
        plan = MitigationPlan(
            noise_scales=[1.0, 3.0],
            total_shots=4096,
            method="zne",
        )
        result = mitigation.execute(qc, plan, raw_values=[0.85, 0.55])
        assert result.method == "zne"
        assert len(result.extrapolation_coefficients) == 2
        assert abs(sum(result.extrapolation_coefficients) - 1.0) < 1e-10

    def test_execute_zne_three_scales(self, mitigation):
        qc = QuantumCircuit(2)
        plan = MitigationPlan(
            noise_scales=[1.0, 2.0, 3.0],
            total_shots=8192,
            method="zne",
        )
        result = mitigation.execute(
            qc, plan, raw_values=[0.85, 0.72, 0.58]
        )
        assert result.method == "zne"
        assert result.mitigated_value != 0.0
        assert len(result.extrapolation_coefficients) == 3

    def test_execute_zne_simulated_values(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc)
        result = mitigation.execute(qc, plan)
        assert result.method == "zne"
        assert result.mitigated_value != 0.0

    def test_execute_pec(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, method="pec")
        result = mitigation.execute(qc, plan, raw_values=[0.85])
        assert result.method == "pec"

    def test_execute_cdr(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, method="cdr")
        result = mitigation.execute(qc, plan, raw_values=[0.85, 0.70])
        assert result.method == "cdr"
        expected = 2 * 0.85 - 0.70
        assert abs(result.mitigated_value - expected) < 1e-10


class TestComputeSensitivity:
    """Tests for sensitivity computation."""

    @pytest.fixture
    def mitigation(self):
        return AdaptiveErrorMitigation(cost_model=CostModel())

    def test_sensitivity_bell_circuit(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        sensitivity = mitigation._compute_sensitivity(qc, {})
        assert len(sensitivity) > 0
        total = sum(sensitivity.values())
        assert abs(total - 1.0) < 1e-10 or total == 0

    def test_sensitivity_with_observable(self, mitigation):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        observable = {"gradient": [0.1, 0.5, 0.2, 0.05]}
        sensitivity = mitigation._compute_sensitivity(qc, observable)
        assert len(sensitivity) > 0

    def test_sensitivity_empty_circuit(self, mitigation):
        qc = QuantumCircuit(4)
        sensitivity = mitigation._compute_sensitivity(qc, {})
        assert isinstance(sensitivity, dict)


class TestAllocateShots:
    """Tests for shot allocation."""

    @pytest.fixture
    def mitigation(self):
        return AdaptiveErrorMitigation(cost_model=CostModel())

    def test_allocate_proportional(self, mitigation):
        sensitivity = {0: 0.5, 1: 0.3, 2: 0.2}
        shots = mitigation._allocate_shots(sensitivity, 10000)
        total = sum(shots.values())
        assert total == 10000

    def test_allocate_equal_for_zero_sensitivity(self, mitigation):
        sensitivity = {0: 0.0, 1: 0.0, 2: 0.0}
        shots = mitigation._allocate_shots(sensitivity, 3000)
        total = sum(shots.values())
        assert total == 3000

    def test_allocate_empty_sensitivity(self, mitigation):
        shots = mitigation._allocate_shots({}, 8192)
        assert 0 in shots
        assert shots[0] == 8192

    def test_allocate_single_segment(self, mitigation):
        sensitivity = {0: 1.0}
        shots = mitigation._allocate_shots(sensitivity, 8192)
        assert shots[0] == 8192


class TestAssignNoiseScales:
    """Tests for noise scale assignment."""

    @pytest.fixture
    def mitigation(self):
        return AdaptiveErrorMitigation(cost_model=CostModel())

    def test_zne_scales_high_sensitivity(self, mitigation):
        sensitivity = {0: 0.6, 1: 0.2, 2: 0.2}
        scales = mitigation._assign_noise_scales(sensitivity, "zne")
        assert len(scales) == 3
        high_sens_idx = max(sensitivity, key=lambda k: sensitivity[k])
        assert len(scales[high_sens_idx]) >= 2

    def test_pec_scales(self, mitigation):
        sensitivity = {0: 0.5, 1: 0.3, 2: 0.2}
        scales = mitigation._assign_noise_scales(sensitivity, "pec")
        for scale_list in scales.values():
            assert scale_list == [1.0]

    def test_cdr_scales(self, mitigation):
        sensitivity = {0: 0.5, 1: 0.3, 2: 0.2}
        scales = mitigation._assign_noise_scales(sensitivity, "cdr")
        for scale_list in scales.values():
            assert scale_list == [1.0, 2.0]

    def test_empty_sensitivity(self, mitigation):
        scales = mitigation._assign_noise_scales({}, "zne")
        assert 0 in scales
        assert len(scales[0]) >= 2


class TestRichardsonCoefficients:
    """Tests for Richardson extrapolation."""

    def test_two_scales(self):
        coeffs = AdaptiveErrorMitigation._richardson_coefficients([1.0, 3.0])
        assert len(coeffs) == 2
        assert abs(sum(coeffs) - 1.0) < 1e-10
        mitigated = coeffs[0] * 0.85 + coeffs[1] * 0.55
        assert mitigated > 0.85

    def test_three_scales(self):
        coeffs = AdaptiveErrorMitigation._richardson_coefficients(
            [1.0, 2.0, 3.0]
        )
        assert len(coeffs) == 3
        assert abs(sum(coeffs) - 1.0) < 1e-10

    def test_single_scale(self):
        coeffs = AdaptiveErrorMitigation._richardson_coefficients([1.0])
        assert coeffs == [1.0]

    def test_empty_scales(self):
        coeffs = AdaptiveErrorMitigation._richardson_coefficients([])
        assert coeffs == []


class TestAdaptiveErrorMitigationWithBackend:
    """Tests with FakeBrisbane backend."""

    @pytest.fixture
    def mitigation_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        return AdaptiveErrorMitigation(cost_model=model)

    def test_create_plan_with_backend(self, mitigation_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        plan = mitigation_with_backend.create_plan(qc)
        assert plan.total_shots == 8192
        assert plan.method == "zne"

    def test_execute_with_backend(self, mitigation_with_backend):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation_with_backend.create_plan(qc)
        result = mitigation_with_backend.execute(qc, plan)
        assert result.method == "zne"


class TestMitigationEdgeCases:
    """Tests for mitigation edge cases."""

    @pytest.fixture
    def mitigation(self):
        return AdaptiveErrorMitigation(cost_model=CostModel())

    def test_execute_unknown_method_returns_result(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = MitigationPlan(
            method="unknown",
            noise_scales=[1.0],
            shots_per_scale={0: [8192]},
            subcircuit_sensitivity={0: 1.0},
            total_shots=8192,
            segments=[(0, 1)],
            shots_per_segment={0: 8192},
            scales_per_segment={0: [1.0]},
        )
        result = mitigation.execute(qc, plan)
        assert result.method == "unknown"

    def test_zne_near_zero_denominator(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, method="zne", num_segments=2)
        result = mitigation.execute(qc, plan, raw_values=[0.5])
        assert result is not None

    def test_gradient_based_sensitivity(self, mitigation):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        observable = {"gradient": {0: 0.8, 1: 0.2}}
        _ = mitigation.create_plan(qc, method="zne", observable=observable)


class TestPlaceholderMitigation:
    """Regression tests for PEC/CDR placeholder warnings (issue #42)."""

    def test_pec_result_is_marked_placeholder(self):
        mitigation = AdaptiveErrorMitigation(CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, method="pec")
        with pytest.warns(UserWarning, match="PEC mitigation is a placeholder"):
            result = mitigation.execute(qc, plan)
        assert result.placeholder is True
        assert result.method == "pec"

    def test_cdr_result_is_marked_placeholder(self):
        mitigation = AdaptiveErrorMitigation(CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, method="cdr")
        with pytest.warns(UserWarning, match="CDR mitigation is a placeholder"):
            result = mitigation.execute(qc, plan)
        assert result.placeholder is True
        assert result.method == "cdr"

    def test_zne_result_is_not_placeholder(self):
        mitigation = AdaptiveErrorMitigation(CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = mitigation.create_plan(qc, method="zne")
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = mitigation.execute(qc, plan)
        assert result.placeholder is False
        assert result.method == "zne"
        assert plan.subcircuit_sensitivity is not None