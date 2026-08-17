"""Shared utilities for qc-compiler.

Provides helper functions for circuit analysis and backend property
extraction used across all optimization modules.
"""

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2

TWO_QUBIT_GATES = {"cx", "cz", "ecr", "swap", "rxx", "rzz", "ryy", "crx", "cry", "crz"}


def get_backend_properties(backend: BackendV2) -> dict:
    """Extract calibration properties from a quantum backend.

    Handles both real IBM Quantum backends and fake (simulated) backends.
    Returns a structured dictionary with all device parameters needed
    by the cost model.

    Args:
        backend: A Qiskit BackendV2 instance (e.g., FakeBrisbane,
                 or a real backend from QiskitRuntimeService).

    Returns:
        Dictionary with keys:
            - backend_name: str
            - num_qubits: int
            - t1_times: dict[int, float] (qubit -> T1 in seconds)
            - t2_times: dict[int, float] (qubit -> T2 in seconds)
            - single_qubit_gate_errors: dict[tuple[str, int], float]
            - two_qubit_gate_errors: dict[tuple[str, tuple[int, ...]], float]
            - readout_errors: dict[int, float] (qubit -> readout error)
            - gate_lengths: dict[tuple[str, tuple[int, ...]], float]
                            (gate+qubits -> duration in seconds)
    """
    props = backend.properties()

    t1_times = {}
    t2_times = {}
    readout_errors = {}

    for qubit in range(backend.num_qubits):
        try:
            t1_val = props.qubit_property(qubit, "T1")[0]
            t1_times[qubit] = float(t1_val)
        except Exception:  # noqa: S110, BLE001
            pass

        try:
            t2_val = props.qubit_property(qubit, "T2")[0]
            t2_times[qubit] = float(t2_val)
        except Exception:  # noqa: S110, BLE001
            pass

        try:
            ro_val = props.qubit_property(qubit, "readout_error")[0]
            readout_errors[qubit] = float(ro_val)
        except Exception:  # noqa: S110, BLE001
            pass

    single_qubit_gate_errors = {}
    two_qubit_gate_errors = {}
    gate_lengths = {}

    for gate in props.gates:
        gate_name = gate.gate
        qubits = tuple(gate.qubits)
        gate_error = None
        gate_length = None

        for param in gate.parameters:
            if param.name == "gate_error":
                gate_error = float(param.value)
            elif param.name == "gate_length":
                unit = param.unit
                value = float(param.value)
                if unit == "ns":
                    gate_length = value * 1e-9
                elif unit == "us":
                    gate_length = value * 1e-6
                elif unit == "s":
                    gate_length = value
                else:
                    gate_length = value

        if gate_error is not None:
            if len(qubits) == 1:
                single_qubit_gate_errors[(gate_name, qubits[0])] = gate_error
            else:
                two_qubit_gate_errors[(gate_name, qubits)] = gate_error

        if gate_length is not None:
            gate_lengths[(gate_name, qubits)] = gate_length

    return {
        "backend_name": backend.name if hasattr(backend, "name") else str(backend),
        "num_qubits": backend.num_qubits,
        "t1_times": t1_times,
        "t2_times": t2_times,
        "single_qubit_gate_errors": single_qubit_gate_errors,
        "two_qubit_gate_errors": two_qubit_gate_errors,
        "readout_errors": readout_errors,
        "gate_lengths": gate_lengths,
    }


def compute_circuit_depth(circuit: QuantumCircuit) -> int:
    """Compute the depth of a quantum circuit."""
    return circuit.depth()


def compute_cnot_count(circuit: QuantumCircuit) -> int:
    """Count the number of two-qubit gates in a circuit."""
    ops = circuit.count_ops()
    return sum(
        count for gate, count in ops.items() if gate in TWO_QUBIT_GATES
    )


def compute_idle_fraction(circuit: QuantumCircuit) -> float:
    """Compute the fraction of idle qubit-time in a circuit.

    Idle fraction = (total_idle_qubit_cycles) / (num_qubits × depth)

    A circuit where every qubit is active every cycle has idle_fraction = 0.
    A circuit with many unused qubits has a high idle fraction.

    Args:
        circuit: The quantum circuit to analyze.

    Returns:
        Fraction between 0 and 1 representing idle time.
    """
    depth = circuit.depth()
    if depth == 0:
        return 0.0

    total_slots = circuit.num_qubits * depth
    active_slots = 0
    for instr in circuit.data:
        active_slots += len(instr.qubits)

    idle_slots = total_slots - active_slots

    return idle_slots / total_slots


def get_avg_gate_time(device_props: dict, gate_type: str = "all") -> float:
    """Get average gate duration from device properties.

    Args:
        device_props: Dictionary from get_backend_properties().
        gate_type: 'single' for 1-qubit gates, 'two' for 2-qubit gates,
                   or 'all' for all gates.

    Returns:
        Average gate time in seconds.
    """
    gate_lengths = device_props.get("gate_lengths", {})

    if not gate_lengths:
        if gate_type == "two":
            return 300e-9
        return 50e-9

    times = []
    for (gate_name, qubits), duration in gate_lengths.items():
        if gate_type == "single" and len(qubits) == 1 or gate_type == "two" and len(qubits) == 2 or gate_type == "all":
            times.append(duration)

    if not times:
        if gate_type == "two":
            return 300e-9
        return 50e-9

    return sum(times) / len(times)