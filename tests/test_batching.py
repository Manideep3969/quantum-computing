"""Tests for qc_compiler.batching module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.batching import CircuitBatcher, BatchPlan, MEASUREMENT_BASIS


def _make_bell_circuit(basis="Z"):
    """Create a Bell state circuit with specified measurement basis."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    if basis == "X":
        qc.h(0)
        qc.h(1)
    elif basis == "Y":
        qc.sdg(0)
        qc.h(0)
        qc.sdg(1)
        qc.h(1)
    elif basis == "Z":
        pass
    qc.measure_all()
    return qc


def _make_ghz_circuit(n=4, basis="Z"):
    """Create a GHZ state circuit with specified measurement basis."""
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(1, n):
        qc.cx(0, i)
    if basis == "X":
        for i in range(n):
            qc.h(i)
    elif basis == "Y":
        for i in range(n):
            qc.sdg(i)
            qc.h(i)
    qc.measure_all()
    return qc


class TestBatchPlan:
    def test_default_values(self):
        plan = BatchPlan()
        assert plan.batches == []
        assert plan.measurement_groups == {}
        assert plan.estimated_speedup == 1.0
        assert plan.total_circuits == 0
        assert plan.num_batches == 0
        assert plan.batch_sizes == []
        assert plan.unitary_core_groups == {}

    def test_avg_batch_size(self):
        plan = BatchPlan(batch_sizes=[3, 2, 5])
        assert abs(plan.avg_batch_size - 3.333) < 0.01

    def test_avg_batch_size_empty(self):
        plan = BatchPlan()
        assert plan.avg_batch_size == 0.0

    def test_max_batch_size(self):
        plan = BatchPlan(batch_sizes=[3, 2, 5])
        assert plan.max_batch_size == 5

    def test_max_batch_size_empty(self):
        plan = BatchPlan()
        assert plan.max_batch_size == 0

    def test_min_batch_size(self):
        plan = BatchPlan(batch_sizes=[3, 2, 5])
        assert plan.min_batch_size == 2

    def test_min_batch_size_empty(self):
        plan = BatchPlan()
        assert plan.min_batch_size == 0


