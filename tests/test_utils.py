"""Tests for qc_compiler.utils module."""

from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeBrisbane

from qc_compiler.utils import (
    TWO_QUBIT_GATES,
    compute_circuit_depth,
    compute_cnot_count,
    compute_idle_fraction,
    get_avg_gate_time,
    get_backend_properties,
)


class TestTwoQubitGates:
    def test_contains_standard_gates(self):
        assert "cx" in TWO_QUBIT_GATES
        assert "cz" in TWO_QUBIT_GATES
        assert "ecr" in TWO_QUBIT_GATES
        assert "swap" in TWO_QUBIT_GATES

    def test_contains_parametric_two_qubit_gates(self):
        assert "rxx" in TWO_QUBIT_GATES
        assert "rzz" in TWO_QUBIT_GATES
        assert "ryy" in TWO_QUBIT_GATES

    def test_contains_controlled_rotation_gates(self):
        assert "crx" in TWO_QUBIT_GATES
        assert "cry" in TWO_QUBIT_GATES
        assert "crz" in TWO_QUBIT_GATES

    def test_does_not_contain_single_qubit_gates(self):
        assert "h" not in TWO_QUBIT_GATES
        assert "x" not in TWO_QUBIT_GATES
        assert "rz" not in TWO_QUBIT_GATES


