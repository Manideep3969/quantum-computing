"""Tests for qc_compiler.cost_model module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel, CircuitMetrics


class TestCostModel:
    def test_compute_metrics_basic_circuit(self):
        cost_model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        metrics = cost_model.compute_metrics(qc)
        assert metrics.num_qubits == 2
        assert metrics.two_qubit_gate_count == 1

    def test_compute_metrics_empty_circuit(self):
        cost_model = CostModel()
        qc = QuantumCircuit(4)
        metrics = cost_model.compute_metrics(qc)
        assert metrics.num_qubits == 4
        assert metrics.depth == 0
        assert metrics.total_gate_count == 0

    def test_estimate_fidelity_not_implemented(self):
        cost_model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            cost_model.estimate_fidelity(qc)


class TestCircuitMetrics:
    def test_default_values(self):
        metrics = CircuitMetrics()
        assert metrics.depth == 0
        assert metrics.num_qubits == 0
        assert metrics.single_qubit_gate_count == 0
        assert metrics.two_qubit_gate_count == 0