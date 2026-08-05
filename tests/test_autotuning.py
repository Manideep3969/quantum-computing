"""Tests for qc_compiler.autotuning module."""

import os
import tempfile

import pytest
from qiskit import QuantumCircuit

from qc_compiler.autotuning import AutoTuner, AutotuneResult, TranspileConfig
from qc_compiler.cost_model import CostModel


class TestTranspileConfig:
    def test_default_values(self):
        config = TranspileConfig()
        assert config.routing_method == "sabre"
        assert config.layout_method == "dense"
        assert config.optimization_level == 3
        assert config.seed == 0
        assert config.gate_fusion is True
        assert config.scheduling_method == "coherence_aware"

    def test_custom_values(self):
        config = TranspileConfig(
            routing_method="stochastic",
            layout_method="trivial",
            optimization_level=1,
            seed=42,
            gate_fusion=False,
            scheduling_method="alap",
        )
        assert config.routing_method == "stochastic"
        assert config.layout_method == "trivial"
        assert config.optimization_level == 1
        assert config.seed == 42
        assert config.gate_fusion is False
        assert config.scheduling_method == "alap"

    def test_config_key(self):
        config = TranspileConfig(
            routing_method="sabre",
            layout_method="dense",
            optimization_level=3,
            seed=0,
            gate_fusion=True,
            scheduling_method="coherence_aware",
        )
        key = config.config_key()
        assert "sabre" in key
        assert "dense" in key
        assert "opt3" in key
        assert "seed0" in key
        assert "fusion1" in key
        assert "coherence_aware" in key

    def test_config_key_unique(self):
        config1 = TranspileConfig(optimization_level=1)
        config2 = TranspileConfig(optimization_level=2)
        assert config1.config_key() != config2.config_key()


class TestAutotuneResult:
    def test_default_values(self):
        result = AutotuneResult()
        assert result.best_config is None
        assert result.best_estimated_fidelity == 0.0
        assert result.all_results == {}
        assert result.measured_fidelities == {}
        assert result.circuits_evaluated == 0
        assert result.search_space_size == 0
        assert result.best_circuit is None
        assert result.top_k_configs == []

    def test_improvement_over_default(self):
        result = AutotuneResult(
            best_estimated_fidelity=0.95,
            all_results={"default": 0.85, "best": 0.95},
        )
        assert abs(result.improvement_over_default - 0.10) < 1e-10

    def test_improvement_over_default_no_default(self):
        result = AutotuneResult(
            best_estimated_fidelity=0.95,
            all_results={"best": 0.95},
        )
        assert result.improvement_over_default == 0.0

    def test_num_configs_evaluated(self):
        result = AutotuneResult(
            all_results={"a": 0.9, "b": 0.85, "c": 0.8}
        )
        assert result.num_configs_evaluated == 3


