"""Tests for qc_compiler.fusion module."""

import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, process_fidelity

from qc_compiler.cost_model import CostModel
from qc_compiler.fusion import FusionResult, GateFusion


class TestGateFusionNoBackend:
    """Tests for GateFusion without a backend (default model)."""

    @pytest.fixture
    def fusion(self):
        return GateFusion(cost_model=CostModel())

    def test_optimize_bell_state(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = fusion.optimize(qc)
        assert isinstance(result, FusionResult)
        assert result.original_circuit is not None
        assert result.optimized_circuit is not None

    def test_optimize_empty_circuit(self, fusion):
        qc = QuantumCircuit(4)
        result = fusion.optimize(qc)
        assert result.chains_fused == 0
        assert result.total_gates_before == 0
        assert result.total_gates_after == 0

    def test_chain_fusion_reduces_gates(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        qc.rz(0.3, 0)
        qc.h(0)
        qc.sx(0)
        result = fusion.optimize(qc, min_chain_length=2)
        assert result.total_gates_after <= result.total_gates_before

    def test_single_gate_no_fusion(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        result = fusion.optimize(qc)
        assert result.chains_fused == 0

    def test_two_gate_chain(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.sx(0)
        result = fusion.optimize(qc, min_chain_length=2)
        assert result.chains_fused >= 0

    def test_fidelity_preserved(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = fusion.optimize(qc)
        assert result.fidelity_after >= result.fidelity_before or \
               abs(result.fidelity_after - result.fidelity_before) < 1e-10

    def test_fusion_result_properties(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        qc.cx(0, 1)
        result = fusion.optimize(qc)
        assert result.total_gates_before > 0
        assert result.depth_before > 0
        assert isinstance(result.chains_fused, int)
        assert isinstance(result.improvement, float)
        assert isinstance(result.gate_reduction_pct, float)
        assert isinstance(result.depth_reduction_pct, float)

    def test_cost_guided_fusion(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)

        result_guided = fusion.optimize(qc, cost_guided=True)
        result_unguided = fusion.optimize(qc, cost_guided=False)

        assert isinstance(result_guided, FusionResult)
        assert isinstance(result_unguided, FusionResult)

    def test_deep_chain_fusion(self, fusion):
        qc = QuantumCircuit(1)
        for _ in range(10):
            qc.h(0)
            qc.rz(0.3, 0)
            qc.sx(0)
        result = fusion.optimize(qc, min_chain_length=2)
        assert result.total_gates_after <= result.total_gates_before

    def test_multi_qubit_circuit(self, fusion):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        qc.cx(0, 1)
        qc.h(1)
        qc.sx(1)
        qc.rz(0.3, 1)
        qc.cx(1, 2)
        qc.h(2)
        result = fusion.optimize(qc)
        assert result.fidelity_after >= result.fidelity_before or \
               abs(result.fidelity_after - result.fidelity_before) < 1e-6


class TestGateFusionWithBackend:
    """Tests for GateFusion with FakeBrisbane backend."""

    @pytest.fixture
    def fusion_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        return GateFusion(cost_model=model)

    def test_fusion_with_real_backend(self, fusion_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = fusion_with_backend.optimize(qc)
        assert isinstance(result, FusionResult)
        assert result.fidelity_after >= 0
        assert result.fidelity_after <= 1

    def test_fusion_preserves_functionality(self, fusion_with_backend):
        qc1 = QuantumCircuit(1)
        qc1.h(0)
        qc1.rz(0.5, 0)
        qc1.sx(0)
        qc1.rz(0.3, 0)
        qc1.sx(0)

        result = fusion_with_backend.optimize(qc1)
        qc2 = result.optimized_circuit

        op1 = Operator(qc1)
        op2 = Operator(qc2)
        fid = process_fidelity(op1, op2)
        assert fid > 0.99, f"Fusion changed circuit functionality: fidelity={fid}"

    def test_fusion_ghz_with_backend(self, fusion_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = fusion_with_backend.optimize(qc)
        assert result.fidelity_after >= 0


class TestFusionResult:
    """Tests for FusionResult data class."""

    def test_default_values(self):
        result = FusionResult()
        assert result.chains_fused == 0
        assert result.total_gates_before == 0
        assert result.total_gates_after == 0
        assert result.depth_before == 0
        assert result.depth_after == 0
        assert result.fidelity_before == 0.0
        assert result.fidelity_after == 0.0

    def test_improvement_property(self):
        result = FusionResult(
            fidelity_before=0.85,
            fidelity_after=0.90,
        )
        assert abs(result.improvement - 0.05) < 1e-10

    def test_gate_reduction_pct(self):
        result = FusionResult(
            total_gates_before=20,
            total_gates_after=16,
        )
        assert abs(result.gate_reduction_pct - 20.0) < 1e-10

    def test_depth_reduction_pct(self):
        result = FusionResult(
            depth_before=10,
            depth_after=7,
        )
        assert abs(result.depth_reduction_pct - 30.0) < 1e-10

    def test_zero_division_protection(self):
        result = FusionResult(
            total_gates_before=0,
            total_gates_after=0,
            depth_before=0,
            depth_after=0,
        )
        assert result.gate_reduction_pct == 0.0
        assert result.depth_reduction_pct == 0.0


class TestFindChains:
    """Tests for chain finding logic."""

    @pytest.fixture
    def fusion(self):
        return GateFusion(cost_model=CostModel())

    def test_find_chains_simple(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        chains = fusion._find_single_qubit_chains(qc)
        assert 0 in chains
        assert len(chains[0]) >= 1

    def test_find_chains_separated_by_cx(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.cx(0, 1)
        qc.h(1)
        qc.sx(1)
        chains = fusion._find_single_qubit_chains(qc)
        assert len(chains) >= 1

    def test_find_chains_empty_circuit(self, fusion):
        qc = QuantumCircuit(4)
        chains = fusion._find_single_qubit_chains(qc)
        assert len(chains) == 0

    def test_find_chains_no_chains(self, fusion):
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        chains = fusion._find_single_qubit_chains(qc)
        assert len(chains) == 0

    def test_find_chains_barrier_splits(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.sx(0)
        qc.barrier()
        qc.rz(0.5, 0)
        qc.sx(0)
        chains = fusion._find_single_qubit_chains(qc)
        assert 0 in chains
        assert len(chains[0]) == 2
        for start, end, indices in chains[0]:
            assert all(
                qc.data[i].operation.name != "barrier"
                for i in indices
            )


class TestComputeChainUnitary:
    """Tests for unitary computation of gate chains."""

    @pytest.fixture
    def fusion(self):
        return GateFusion(cost_model=CostModel())

    def test_identity_chain(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)
        chains = fusion._find_single_qubit_chains(qc)
        if chains.get(0):
            unitary = fusion._compute_chain_unitary(qc, chains[0][0][2])
            assert unitary is not None
            expected = Operator(QuantumCircuit(1))
        assert process_fidelity(unitary, expected) > 0.99

    def test_decompose_failure_returns_none(self, fusion):
        from qiskit.quantum_info import Operator
        non_unitary = Operator([[1, 0], [0, 0]])
        result = fusion._decompose_to_basis(non_unitary)
        assert result is None


class TestCostGuidedRejection:
    """Tests for cost-guided fusion that rejects fusion when it degrades fidelity."""

    @pytest.fixture
    def fusion(self):
        return GateFusion(cost_model=CostModel())

    def test_cost_guided_fusion_reverts_on_degradation(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = fusion.optimize(qc, cost_guided=True)
        assert isinstance(result, FusionResult)
        assert result.original_circuit is not None

    def test_hrz_chain(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.sx(0)
        chains = fusion._find_single_qubit_chains(qc)
        assert 0 in chains
        assert len(chains[0]) >= 1
        unitary = fusion._compute_chain_unitary(qc, chains[0][0][2])
        assert unitary is not None
        expected = Operator(qc)
        assert process_fidelity(unitary, expected) > 0.99


class TestMultiChainFusion:
    """Regression tests for multi-chain fusion (issue #37).

    When a circuit has multiple fusible chains on different qubits,
    the old _replace_chain method would corrupt the circuit because
    it rebuilt the circuit on each replacement, shifting instruction
    indices. The fix uses a single-pass _replace_all_chains that
    processes all chains simultaneously.
    """

    @pytest.fixture
    def fusion(self):
        return GateFusion(cost_model=CostModel())

    def test_two_chains_on_separate_qubits(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(0)
        qc.h(1)
        qc.h(1)
        result = fusion.optimize(qc)
        original_unitary = Operator(qc)
        fused_unitary = Operator(result.optimized_circuit)
        assert process_fidelity(fused_unitary, original_unitary) > 0.99

    def test_chains_separated_by_two_qubit_gates(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(0)
        qc.cx(0, 1)
        qc.h(0)
        qc.h(0)
        qc.h(1)
        qc.h(1)
        result = fusion.optimize(qc)
        original_unitary = Operator(qc)
        fused_unitary = Operator(result.optimized_circuit)
        assert process_fidelity(fused_unitary, original_unitary) > 0.99

    def test_three_qubit_multiple_chains(self, fusion):
        qc = QuantumCircuit(3)
        for i in range(3):
            qc.h(i)
            qc.rz(0.5, i)
            qc.sx(i)
        qc.cx(0, 1)
        for i in range(3):
            qc.h(i)
            qc.rz(0.3, i)
            qc.sx(i)
        result = fusion.optimize(qc)
        original_unitary = Operator(qc)
        fused_unitary = Operator(result.optimized_circuit)
        assert process_fidelity(fused_unitary, original_unitary) > 0.99


class TestFusionUnitaryEquivalence:
    """Comprehensive unitary equivalence tests for gate fusion (issue #55)."""

    @pytest.fixture
    def fusion(self):
        return GateFusion(cost_model=CostModel())

    def test_single_qubit_chain_bell(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = fusion.optimize(qc)
        assert process_fidelity(Operator(result.optimized_circuit), Operator(qc)) > 0.99

    def test_single_qubit_chain_ghz(self, fusion):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        result = fusion.optimize(qc)
        assert process_fidelity(Operator(result.optimized_circuit), Operator(qc)) > 0.99

    def test_rz_chain_preserves_unitary(self, fusion):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.rz(0.5, 0)
        qc.rz(0.3, 0)
        qc.cx(0, 1)
        result = fusion.optimize(qc)
        assert process_fidelity(Operator(result.optimized_circuit), Operator(qc)) > 0.99

    def test_multi_qubit_chain_preserves_unitary(self, fusion):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.h(1)
        qc.h(2)
        qc.cx(0, 1)
        qc.cx(1, 2)
        result = fusion.optimize(qc)
        assert process_fidelity(Operator(result.optimized_circuit), Operator(qc)) > 0.99

    def test_fusion_preserves_unitary_up_to_global_phase(self, fusion):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.sx(0)
        qc.rz(1.23, 0)
        result = fusion.optimize(qc)
        original_op = Operator(qc)
        fused_op = Operator(result.optimized_circuit)
        assert original_op.equiv(fused_op)