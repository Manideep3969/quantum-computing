"""Tests for qc_compiler.autotuning module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.autotuning import AutoTuner, TranspileConfig, AutotuneResult


class TestAutoTuner:
    def test_search_not_implemented(self):
        tuner = AutoTuner(cost_model=CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            tuner.search(qc)

    def test_generate_configurations(self):
        tuner = AutoTuner(cost_model=CostModel())
        configs = tuner._generate_configurations()
        assert len(configs) > 0
        assert all(isinstance(c, TranspileConfig) for c in configs)
        routing_methods = {c.routing_method for c in configs}
        assert "sabre" in routing_methods


class TestTranspileConfig:
    def test_default_values(self):
        config = TranspileConfig()
        assert config.routing_method == "sabre"
        assert config.layout_method == "dense"
        assert config.optimization_level == 3
        assert config.gate_fusion is True
        assert config.scheduling_method == "coherence_aware"


class TestAutotuneResult:
    def test_default_values(self):
        result = AutotuneResult()
        assert result.best_config is None
        assert result.best_estimated_fidelity == 0.0