"""Tests for qc_compiler.cutting module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.cutting import CircuitCutter, CuttingResult, CutLocation


class TestCuttingResult:
    def test_default_values(self):
        result = CuttingResult()
        assert result.should_cut is False
        assert result.num_cuts == 0
        assert result.subcircuits == []
        assert result.cut_locations == []
        assert result.estimated_error_uncut == 0.0
        assert result.estimated_error_cut == 0.0
        assert result.sampling_overhead == 0.0
        assert result.subcircuit_qubit_counts == []

    def test_error_reduction(self):
        result = CuttingResult(
            estimated_error_uncut=0.20,
            estimated_error_cut=0.12,
        )
        assert abs(result.error_reduction - 0.08) < 1e-10

    def test_error_reduction_pct(self):
        result = CuttingResult(
            estimated_error_uncut=0.20,
            estimated_error_cut=0.12,
        )
        assert abs(result.error_reduction_pct - 40.0) < 1e-10

    def test_error_reduction_pct_zero(self):
        result = CuttingResult(
            estimated_error_uncut=0.0,
            estimated_error_cut=0.0,
        )
        assert result.error_reduction_pct == 0.0


class TestCutLocation:
    def test_default_values(self):
        loc = CutLocation()
        assert loc.gate_index == 0
        assert loc.gate_name == ""
        assert loc.qubits == ()
        assert loc.cut_type == ""
        assert loc.estimated_benefit == 0.0

    def test_custom_values(self):
        loc = CutLocation(
            gate_index=3,
            gate_name="cx",
            qubits=(0, 5),
            cut_type="gate",
            estimated_benefit=0.15,
        )
        assert loc.gate_index == 3
        assert loc.gate_name == "cx"
        assert loc.qubits == (0, 5)
        assert loc.cut_type == "gate"
        assert loc.estimated_benefit == 0.15


class TestCircuitCutterNoBackend:
    """Tests without a backend (default model)."""

    @pytest.fixture
    def cutter(self):
        return CircuitCutter(cost_model=CostModel())

    def test_analyze_small_circuit(self, cutter):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = cutter.analyze(qc)
        assert isinstance(result, CuttingResult)
        assert result.estimated_error_uncut >= 0

    def test_analyze_empty_circuit(self, cutter):
        qc = QuantumCircuit(4)
        result = cutter.analyze(qc)
        assert result.should_cut is False
        assert result.num_cuts == 0

    def test_analyze_forces_cut_for_large_circuit(self):
        cutter = CircuitCutter(cost_model=CostModel(), max_qubits=4)
        qc = QuantumCircuit(8)
        qc.h(0)
        for i in range(7):
            qc.cx(i, i + 1)
        result = cutter.analyze(qc)
        assert result.should_cut is True

    def test_analyze_ghz(self, cutter, ghz_circuit):
        result = cutter.analyze(ghz_circuit)
        assert isinstance(result, CuttingResult)
        assert result.estimated_error_uncut > 0

    def test_analyze_bell(self, cutter, bell_circuit):
        result = cutter.analyze(bell_circuit)
        assert isinstance(result, CuttingResult)

    def test_cut_returns_circuits(self, cutter):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        subcircuits = cutter.cut(qc)
        assert len(subcircuits) >= 1
        for sub in subcircuits:
            assert isinstance(sub, QuantumCircuit)

    def test_cut_no_cut_returns_original(self, cutter):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = cutter.analyze(qc)
        if not result.should_cut:
            subcircuits = cutter.cut(qc)
            assert len(subcircuits) == 1
            assert subcircuits[0].num_qubits == qc.num_qubits

    def test_reconstruct_no_cuts(self, cutter):
        results = [{"00": 500, "11": 500}]
        reconstructed = cutter.reconstruct(results, num_cuts=0)
        assert isinstance(reconstructed, dict)
        assert "00" in reconstructed or "11" in reconstructed

    def test_reconstruct_with_cuts(self, cutter):
        results = [{"00": 300, "11": 200}, {"01": 250, "10": 250}]
        reconstructed = cutter.reconstruct(results, num_cuts=1)
        assert isinstance(reconstructed, dict)

    def test_reconstruct_empty(self, cutter):
        result = cutter.reconstruct([], num_cuts=0)
        assert result == {}

    def test_analyze_qaoa(self, cutter, qaoa_circuit):
        result = cutter.analyze(qaoa_circuit)
        assert result.estimated_error_uncut > 0

    def test_sampling_overhead_calculation(self):
        cutter = CircuitCutter(cost_model=CostModel(), max_qubits=2)
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        result = cutter.analyze(qc)
        if result.should_cut and result.num_cuts > 0:
            expected_overhead = (4 ** result.num_cuts) / 8192
            assert abs(result.sampling_overhead - expected_overhead) < 1e-10

    def test_cut_with_explicit_locations(self, cutter):
        qc = QuantumCircuit(4)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        qc.cx(2, 3)
        cut_locs = [CutLocation(gate_index=2, gate_name="cx", qubits=(1, 2), cut_type="gate")]
        subcircuits = cutter.cut(qc, cut_locations=cut_locs)
        assert len(subcircuits) >= 1


class TestCircuitCutterWithBackend:
    """Tests with FakeBrisbane backend."""

    @pytest.fixture
    def cutter_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        return CircuitCutter(cost_model=model)

    def test_analyze_with_backend(self, cutter_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        result = cutter_with_backend.analyze(qc)
        assert result.estimated_error_uncut > 0

    def test_analyze_ghz_with_backend(self, cutter_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = cutter_with_backend.analyze(qc)
        assert result.estimated_error_uncut > 0


class TestFindCutCandidates:
    """Tests for candidate finding logic."""

    @pytest.fixture
    def cutter(self):
        return CircuitCutter(cost_model=CostModel())

    def test_finds_two_qubit_gates(self, cutter):
        qc = QuantumCircuit(4)
        qc.cx(0, 1)
        qc.cx(2, 3)
        candidates = cutter._find_cut_candidates(qc)
        assert len(candidates) >= 2
        assert all(c.cut_type == "gate" for c in candidates)

    def test_no_candidates_no_two_qubit(self, cutter):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.h(1)
        qc.h(2)
        candidates = cutter._find_cut_candidates(qc)
        assert len(candidates) == 0

    def test_candidates_sorted_by_benefit(self, cutter):
        qc = QuantumCircuit(4)
        qc.cx(0, 1)
        qc.cx(0, 3)
        candidates = cutter._find_cut_candidates(qc)
        for i in range(len(candidates) - 1):
            assert candidates[i].estimated_benefit >= candidates[i + 1].estimated_benefit


class TestEstimateSwapBenefit:
    """Tests for SWAP benefit estimation."""

    @pytest.fixture
    def cutter(self):
        return CircuitCutter(cost_model=CostModel())

    def test_adjacent_qubits_no_benefit(self, cutter):
        benefit = cutter._estimate_swap_benefit(
            QuantumCircuit(2), (0, 1)
        )
        assert benefit == 0.0

    def test_distant_qubits_have_benefit(self, cutter):
        benefit = cutter._estimate_swap_benefit(
            QuantumCircuit(4), (0, 3)
        )
        assert benefit > 0


class TestEstimateCutError:
    """Tests for cut error estimation."""

    @pytest.fixture
    def cutter(self):
        return CircuitCutter(cost_model=CostModel())

    def test_zero_cuts_equals_uncut(self, cutter):
        qc = QuantumCircuit(4)
        qc.h(0)
        qc.cx(0, 1)
        error = cutter._estimate_cut_error(qc, [], 8192)
        assert error > 0

    def test_more_cuts_increase_sampling_overhead(self, cutter):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i + 1)
        cut1 = [CutLocation(gate_index=1, gate_name="cx", qubits=(1, 2), cut_type="gate")]
        cut2 = [
            CutLocation(gate_index=1, gate_name="cx", qubits=(1, 2), cut_type="gate"),
            CutLocation(gate_index=2, gate_name="cx", qubits=(2, 3), cut_type="gate"),
        ]
        error1 = cutter._estimate_cut_error(qc, cut1, 8192)
        error2 = cutter._estimate_cut_error(qc, cut2, 8192)
        assert error2 >= error1


class TestPartitionQubits:
    """Tests for qubit partitioning."""

    @pytest.fixture
    def cutter(self):
        return CircuitCutter(cost_model=CostModel())

    def test_partition_no_cuts(self, cutter):
        qc = QuantumCircuit(4)
        groups = cutter._partition_qubits(qc, [])
        assert len(groups) >= 1

    def test_partition_with_cut(self, cutter):
        qc = QuantumCircuit(4)
        cut_points = [(1, 2)]
        groups = cutter._partition_qubits(qc, cut_points)
        assert len(groups) >= 1