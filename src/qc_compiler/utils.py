"""Shared utilities for qc-compiler."""

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2


def get_backend_properties(backend: BackendV2) -> dict:
    """Extract calibration properties from an IBM Quantum backend.

    Args:
        backend: An IBM Quantum backend instance.

    Returns:
        Dictionary with qubit properties, gate errors, and T1/T2 times.
    """
    raise NotImplementedError("Backend property extraction not yet implemented")


def compute_circuit_depth(circuit: QuantumCircuit) -> int:
    """Compute the depth of a quantum circuit."""
    return circuit.depth()


def compute_cnot_count(circuit: QuantumCircuit) -> int:
    """Count the number of CNOT (two-qubit) gates in a circuit."""
    ops = circuit.count_ops()
    return sum(
        count for gate, count in ops.items()
        if gate in ("cx", "cz", "ecr", "swap")
    )


def compute_idle_fraction(circuit: QuantumCircuit) -> float:
    """Compute the fraction of idle qubit-time in a circuit."""
    raise NotImplementedError("Idle fraction computation not yet implemented")