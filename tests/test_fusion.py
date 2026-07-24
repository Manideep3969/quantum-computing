"""Tests for qc_compiler.fusion module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.fusion import GateFusion


class TestGateFusion:
    def test_optimize_not_implemented(self):
        fusion = GateFusion(cost_model=CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            fusion.optimize(qc)

    def test_fuse_single_qubit_chains_not_implemented(self):
        fusion = GateFusion(cost_model=CostModel())
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.z(0)
        with pytest.raises(NotImplementedError):
            fusion._fuse_single_qubit_chains(qc)

    def test_absorb_into_two_qubit_not_implemented(self):
        fusion = GateFusion(cost_model=CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            fusion._absorb_into_two_qubit(qc)