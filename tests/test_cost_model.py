"""Tests for qc_compiler.cost_model module."""

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT

from qc_compiler.cost_model import CostModel, CircuitMetrics, ErrorBreakdown, DeviceCharacterization


class TestDeviceCharacterization:
    def test_default_values(self):
        device = DeviceCharacterization()
        assert device.backend_name == ""
        assert device.num_qubits == 0
        assert device.t1_times == {}
        assert device.t2_times == {}
        assert device.single_qubit_gate_errors == {}
        assert device.two_qubit_gate_errors == {}
        assert device.readout_errors == {}
        assert device.gate_lengths == {}

    def test_custom_values(self):
        device = DeviceCharacterization(
            backend_name="fake_brisbane",
            num_qubits=127,
            t1_times={0: 0.0002, 1: 0.0003},
            t2_times={0: 0.0001, 1: 0.00015},
            readout_errors={0: 0.02, 1: 0.03},
        )
        assert device.backend_name == "fake_brisbane"
        assert device.num_qubits == 127
        assert device.t1_times[0] == 0.0002
        assert device.readout_errors[1] == 0.03


class TestCircuitMetrics:
    def test_default_values(self):
        metrics = CircuitMetrics()
        assert metrics.depth == 0
        assert metrics.num_qubits == 0
        assert metrics.single_qubit_gate_count == 0
        assert metrics.two_qubit_gate_count == 0
        assert metrics.total_gate_count == 0
        assert metrics.gate_counts == {}

    def test_bell_circuit(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        metrics = CostModel().compute_metrics(qc)
        assert metrics.num_qubits == 2
        assert metrics.two_qubit_gate_count == 1
        assert metrics.single_qubit_gate_count == 1
        assert metrics.total_gate_count == 2


class TestCostModelNoBackend:
    """Tests for CostModel without a backend (default model)."""

    def test_init_no_backend(self):
        model = CostModel()
        assert model.device.backend_name == ""
        assert model.device.num_qubits == 0

    def test_compute_metrics_empty_circuit(self):
        model = CostModel()
        qc = QuantumCircuit(4)
        metrics = model.compute_metrics(qc)
        assert metrics.depth == 0
        assert metrics.num_qubits == 4
        assert metrics.total_gate_count == 0
        assert metrics.single_qubit_gate_count == 0
        assert metrics.two_qubit_gate_count == 0

    def test_compute_metrics_bell_state(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        metrics = model.compute_metrics(qc)
        assert metrics.num_qubits == 2
        assert metrics.depth == 2
        assert metrics.two_qubit_gate_count == 1
        assert metrics.single_qubit_gate_count == 1
        assert metrics.total_gate_count == 2
        assert metrics.gate_counts == {"h": 1, "cx": 1}

    def test_compute_metrics_ghz_state(self):
        model = CostModel()
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        metrics = model.compute_metrics(qc)
        assert metrics.two_qubit_gate_count == 3
        assert metrics.single_qubit_gate_count == 1
        assert metrics.depth > 0

    def test_compute_metrics_qft(self):
        model = CostModel()
        qc = QFT(4, do_swaps=True).decompose()
        metrics = model.compute_metrics(qc)
        assert metrics.num_qubits == 4
        assert metrics.two_qubit_gate_count > 0
        assert metrics.total_gate_count > 0

    def test_gate_error_bell_state(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        error = model.estimate_gate_error(qc)
        assert 0 < error < 1
        expected = 1.0 - (0.9995 * 0.99)
        assert abs(error - expected) < 1e-10

    def test_gate_error_empty_circuit(self):
        model = CostModel()
        qc = QuantumCircuit(4)
        error = model.estimate_gate_error(qc)
        assert error == 0.0

    def test_gate_error_increases_with_gates(self):
        model = CostModel()
        qc_small = QuantumCircuit(2)
        qc_small.h(0)
        qc_small.cx(0, 1)

        qc_large = QuantumCircuit(2)
        qc_large.h(0)
        qc_large.cx(0, 1)
        qc_large.cx(1, 0)
        qc_large.h(1)

        error_small = model.estimate_gate_error(qc_small)
        error_large = model.estimate_gate_error(qc_large)
        assert error_large > error_small

    def test_decoherence_error_bell_state(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        error = model.estimate_decoherence_error(qc)
        assert 0 <= error < 1

    def test_decoherence_error_empty_circuit(self):
        model = CostModel()
        qc = QuantumCircuit(4)
        error = model.estimate_decoherence_error(qc)
        assert error == 0.0

    def test_measurement_error_bell_state(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()
        error = model.estimate_measurement_error(qc)
        assert 0 < error < 1
        expected = 1.0 - (1.0 - 0.015) ** 2
        assert abs(error - expected) < 1e-10

    def test_measurement_error_no_measure(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        error = model.estimate_measurement_error(qc)
        assert error > 0

    def test_fidelity_bell_state(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()
        breakdown = model.estimate_fidelity(qc)
        assert 0 < breakdown.gate_fidelity < 1
        assert 0 < breakdown.decoherence_fidelity <= 1
        assert 0 < breakdown.measurement_fidelity < 1
        assert 0 < breakdown.total_fidelity < 1
        assert abs(breakdown.total_fidelity - breakdown.gate_fidelity * breakdown.decoherence_fidelity * breakdown.measurement_fidelity) < 1e-10

    def test_fidelity_components_multiply(self):
        model = CostModel()
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        qc.measure_all()
        breakdown = model.estimate_fidelity(qc)
        expected = (
            breakdown.gate_fidelity
            * breakdown.decoherence_fidelity
            * breakdown.measurement_fidelity
        )
        assert abs(breakdown.total_fidelity - expected) < 1e-10


class TestCostModelWithBackend:
    """Tests for CostModel with a real backend (using FakeBrisbane)."""

    @pytest.fixture
    def fake_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        return FakeBrisbane()

    def test_init_with_backend(self, fake_backend):
        model = CostModel(backend=fake_backend)
        assert model.device.backend_name == "fake_brisbane"
        assert model.device.num_qubits == 127
        assert len(model.device.t1_times) > 0
        assert len(model.device.t2_times) > 0
        assert len(model.device.readout_errors) > 0

    def test_compute_metrics_with_backend(self, fake_backend):
        model = CostModel(backend=fake_backend)
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        metrics = model.compute_metrics(qc)
        assert metrics.num_qubits == 2
        assert metrics.two_qubit_gate_count == 1

    def test_gate_error_with_backend(self, fake_backend):
        model = CostModel(backend=fake_backend)
        from qiskit import transpile
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        tqc = transpile(qc, backend=fake_backend, optimization_level=0)
        error = model.estimate_gate_error(tqc)
        assert 0 < error < 1

    def test_decoherence_error_with_backend(self, fake_backend):
        model = CostModel(backend=fake_backend)
        from qiskit import transpile
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        tqc = transpile(qc, backend=fake_backend, optimization_level=0)
        error = model.estimate_decoherence_error(tqc)
        assert 0 <= error < 1

    def test_fidelity_with_backend(self, fake_backend):
        model = CostModel(backend=fake_backend)
        from qiskit import transpile
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()
        tqc = transpile(qc, backend=fake_backend, optimization_level=0)
        breakdown = model.estimate_fidelity(tqc)
        assert 0 < breakdown.total_fidelity < 1
        assert breakdown.gate_fidelity > 0
        assert breakdown.decoherence_fidelity > 0
        assert breakdown.measurement_fidelity > 0


class TestCompareCircuits:
    """Tests for circuit comparison functionality."""

    def test_compare_different_depths(self):
        model = CostModel()
        qc_shallow = QuantumCircuit(4)
        qc_shallow.h(0)

        qc_deep = QuantumCircuit(4)
        qc_deep.h(0)
        for i in range(1, 4):
            qc_deep.cx(0, i)

        results = model.compare_circuits([qc_shallow, qc_deep])
        assert len(results) == 2
        assert results[0].total_fidelity > results[1].total_fidelity

    def test_compare_same_circuit(self):
        model = CostModel()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()

        results = model.compare_circuits([qc, qc])
        assert len(results) == 2
        assert abs(results[0].total_fidelity - results[1].total_fidelity) < 1e-10


class TestErrorBreakdown:
    def test_default_values(self):
        breakdown = ErrorBreakdown()
        assert breakdown.gate_fidelity == 1.0
        assert breakdown.decoherence_fidelity == 1.0
        assert breakdown.measurement_fidelity == 1.0
        assert breakdown.total_fidelity == 1.0