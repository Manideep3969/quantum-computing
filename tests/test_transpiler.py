"""Tests for qc_compiler.transpiler module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.transpiler import QCompiler, OptimizerConfig, QCompilerResult


class TestOptimizerConfig:
    def test_default_values(self):
        config = OptimizerConfig()
        assert config.fusion is True
        assert config.cutting is True
        assert config.mitigation == "adaptive"
        assert config.scheduling == "coherence_aware"
        assert config.batch is True
        assert config.autotune is False

    def test_custom_values(self):
        config = OptimizerConfig(
            fusion=False,
            cutting=False,
            mitigation="zne",
            scheduling="alap",
            batch=False,
            autotune=True,
        )
        assert config.fusion is False
        assert config.cutting is False
        assert config.mitigation == "zne"
        assert config.scheduling == "alap"
        assert config.batch is False
        assert config.autotune is True

    def test_disable_all(self):
        config = OptimizerConfig(
            fusion=False,
            cutting=False,
            mitigation="none",
            scheduling="none",
            batch=False,
            autotune=False,
        )
        assert config.fusion is False
        assert config.cutting is False
        assert config.mitigation == "none"
        assert config.scheduling == "none"


class TestQCompilerResult:
    def test_default_values(self):
        result = QCompilerResult()
        assert result.original_circuit is None
        assert result.optimized_circuit is None
        assert result.fidelity_before == 0.0
        assert result.fidelity_after == 0.0
        assert result.fusion_result is None
        assert result.cutting_result is None
        assert result.schedule_result is None
        assert result.mitigation_plan is None
        assert result.autotune_result is None
        assert result.batch_plan is None
        assert result.passes_applied == []
        assert result.config is None

    def test_fidelity_improvement(self):
        result = QCompilerResult(
            fidelity_before=0.80,
            fidelity_after=0.90,
        )
        assert abs(result.fidelity_improvement - 0.10) < 1e-10

    def test_fidelity_improvement_pct(self):
        result = QCompilerResult(
            fidelity_before=0.80,
            fidelity_after=0.90,
        )
        assert abs(result.fidelity_improvement_pct - 12.5) < 1e-10

    def test_fidelity_improvement_pct_zero(self):
        result = QCompilerResult(
            fidelity_before=0.0,
            fidelity_after=0.0,
        )
        assert result.fidelity_improvement_pct == 0.0


class TestQCompilerNoBackend:
    """Tests without a backend (default model)."""

    @pytest.fixture
    def compiler(self):
        return QCompiler()

    def test_optimize_default_config(self, compiler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = compiler.optimize(qc)
        assert isinstance(result, QCompilerResult)
        assert result.original_circuit is not None
        assert result.optimized_circuit is not None
        assert result.fidelity_before > 0
        assert result.fidelity_after > 0
        assert len(result.passes_applied) > 0

    def test_optimize_preserves_circuit(self, compiler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = compiler.optimize(qc)
        assert result.original_circuit.num_qubits == qc.num_qubits

    def test_optimize_fusion_only(self, compiler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        qc.cx(0, 1)
        config = OptimizerConfig(
            fusion=True,
            cutting=False,
            mitigation="none",
            scheduling="none",
            batch=False,
            autotune=False,
        )
        result = compiler.optimize(qc, config=config)
        assert "fusion" in result.passes_applied
        assert result.fusion_result is not None

    def test_optimize_scheduling_only(self, compiler):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        config = OptimizerConfig(
            fusion=False,
            cutting=False,
            mitigation="none",
            scheduling="coherence_aware",
            batch=False,
            autotune=False,
        )
        result = compiler.optimize(qc, config=config)
        assert "scheduling:coherence_aware" in result.passes_applied
        assert result.schedule_result is not None

    def test_optimize_mitigation_only(self, compiler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        config = OptimizerConfig(
            fusion=False,
            cutting=False,
            mitigation="zne",
            scheduling="none",
            batch=False,
            autotune=False,
        )
        result = compiler.optimize(qc, config=config)
        assert "mitigation:zne" in result.passes_applied
        assert result.mitigation_plan is not None

    def test_optimize_cutting_only(self, compiler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        config = OptimizerConfig(
            fusion=False,
            cutting=True,
            mitigation="none",
            scheduling="none",
            batch=False,
            autotune=False,
        )
        result = compiler.optimize(qc, config=config)
        assert "cutting" in result.passes_applied
        assert result.cutting_result is not None

    def test_optimize_no_passes(self, compiler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        config = OptimizerConfig(
            fusion=False,
            cutting=False,
            mitigation="none",
            scheduling="none",
            batch=False,
            autotune=False,
        )
        result = compiler.optimize(qc, config=config)
        assert len(result.passes_applied) == 0
        assert result.fidelity_before > 0
        assert result.fidelity_after > 0

    def test_optimize_ghz(self, compiler, ghz_circuit):
        result = compiler.optimize(ghz_circuit)
        assert result.fidelity_before > 0
        assert result.fidelity_after > 0

    def test_optimize_qaoa(self, compiler, qaoa_circuit):
        result = compiler.optimize(qaoa_circuit)
        assert result.fidelity_before > 0

    def test_optimize_empty_circuit(self, compiler):
        qc = QuantumCircuit(4)
        result = compiler.optimize(qc)
        assert result.fidelity_before > 0

    def test_optimize_bell(self, compiler, bell_circuit):
        result = compiler.optimize(bell_circuit)
        assert result.fidelity_before > 0
        assert result.fidelity_after > 0

    def test_optimize_full_pipeline(self, compiler):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        config = OptimizerConfig(
            fusion=True,
            cutting=True,
            mitigation="zne",
            scheduling="coherence_aware",
            batch=False,
            autotune=False,
        )
        result = compiler.optimize(qc, config=config)
        assert "fusion" in result.passes_applied
        assert "cutting" in result.passes_applied
        assert "scheduling:coherence_aware" in result.passes_applied
        assert "mitigation:zne" in result.passes_applied


class TestQCompilerBatch:
    """Tests for batch optimization."""

    @pytest.fixture
    def compiler(self):
        return QCompiler()

    def test_optimize_batch(self, compiler):
        circuits = []
        for i in range(3):
            qc = QuantumCircuit(2)
            qc.h(0)
            qc.cx(0, 1)
            circuits.append(qc)

        config = OptimizerConfig(
            fusion=False,
            cutting=False,
            mitigation="none",
            scheduling="none",
            batch=True,
            autotune=False,
        )
        results = compiler.optimize_batch(circuits, config=config)
        assert len(results) == 3
        for r in results:
            assert r.fidelity_before > 0

    def test_optimize_batch_with_batching(self, compiler):
        circuits = []
        for i in range(2):
            qc = QuantumCircuit(2)
            qc.h(0)
            qc.cx(0, 1)
            circuits.append(qc)

        config = OptimizerConfig(
            fusion=True,
            cutting=False,
            mitigation="none",
            scheduling="none",
            batch=True,
            autotune=False,
        )
        results = compiler.optimize_batch(circuits, config=config)
        assert len(results) == 2
        assert all(r.batch_plan is not None for r in results)


class TestQCompilerWithBackend:
    """Tests with FakeBrisbane backend."""

    @pytest.fixture
    def compiler_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        return QCompiler(backend=backend)

    def test_optimize_with_backend(self, compiler_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = compiler_with_backend.optimize(qc)
        assert result.fidelity_before > 0
        assert result.fidelity_after > 0
        assert len(result.passes_applied) > 0

    def test_optimize_fusion_with_backend(self, compiler_with_backend):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        qc.cx(0, 1)
        config = OptimizerConfig(
            fusion=True,
            cutting=False,
            mitigation="none",
            scheduling="none",
            batch=False,
            autotune=False,
        )
        result = compiler_with_backend.optimize(qc, config=config)
        assert result.fusion_result is not None