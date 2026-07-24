"""Tests for qc_compiler.mitigation module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.mitigation import AdaptiveErrorMitigation, MitigationPlan


class TestAdaptiveErrorMitigation:
    def test_create_plan_not_implemented(self):
        mitigation = AdaptiveErrorMitigation(cost_model=CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            mitigation.create_plan(qc)

    def test_execute_not_implemented(self):
        mitigation = AdaptiveErrorMitigation(cost_model=CostModel())
        plan = MitigationPlan()
        qc = QuantumCircuit(2)
        with pytest.raises(NotImplementedError):
            mitigation.execute(qc, plan)


class TestMitigationPlan:
    def test_default_values(self):
        plan = MitigationPlan()
        assert plan.noise_scales == []
        assert plan.total_shots == 0