class TestGetBackendProperties:
    def test_with_fake_backend(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        assert "backend_name" in props
        assert "num_qubits" in props
        assert "t1_times" in props
        assert "t2_times" in props
        assert "single_qubit_gate_errors" in props
        assert "two_qubit_gate_errors" in props
        assert "readout_errors" in props
        assert "gate_lengths" in props

        assert props["num_qubits"] == 127
        assert isinstance(props["t1_times"], dict)
        assert isinstance(props["t2_times"], dict)
        assert isinstance(props["readout_errors"], dict)

    def test_t1_times_are_positive(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        for qubit, t1 in props["t1_times"].items():
            assert t1 > 0, f"T1 for qubit {qubit} should be positive"

    def test_t2_times_are_positive(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        for qubit, t2 in props["t2_times"].items():
            assert t2 > 0, f"T2 for qubit {qubit} should be positive"

    def test_readout_errors_in_range(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        for qubit, error in props["readout_errors"].items():
            assert 0 <= error <= 1, f"Readout error for qubit {qubit} out of range"

    def test_gate_errors_in_range(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        for key, error in props["single_qubit_gate_errors"].items():
            assert 0 <= error <= 1, f"Single-qubit gate error for {key} out of range"

        for key, error in props["two_qubit_gate_errors"].items():
            assert 0 <= error <= 1, f"Two-qubit gate error for {key} out of range"

    def test_gate_lengths_are_non_negative(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        for key, length in props["gate_lengths"].items():
            assert length >= 0, f"Gate length for {key} should be non-negative"

    def test_gate_lengths_in_seconds(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        for key, length in props["gate_lengths"].items():
            assert length < 1.0, f"Gate length for {key} seems too large (not in seconds?): {length}"

    def test_two_qubit_gate_errors_populated(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        assert len(props["two_qubit_gate_errors"]) > 0

    def test_single_qubit_gate_errors_populated(self):
        backend = FakeBrisbane()
        props = get_backend_properties(backend)

        assert len(props["single_qubit_gate_errors"]) > 0


class TestComputeCircuitDepth:
    def test_empty_circuit(self):
        qc = QuantumCircuit(2)
        assert compute_circuit_depth(qc) == 0

    def test_single_gate(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        assert compute_circuit_depth(qc) == 1

    def test_sequential_gates(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        assert compute_circuit_depth(qc) == 2

    def test_parallel_gates(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        assert compute_circuit_depth(qc) == 1

    def test_ghz_circuit(self):
        qc = QuantumCircuit(5)
        qc.h(0)
        for i in range(4):
            qc.cx(0, i + 1)
        assert compute_circuit_depth(qc) == 5


class TestComputeCnotCount:
    def test_empty_circuit(self):
        qc = QuantumCircuit(2)
        assert compute_cnot_count(qc) == 0

    def test_single_cx(self):
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        assert compute_cnot_count(qc) == 1

    def test_multiple_cx(self):
        qc = QuantumCircuit(3)
        qc.cx(0, 1)
        qc.cx(1, 2)
        assert compute_cnot_count(qc) == 2

    def test_mixed_gates(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.h(1)
        assert compute_cnot_count(qc) == 1

    def test_swap_gates(self):
        qc = QuantumCircuit(2)
        qc.swap(0, 1)
        assert compute_cnot_count(qc) == 1

    def test_cz_gate(self):
        qc = QuantumCircuit(2)
        qc.cz(0, 1)
        assert compute_cnot_count(qc) == 1

    def test_no_two_qubit_gates(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        qc.rz(0.5, 0)
        assert compute_cnot_count(qc) == 0


class TestComputeIdleFraction:
    def test_empty_circuit(self):
        qc = QuantumCircuit(2)
        assert compute_idle_fraction(qc) == 0.0

    def test_fully_active_circuit(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        idle = compute_idle_fraction(qc)
        assert idle == 0.0

    def test_partially_idle_circuit(self):
        qc = QuantumCircuit(3)
        qc.h(0)
        idle = compute_idle_fraction(qc)
        assert idle > 0.0

    def test_single_gate_idle(self):
        qc = QuantumCircuit(4)
        qc.h(0)
        idle = compute_idle_fraction(qc)
        assert abs(idle - 0.75) < 0.01

    def test_bell_circuit_idle(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        idle = compute_idle_fraction(qc)
        assert idle == 0.25

    def test_ghz_circuit_idle(self):
        qc = QuantumCircuit(5)
        qc.h(0)
        for i in range(4):
            qc.cx(0, i + 1)
        idle = compute_idle_fraction(qc)
        assert idle > 0.0


class TestGetAvgGateTime:
    def setup_method(self):
        self.backend = FakeBrisbane()
        self.device_props = get_backend_properties(self.backend)

    def test_single_qubit_gate_time(self):
        avg_time = get_avg_gate_time(self.device_props, gate_type="single")
        assert avg_time > 0
        assert avg_time < 1e-3

    def test_two_qubit_gate_time(self):
        avg_time = get_avg_gate_time(self.device_props, gate_type="two")
        assert avg_time > 0
        assert avg_time < 1e-2

    def test_all_gate_time(self):
        avg_time = get_avg_gate_time(self.device_props, gate_type="all")
        assert avg_time > 0

    def test_two_qubit_slower_than_single(self):
        single_time = get_avg_gate_time(self.device_props, gate_type="single")
        two_time = get_avg_gate_time(self.device_props, gate_type="two")
        assert two_time > single_time

    def test_default_for_empty_props_single(self):
        props = {"gate_lengths": {}}
        avg_time = get_avg_gate_time(props, gate_type="single")
        assert avg_time == 50e-9

    def test_default_for_empty_props_two(self):
        props = {"gate_lengths": {}}
        avg_time = get_avg_gate_time(props, gate_type="two")
        assert avg_time == 300e-9

    def test_default_for_empty_props_all(self):
        props = {"gate_lengths": {}}
        avg_time = get_avg_gate_time(props, gate_type="all")
        assert avg_time == 50e-9

    def test_no_matching_gates_single(self):
        props = {"gate_lengths": {("cx", (0, 1)): 300e-9}}
        avg_time = get_avg_gate_time(props, gate_type="single")
        assert avg_time == 50e-9

    def test_no_matching_gates_two(self):
        props = {"gate_lengths": {("rz", (0,)): 50e-9}}
        avg_time = get_avg_gate_time(props, gate_type="two")
        assert avg_time == 300e-9

    def test_missing_gate_lengths_key(self):
        props = {}
        avg_time = get_avg_gate_time(props, gate_type="single")
        assert avg_time == 50e-9

    def test_missing_gate_lengths_key_two(self):
        props = {}
        avg_time = get_avg_gate_time(props, gate_type="two")
        assert avg_time == 300e-9

    def test_avg_time_with_real_backend(self):
        avg_single = get_avg_gate_time(self.device_props, "single")
        avg_two = get_avg_gate_time(self.device_props, "two")
        avg_all = get_avg_gate_time(self.device_props, "all")
        assert avg_single > 0
        assert avg_two > 0
        assert avg_all > 0
        assert avg_single < avg_two


class TestGetBackendPropertiesEdgeCases:
    """Tests for backend property extraction edge cases."""

    def test_missing_qubit_properties_handled_gracefully(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        backend.num_qubits = 2
        mock_props = MagicMock()
        mock_props.qubit_property.side_effect = Exception("no data")
        mock_props.gates = []
        backend.properties.return_value = mock_props

        props = get_backend_properties(backend)
        assert props["num_qubits"] == 2
        assert props["t1_times"] == {}
        assert props["t2_times"] == {}
        assert props["readout_errors"] == {}
        assert props["single_qubit_gate_errors"] == {}
        assert props["two_qubit_gate_errors"] == {}
        assert props["gate_lengths"] == {}

    def test_partial_qubit_data(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        backend.num_qubits = 3
        backend.name = "test_backend"

        mock_props = MagicMock()

        def qubit_prop(qubit, prop):
            if qubit == 0 and prop == "T1":
                return (1e-4,)
            if qubit == 0 and prop == "T2":
                return (5e-5,)
            if qubit == 0 and prop == "readout_error":
                return (0.02,)
            raise RuntimeError("no data")

        mock_props.qubit_property = qubit_prop
        mock_props.gates = []
        backend.properties.return_value = mock_props

        props = get_backend_properties(backend)
        assert 0 in props["t1_times"]
        assert 0 in props["t2_times"]
        assert 0 in props["readout_errors"]

    def test_gate_length_unit_conversion(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        backend.num_qubits = 1
        backend.name = "test_backend"

        mock_gate_ns = MagicMock()
        mock_gate_ns.gate = "h"
        mock_gate_ns.qubits = [0]
        mock_param = MagicMock()
        mock_param.name = "gate_length"
        mock_param.value = 50.0
        mock_param.unit = "ns"
        mock_gate_ns.parameters = [mock_param]

        mock_props = MagicMock()
        mock_props.qubit_property.side_effect = Exception("no data")
        mock_props.gates = [mock_gate_ns]
        backend.properties.return_value = mock_props

        props = get_backend_properties(backend)
        assert len(props["gate_lengths"]) > 0
        for length in props["gate_lengths"].values():
            assert length > 0