"""Tests for qc_compiler.cutting module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.cutting import CircuitCutter, CuttingResult


class TestCircuitCutter:
    def test_analyze_not_implemented(self):
        cutter = CircuitCutter(cost_model=CostModel())
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        with pytest.raises(NotImplementedError):
            cutter.analyze(qc)

    def test_cut_not_implemented(self):
        cutter = CircuitCutter(cost_model=CostModel())
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        with pytest.raises(NotImplementedError):
            cutter.cut(qc)

    def test_reconstruct_not_implemented(self):
        cutter = CircuitCutter(cost_model=CostModel())
        with pytest.raises(NotImplementedError):
            cutter.reconstruct([], num_cuts=1)


class TestCuttingResult:
    def test_default_values(self):
        result = CuttingResult()
        assert result.should_cut is False
        assert result.num_cuts == 0
        assert result.subcircuits == []