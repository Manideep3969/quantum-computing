"""Unified error cost model for quantum circuits on NISQ devices.

Computes estimated total error for a given circuit on a given device,
considering gate errors, decoherence, measurement errors, and crosstalk.

This is the foundation of the qc-compiler framework. Every optimization
module queries the cost model to make decisions about when and how to
optimize a circuit.

Analogous to the GPU cost model:
    Total_Latency = Kernel_Compute + Memory_Transfer + Synchronization_Overhead
Our quantum cost model computes:
    Total_Error = Gate_Errors + Decoherence_Errors + Measurement_Errors
"""

from dataclasses import dataclass, field

from qiskit import QuantumCircuit

from qc_compiler.utils import (
    TWO_QUBIT_GATES,
    compute_circuit_depth,
    get_backend_properties,
)

SINGLE_QUBIT_GATES = {"id", "rz", "sx", "x", "h", "s", "t", "p", "u", "u1", "u2", "u3"}


@dataclass
class DeviceCharacterization:
    """Calibration data for a quantum device.

    Attributes:
        backend_name: Name of the backend.
        num_qubits: Number of qubits on the device.
        t1_times: T1 relaxation times in seconds, keyed by qubit index.
        t2_times: T2 dephasing times in seconds, keyed by qubit index.
        single_qubit_gate_errors: Gate error rates keyed by (gate_name, qubit).
        two_qubit_gate_errors: Gate error rates keyed by (gate_name, qubit_pair).
        readout_errors: Readout error rates keyed by qubit index.
        gate_lengths: Gate durations in seconds keyed by (gate_name, qubits).
    """

    backend_name: str = ""
    num_qubits: int = 0
    t1_times: dict[int, float] = field(default_factory=dict)
    t2_times: dict[int, float] = field(default_factory=dict)
    single_qubit_gate_errors: dict[tuple[str, int], float] = field(
        default_factory=dict
    )
    two_qubit_gate_errors: dict[tuple[str, tuple[int, ...]], float] = field(
        default_factory=dict
    )
    readout_errors: dict[int, float] = field(default_factory=dict)
    gate_lengths: dict[tuple[str, tuple[int, ...]], float] = field(
        default_factory=dict
    )


@dataclass
class CircuitMetrics:
    """Metrics extracted from a transpiled quantum circuit.

    Attributes:
        depth: Circuit depth (longest path in gate count).
        num_qubits: Number of qubits used.
        single_qubit_gate_count: Count of single-qubit gates.
        two_qubit_gate_count: Count of two-qubit gates (cx, cz, ecr, swap).
        total_gate_count: Total number of gates.
        gate_counts: Per-gate-type counts (e.g., {'h': 4, 'cx': 3}).
    """

    depth: int = 0
    num_qubits: int = 0
    single_qubit_gate_count: int = 0
    two_qubit_gate_count: int = 0
    total_gate_count: int = 0
    gate_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class ErrorBreakdown:
    """Detailed error breakdown for a circuit on a device.

    Attributes:
        gate_error: Product of (1 - gate_error) for all gates.
        decoherence_error: Estimated error from qubit decoherence during idle time.
        measurement_error: Average readout error for measured qubits.
        total_fidelity: Estimated overall circuit fidelity (0 to 1).
    """

    gate_fidelity: float = 1.0
    decoherence_fidelity: float = 1.0
    measurement_fidelity: float = 1.0
    total_fidelity: float = 1.0


