"""Tests for qc_compiler.batching module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.batching import CircuitBatcher, BatchPlan


class TestCircuitBatcher:
    def test_create_batch_plan_not_implemented(self):
        batcher = CircuitBatcher(cost_model=CostModel())
        circuits = [QuantumCircuit(2), QuantumCircuit(2)]
        with pytest.raises(NotImplementedError):
            batcher.create_batch_plan(circuits)

    def test_group_by_unitary_core_not_implemented(self):
        batcher = CircuitBatcher(cost_model=CostModel())
        circuits = [QuantumCircuit(2)]
        with pytest.raises(NotImplementedError):
            batcher._group_by_unitary_core(circuits)


class TestBatchPlan:
    def test_default_values(self):
        plan = BatchPlan()
        assert plan.batches == []
        assert plan.estimated_speedup == 1.0