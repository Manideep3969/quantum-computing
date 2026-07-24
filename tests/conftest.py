"""Shared test fixtures for qc-compiler tests."""

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT


@pytest.fixture
def bell_circuit():
    """Create a simple Bell state circuit."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


@pytest.fixture
def ghz_circuit():
    """Create a 4-qubit GHZ state circuit."""
    qc = QuantumCircuit(4)
    qc.h(0)
    for i in range(1, 4):
        qc.cx(0, i)
    return qc


@pytest.fixture
def qft_circuit():
    """Create a 4-qubit QFT circuit."""
    return QFT(4, do_swaps=True).decompose()


@pytest.fixture
def random_circuit():
    """Create a random 4-qubit circuit for testing."""
    from qiskit.circuit.random import random_circuit

    return random_circuit(4, depth=10, seed=42, max_operands=2)


@pytest.fixture
def qaoa_circuit():
    """Create a simple QAOA circuit for Max-Cut on a 3-regular graph."""
    qc = QuantumCircuit(4)
    for i in range(4):
        qc.h(i)
    for i in range(3):
        qc.cx(i, i + 1)
        qc.rz(0.5, i + 1)
        qc.cx(i, i + 1)
    for i in range(4):
        qc.rx(0.3, i)
    return qc