class CostModel:
    """Estimates total error for a quantum circuit on a given device.

    The cost model computes:
        Total_Fidelity = Gate_Fidelity × Decoherence_Fidelity × Measurement_Fidelity

    Where:
        Gate_Fidelity = Π_gates (1 - error_rate(gate, qubits))
        Decoherence_Fidelity = Π_qubits exp(-idle_time_q / T2_q)
        Measurement_Fidelity = Π_measured_qubits (1 - readout_error_q)

    This is analogous to the GPU cost model:
        Total_Latency = Kernel_Compute + Memory_Transfer + Synchronization
    """

    def __init__(self, backend=None):
        """Initialize the cost model with device characterization.

        Args:
            backend: A Qiskit BackendV2 instance (e.g., FakeBrisbane for simulation,
                     or a real IBM Quantum backend). If None, uses a default
                     idealized model.
        """
        self.device = self._load_device_characterization(backend)

    def _load_device_characterization(self, backend) -> DeviceCharacterization:
        """Load device calibration data from a backend.

        Args:
            backend: A Qiskit BackendV2 instance or None.

        Returns:
            A DeviceCharacterization populated with calibration data.
        """
        if backend is None:
            return DeviceCharacterization()

        device = DeviceCharacterization()
        props = get_backend_properties(backend)
        device.backend_name = props["backend_name"]
        device.num_qubits = props["num_qubits"]
        device.t1_times = props["t1_times"]
        device.t2_times = props["t2_times"]
        device.single_qubit_gate_errors = props["single_qubit_gate_errors"]
        device.two_qubit_gate_errors = props["two_qubit_gate_errors"]
        device.readout_errors = props["readout_errors"]
        device.gate_lengths = props["gate_lengths"]
        return device

    def compute_metrics(self, circuit: QuantumCircuit) -> CircuitMetrics:
        """Extract metrics from a quantum circuit.

        Works on both abstract and transpiled circuits. For accurate
        error estimation, use a transpiled circuit (with basis gates
        matching the target device).

        Args:
            circuit: The quantum circuit to analyze.

        Returns:
            A CircuitMetrics object with gate counts and depth.
        """
        ops = circuit.count_ops()
        sq_count = sum(
            count
            for gate, count in ops.items()
            if gate not in TWO_QUBIT_GATES
        )
        tq_count = sum(
            count
            for gate, count in ops.items()
            if gate in TWO_QUBIT_GATES
        )

        return CircuitMetrics(
            depth=compute_circuit_depth(circuit),
            num_qubits=circuit.num_qubits,
            single_qubit_gate_count=sq_count,
            two_qubit_gate_count=tq_count,
            total_gate_count=sum(ops.values()),
            gate_counts=dict(ops),
        )

    def estimate_gate_error(
        self, circuit: QuantumCircuit, layout: dict | None = None
    ) -> float:
        """Estimate total gate error for the circuit on the characterized device.

        Computes 1 - Π_gates (1 - error_rate(gate, qubits)).

        If no device is characterized, uses average error rates from
        typical superconducting hardware:
            - Single-qubit gate error: 0.05%
            - Two-qubit gate error: 1.0%

        Args:
            circuit: The transpiled quantum circuit.
            layout: Optional mapping from virtual to physical qubits.
                    If None, assumes qubits map directly (qubit 0 -> physical 0).

        Returns:
            Estimated gate error (0 to 1).
        """
        if not self.device.num_qubits:
            return self._estimate_gate_error_default(circuit)

        product = 1.0
        ops = circuit.count_ops()

        for gate_name, count in ops.items():
            for _ in range(count):
                fidelity = self._get_gate_fidelity(gate_name, layout)
                product *= fidelity

        return 1.0 - product

    def _estimate_gate_error_default(self, circuit: QuantumCircuit) -> float:
        """Estimate gate error using default hardware parameters.

        Uses typical superconducting qubit error rates:
            - Single-qubit: 0.9995 fidelity (0.05% error)
            - Two-qubit: 0.99 fidelity (1% error)
        """
        SQ_FIDELITY = 0.9995
        TQ_FIDELITY = 0.99

        ops = circuit.count_ops()
        product = 1.0

        for gate_name, count in ops.items():
            if gate_name in TWO_QUBIT_GATES:
                product *= TQ_FIDELITY**count
            else:
                product *= SQ_FIDELITY**count

        return 1.0 - product

    def _get_gate_fidelity(
        self, gate_name: str, layout: dict | None = None
    ) -> float:
        """Get the fidelity for a single gate execution on the device.

        Args:
            gate_name: The gate name (e.g., 'sx', 'cx', 'ecr').
            layout: Optional qubit mapping.

        Returns:
            Gate fidelity (0 to 1).
        """
        if gate_name in TWO_QUBIT_GATES:
            avg_error = self._avg_two_qubit_error()
        else:
            avg_error = self._avg_single_qubit_error()

        return 1.0 - avg_error

    def _avg_single_qubit_error(self) -> float:
        """Compute average single-qubit gate error across all qubits."""
        if not self.device.single_qubit_gate_errors:
            return 0.0005

        errors = list(self.device.single_qubit_gate_errors.values())
        return sum(errors) / len(errors)

    def _avg_two_qubit_error(self) -> float:
        """Compute average two-qubit gate error across all qubit pairs."""
        if not self.device.two_qubit_gate_errors:
            return 0.01

        errors = list(self.device.two_qubit_gate_errors.values())
        return sum(errors) / len(errors)

    def estimate_decoherence_error(
        self, circuit: QuantumCircuit, layout: dict | None = None
    ) -> float:
        """Estimate decoherence error based on idle qubit times and T1/T2.

        Computes 1 - Π_qubits exp(-idle_time_q / T2_q).

        Idle time for each qubit is estimated as:
            idle_time_q = circuit_depth × avg_gate_time - time_q_is_active

        For simplicity, we use a conservative estimate where idle time
        is proportional to circuit depth.

        Args:
            circuit: The transpiled quantum circuit.
            layout: Optional qubit mapping.

        Returns:
            Estimated decoherence error (0 to 1).
        """
        if not self.device.t2_times:
            return self._estimate_decoherence_error_default(circuit)

        depth = compute_circuit_depth(circuit)
        avg_gate_time = self._avg_gate_time()

        product = 1.0
        for qubit in range(circuit.num_qubits):
            if qubit < len(self.device.t2_times):
                t2 = self.device.t2_times.get(qubit, max(self.device.t2_times.values()))
            else:
                t2 = max(self.device.t2_times.values())

            total_time = depth * avg_gate_time
            fidelity = float(min(1.0, 2.0**(-total_time / t2)))
            product *= fidelity

        return 1.0 - product

    def _estimate_decoherence_error_default(
        self, circuit: QuantumCircuit
    ) -> float:
        """Estimate decoherence error using default parameters.

        Uses typical superconducting qubit T2 time of 150 μs.
        """
        DEFAULT_T2 = 150e-6
        DEFAULT_GATE_TIME = 50e-9

        depth = compute_circuit_depth(circuit)
        total_time = depth * DEFAULT_GATE_TIME
        fidelity = float(2.0 ** (-total_time / DEFAULT_T2))
        product = fidelity**circuit.num_qubits

        return 1.0 - product

    def _avg_gate_time(self) -> float:
        """Compute average gate duration across all gate types."""
        if not self.device.gate_lengths:
            return 50e-9

        times = list(self.device.gate_lengths.values())
        return sum(times) / len(times)

    def estimate_measurement_error(
        self, circuit: QuantumCircuit
    ) -> float:
        """Estimate readout error for the measured qubits.

        Computes 1 - Π_measured_qubits (1 - readout_error_q).

        Args:
            circuit: The quantum circuit with measurements.

        Returns:
            Estimated measurement error (0 to 1).
        """
        measured_qubits = self._get_measured_qubits(circuit)

        if not self.device.readout_errors:
            DEFAULT_READOUT_ERROR = 0.015
            return 1.0 - (1.0 - DEFAULT_READOUT_ERROR) ** len(measured_qubits)

        product = 1.0
        for qubit in measured_qubits:
            error = self.device.readout_errors.get(
                qubit, sum(self.device.readout_errors.values()) / len(self.device.readout_errors)
            )
            product *= 1.0 - error

        return 1.0 - product

    def _get_measured_qubits(self, circuit: QuantumCircuit) -> list[int]:
        """Extract the list of measured qubits from a circuit.

        Args:
            circuit: The quantum circuit.

        Returns:
            Sorted list of qubit indices that are measured.
        """
        measured = set()
        for instr in circuit.data:
            if instr.operation.name == "measure":
                for qubit in instr.qubits:
                    measured.add(circuit.find_bit(qubit).index)
        if not measured:
            measured = set(range(circuit.num_qubits))
        return sorted(measured)

    def estimate_fidelity(
        self,
        circuit: QuantumCircuit,
        layout: dict | None = None,
    ) -> ErrorBreakdown:
        """Estimate circuit fidelity on the characterized device.

        Computes a detailed breakdown of gate error, decoherence error,
        and measurement error, then combines them into an overall
        fidelity estimate.

        Fidelity = Gate_Fidelity × Decoherence_Fidelity × Measurement_Fidelity

        Args:
            circuit: The transpiled quantum circuit.
            layout: Optional mapping from virtual to physical qubits.

        Returns:
            An ErrorBreakdown with detailed and total fidelity estimates.
        """
        gate_fidelity = 1.0 - self.estimate_gate_error(circuit, layout)
        decoherence_fidelity = 1.0 - self.estimate_decoherence_error(
            circuit, layout
        )
        measurement_fidelity = 1.0 - self.estimate_measurement_error(circuit)

        total_fidelity = (
            gate_fidelity * decoherence_fidelity * measurement_fidelity
        )

        return ErrorBreakdown(
            gate_fidelity=float(gate_fidelity),
            decoherence_fidelity=float(decoherence_fidelity),
            measurement_fidelity=float(measurement_fidelity),
            total_fidelity=float(total_fidelity),
        )

    def compare_circuits(
        self,
        circuits: list[QuantumCircuit],
        layouts: list[dict] | None = None,
    ) -> list[ErrorBreakdown]:
        """Compare the estimated fidelity of multiple circuits.

        Useful for comparing different transpilations of the same circuit,
        or different optimization levels.

        Args:
            circuits: List of quantum circuits to compare.
            layouts: Optional list of qubit mappings (one per circuit).

        Returns:
            List of ErrorBreakdown objects, one per circuit.
        """
        if layouts is None:
            layouts = [None] * len(circuits)

        results = []
        for circuit, layout in zip(circuits, layouts):
            breakdown = self.estimate_fidelity(circuit, layout)
            results.append(breakdown)

        return results