class TestAutoTunerNoBackend:
    """Tests without a backend (default model)."""

    @pytest.fixture
    def tuner(self):
        return AutoTuner(
            cost_model=CostModel(),
            cache_dir=tempfile.mkdtemp(),
        )

    def test_search_returns_result(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = tuner.search(qc, circuit_family="test_bell")
        assert isinstance(result, AutotuneResult)
        assert result.best_config is not None
        assert result.best_estimated_fidelity > 0

    def test_search_ghz(self, tuner, ghz_circuit):
        result = tuner.search(ghz_circuit, circuit_family="test_ghz")
        assert result.best_config is not None
        assert result.best_estimated_fidelity > 0

    def test_search_qaoa(self, tuner, qaoa_circuit):
        result = tuner.search(qaoa_circuit, circuit_family="test_qaoa")
        assert result.best_config is not None

    def test_search_evaluates_configs(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = tuner.search(qc, circuit_family="test_eval")
        assert result.circuits_evaluated > 0
        assert result.search_space_size > 0
        assert len(result.all_results) > 0

    def test_search_top_k(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = tuner.search(qc, top_k=3)
        assert len(result.top_k_configs) <= 3

    def test_search_default_always_evaluated(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = tuner.search(qc)
        assert "default" in result.all_results

    def test_search_caches_result(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result1 = tuner.search(qc, circuit_family="test_cache_family")
        assert result1.best_config is not None

        result2 = tuner.search(qc, circuit_family="test_cache_family")
        assert result2.best_config is not None
        assert "cached" in result2.all_results

    def test_generate_configurations(self, tuner):
        configs = tuner._generate_configurations()
        assert len(configs) > 0
        assert all(isinstance(c, TranspileConfig) for c in configs)
        routing_methods = {c.routing_method for c in configs}
        assert "sabre" in routing_methods
        assert "stochastic" in routing_methods

    def test_estimate_fidelity(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        config = TranspileConfig()
        fidelity = tuner._estimate_fidelity(qc, config)
        assert 0 <= fidelity <= 1.0

    def test_estimate_fidelity_higher_opt_better(self, tuner):
        qc = QuantumCircuit(3)
        qc.h(0)
        for i in range(1, 3):
            qc.cx(0, i)
        config_opt1 = TranspileConfig(optimization_level=1)
        config_opt3 = TranspileConfig(optimization_level=3)
        f1 = tuner._estimate_fidelity(qc, config_opt1)
        f3 = tuner._estimate_fidelity(qc, config_opt3)
        assert f3 >= f1

    def test_estimate_fidelity_fusion_better(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        config_fusion = TranspileConfig(gate_fusion=True)
        config_no_fusion = TranspileConfig(gate_fusion=False)
        f_fusion = tuner._estimate_fidelity(qc, config_fusion)
        f_no_fusion = tuner._estimate_fidelity(qc, config_no_fusion)
        assert f_fusion >= f_no_fusion

    def test_estimate_fidelity_clamped(self, tuner):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        config = TranspileConfig()
        fidelity = tuner._estimate_fidelity(qc, config)
        assert 0.0 <= fidelity <= 1.0


class TestAutoTunerCaching:
    """Tests for caching functionality."""

    @pytest.fixture
    def tuner_with_cache(self):
        cache_dir = tempfile.mkdtemp()
        return AutoTuner(cost_model=CostModel(), cache_dir=cache_dir)

    def test_cache_result(self, tuner_with_cache):
        config = TranspileConfig(optimization_level=2)
        tuner_with_cache._cache_result("test_cache", config, 0.95)
        cache_file = os.path.join(
            tuner_with_cache.cache_dir, "test_cache.json"
        )
        assert os.path.exists(cache_file)

    def test_load_cached(self, tuner_with_cache):
        config = TranspileConfig(optimization_level=2)
        tuner_with_cache._cache_result("test_load", config, 0.95)
        loaded = tuner_with_cache._load_cached("test_load")
        assert loaded is not None
        assert loaded.optimization_level == 2

    def test_load_cached_not_found(self, tuner_with_cache):
        loaded = tuner_with_cache._load_cached("nonexistent")
        assert loaded is None

    def test_cache_round_trip(self, tuner_with_cache):
        config = TranspileConfig(
            routing_method="sabre",
            layout_method="dense",
            optimization_level=3,
            seed=1,
            gate_fusion=True,
            scheduling_method="coherence_aware",
        )
        tuner_with_cache._cache_result("test_roundtrip", config, 0.92)
        loaded = tuner_with_cache._load_cached("test_roundtrip")
        assert loaded is not None
        assert loaded.routing_method == config.routing_method
        assert loaded.layout_method == config.layout_method
        assert loaded.optimization_level == config.optimization_level
        assert loaded.seed == config.seed
        assert loaded.gate_fusion == config.gate_fusion
        assert loaded.scheduling_method == config.scheduling_method


class TestAutoTunerWithBackend:
    """Tests with FakeBrisbane backend."""

    @pytest.fixture
    def tuner_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        return AutoTuner(
            cost_model=model,
            backend=backend,
            cache_dir=tempfile.mkdtemp(),
        )

    def test_search_with_backend(self, tuner_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = tuner_with_backend.search(
            qc, circuit_family="test_backend_ghz"
        )
        assert result.best_config is not None
        assert result.best_estimated_fidelity > 0

    def test_search_with_backend_caches(self, tuner_with_backend):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        _ = tuner_with_backend.search(
            qc, circuit_family="test_backend_cache"
        )
        result2 = tuner_with_backend.search(
            qc, circuit_family="test_backend_cache"
        )
        assert "cached" in result2.all_results