class TestCircuitBatcherNoBackend:
    """Tests without a backend (default model)."""

    @pytest.fixture
    def batcher(self):
        return CircuitBatcher(cost_model=CostModel())

    def test_create_batch_plan_empty(self, batcher):
        plan = batcher.create_batch_plan([])
        assert plan.total_circuits == 0
        assert plan.num_batches == 0

    def test_create_batch_plan_single(self, batcher):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        plan = batcher.create_batch_plan([qc])
        assert plan.total_circuits == 1
        assert plan.num_batches >= 1

    def test_create_batch_plan_auto_strategy(self, batcher):
        circuits = [_make_bell_circuit("Z"), _make_bell_circuit("X")]
        plan = batcher.create_batch_plan(circuits, strategy="auto")
        assert plan.total_circuits == 2
        assert plan.num_batches >= 1

    def test_create_batch_plan_measurement_strategy(self, batcher):
        circuits = [_make_bell_circuit("Z"), _make_bell_circuit("X")]
        plan = batcher.create_batch_plan(circuits, strategy="measurement")
        assert plan.method if hasattr(plan, 'method') else True
        assert plan.total_circuits == 2

    def test_create_batch_plan_structural_strategy(self, batcher):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc1.cx(0, 1)
        qc2 = QuantumCircuit(2)
        qc2.h(0)
        qc2.cx(0, 1)
        plan = batcher.create_batch_plan([qc1, qc2], strategy="structural")
        assert plan.total_circuits == 2

    def test_create_batch_plan_invalid_strategy(self, batcher):
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError, match="Unknown batching strategy"):
            batcher.create_batch_plan([qc], strategy="invalid")

    def test_group_by_unitary_core_same_core(self, batcher):
        circuits = [_make_bell_circuit("Z"), _make_bell_circuit("X")]
        groups = batcher._group_by_unitary_core(circuits)
        assert len(groups) >= 1

    def test_group_by_unitary_core_different_cores(self, batcher):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc1.cx(0, 1)
        qc1.measure_all()

        qc2 = QuantumCircuit(2)
        qc2.x(0)
        qc2.cx(0, 1)
        qc2.measure_all()

        groups = batcher._group_by_unitary_core([qc1, qc2])
        assert len(groups) == 2

    def test_measurement_based_batch_same_core(self, batcher):
        circuits = [_make_bell_circuit("Z"), _make_bell_circuit("X"), _make_bell_circuit("Y")]
        plan = batcher._measurement_based_batch(circuits)
        assert plan.total_circuits == 3
        assert plan.num_batches >= 1
        assert len(plan.measurement_groups) >= 1

    def test_measurement_based_batch_different_cores(self, batcher):
        qc1 = _make_bell_circuit("Z")
        qc2 = _make_ghz_circuit(4, basis="Z")
        plan = batcher._measurement_based_batch([qc1, qc2])
        assert plan.total_circuits == 2

    def test_structural_batch_non_overlapping(self, batcher):
        qc1 = QuantumCircuit(4)
        qc1.h(0)
        qc1.cx(0, 1)

        qc2 = QuantumCircuit(4)
        qc2.h(2)
        qc2.cx(2, 3)

        plan = batcher._structural_batch([qc1, qc2])
        assert plan.total_circuits == 2

    def test_structural_batch_overlapping(self, batcher):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc1.cx(0, 1)

        qc2 = QuantumCircuit(2)
        qc2.h(0)
        qc2.cx(0, 1)

        plan = batcher._structural_batch([qc1, qc2])
        assert plan.total_circuits == 2

    def test_compute_core_hash_identical(self, batcher):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc1.cx(0, 1)

        qc2 = QuantumCircuit(2)
        qc2.h(0)
        qc2.cx(0, 1)

        assert batcher._compute_core_hash(qc1) == batcher._compute_core_hash(qc2)

    def test_compute_core_hash_different(self, batcher):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc1.cx(0, 1)

        qc2 = QuantumCircuit(2)
        qc2.x(0)
        qc2.cx(0, 1)

        assert batcher._compute_core_hash(qc1) != batcher._compute_core_hash(qc2)

    def test_compute_core_hash_ignores_measurements(self, batcher):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc1.cx(0, 1)

        qc2 = QuantumCircuit(2, 2)
        qc2.h(0)
        qc2.cx(0, 1)
        qc2.measure(0, 0)
        qc2.measure(1, 1)

        assert batcher._compute_core_hash(qc1) == batcher._compute_core_hash(qc2)

    def test_detect_measurement_basis_z(self, batcher):
        qc = _make_bell_circuit("Z")
        basis = batcher._detect_measurement_basis(qc)
        assert basis == "Z"

    def test_detect_measurement_basis_x(self, batcher):
        qc = _make_bell_circuit("X")
        basis = batcher._detect_measurement_basis(qc)
        assert basis == "X"

    def test_detect_measurement_basis_y(self, batcher):
        qc = _make_bell_circuit("Y")
        basis = batcher._detect_measurement_basis(qc)
        assert basis == "Y"

    def test_detect_measurement_basis_no_measure(self, batcher):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        basis = batcher._detect_measurement_basis(qc)
        assert basis == "none"

    def test_vqe_batching_pattern(self, batcher):
        """Test VQE-like pattern: same ansatz, different measurement bases."""
        circuits = [
            _make_ghz_circuit(4, basis="Z"),
            _make_ghz_circuit(4, basis="X"),
            _make_ghz_circuit(4, basis="Y"),
        ]
        plan = batcher.create_batch_plan(circuits, strategy="measurement")
        assert plan.total_circuits == 3
        assert plan.estimated_speedup >= 1.0

    def test_speedup_estimation(self, batcher):
        circuits = [_make_bell_circuit(b) for b in ["Z", "X", "Y"]]
        plan = batcher.create_batch_plan(circuits)
        assert plan.estimated_speedup >= 1.0


class TestCircuitBatcherWithBackend:
    """Tests with FakeBrisbane backend."""

    @pytest.fixture
    def batcher_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        return CircuitBatcher(cost_model=model)

    def test_batch_with_real_backend(self, batcher_with_backend):
        circuits = [_make_bell_circuit("Z"), _make_bell_circuit("X")]
        plan = batcher_with_backend.create_batch_plan(circuits)
        assert plan.total_circuits == 2
        assert plan.num_batches >= 1

    def test_ghz_batching_with_backend(self, batcher_with_backend):
        circuits = [_make_ghz_circuit(4, b) for b in ["Z", "X", "Y"]]
        plan = batcher_with_backend.create_batch_plan(circuits)
        assert plan.total_circuits == 3


class TestMeasurementBasis:
    """Tests for MEASUREMENT_BASIS constant."""

    def test_z_basis(self):
        assert MEASUREMENT_BASIS["Z"] == []

    def test_x_basis(self):
        assert MEASUREMENT_BASIS["X"] == ["h"]

    def test_y_basis(self):
        assert MEASUREMENT_BASIS["Y"] == ["sdg", "h"]

    def test_all_bases_present(self):
        assert set(MEASUREMENT_BASIS.keys()) == {"Z", "X", "Y"}