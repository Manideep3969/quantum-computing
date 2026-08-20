"""Circuit batching optimization for quantum hardware.

Analogous to batched inference in GPU serving (Orca, TensorRT-LLM),
this module groups circuits sharing the same unitary core to amortize
execution overhead (calibration, initialization, readout).

Three batching strategies are provided:

    1. Measurement-based batching: Circuits that differ only in
       measurement basis share the same quantum execution. The unitary
       core runs once, and different basis-change layers are applied
       before measurement.

    2. Unitary-core grouping: Circuits with identical pre-measurement
       unitaries are grouped together. This is especially useful for
       VQE where multiple observables are measured for the same ansatz.

    3. Structural batching: Circuits with the same depth on
       non-overlapping qubit subsets can execute in parallel on the
       same device, maximizing qubit utilization.
"""

import hashlib
from dataclasses import dataclass, field

from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel


@dataclass
class BatchPlan:
    """Execution plan for circuit batching.

    Attributes:
        batches: List of circuit batches. Each batch is a list of
            circuits that can be executed together.
        measurement_groups: Mapping from core hash to list of
            measurement basis labels (e.g., 'Z', 'X', 'Y').
        estimated_speedup: Estimated speedup factor from batching.
        total_circuits: Total number of input circuits.
        num_batches: Number of batches in the plan.
        batch_sizes: List of batch sizes.
        unitary_core_groups: Mapping from core hash to circuit indices.
    """

    batches: list[list[QuantumCircuit]] = field(default_factory=list)
    measurement_groups: dict[int, list[str]] = field(default_factory=dict)
    estimated_speedup: float = 1.0
    total_circuits: int = 0
    num_batches: int = 0
    batch_sizes: list[int] = field(default_factory=list)
    unitary_core_groups: dict[int, list[int]] = field(default_factory=dict)

    @property
    def avg_batch_size(self) -> float:
        """Average number of circuits per batch."""
        if not self.batch_sizes:
            return 0.0
        return sum(self.batch_sizes) / len(self.batch_sizes)

    @property
    def max_batch_size(self) -> int:
        """Maximum batch size."""
        if not self.batch_sizes:
            return 0
        return max(self.batch_sizes)

    @property
    def min_batch_size(self) -> int:
        """Minimum batch size."""
        if not self.batch_sizes:
            return 0
        return min(self.batch_sizes)


MEASUREMENT_BASIS = {
    "Z": [],
    "X": ["h"],
    "Y": ["sdg", "h"],
}


class CircuitBatcher:
    """Groups circuits for efficient batched execution.

    Inspired by GPU batched inference: amortize fixed overhead
    (calibration, initialization, readout) by executing multiple
    circuits in a single job, especially those sharing the same
    unitary core.

    Usage::

        from qc_compiler import CostModel, CircuitBatcher

        model = CostModel()
        batcher = CircuitBatcher(cost_model=model)

        plan = batcher.create_batch_plan(circuits)
        print(f"Speedup: {plan.estimated_speedup:.2f}x")
        print(f"Batches: {plan.num_batches}")
    """

    def __init__(self, cost_model: CostModel, max_qubits: int = 127):
        self.cost_model = cost_model
        self.max_qubits = max_qubits

    def create_batch_plan(
        self,
        circuits: list[QuantumCircuit],
        strategy: str = "auto",
    ) -> BatchPlan:
        """Create a batching plan for a set of circuits.

        Args:
            circuits: List of quantum circuits to batch.
            strategy: Batching strategy — 'measurement' for
                measurement-based grouping, 'structural' for
                structural batching, 'auto' for automatic selection.

        Returns:
            A BatchPlan with grouped circuits and estimated speedup.
        """
        if not circuits:
            return BatchPlan()

        if strategy == "measurement":
            return self._measurement_based_batch(circuits)
        elif strategy == "structural":
            return self._structural_batch(circuits)
        elif strategy == "auto":
            core_groups = self._group_by_unitary_core(circuits)
            if len(core_groups) < len(circuits):
                return self._measurement_based_batch(circuits)
            else:
                return self._structural_batch(circuits)
        else:
            raise ValueError(
                f"Unknown batching strategy '{strategy}'. "
                "Use 'measurement', 'structural', or 'auto'."
            )

    def _group_by_unitary_core(
        self, circuits: list[QuantumCircuit]
    ) -> dict[int, list[QuantumCircuit]]:
        """Group circuits that share the same unitary (pre-measurement) part.

        Two circuits share the same unitary core if they have identical
        gates before measurement. Circuits differing only in measurement
        basis are grouped together.

        Args:
            circuits: List of quantum circuits.

        Returns:
            Dictionary mapping core hash to list of circuits.
        """
        groups = {}

        for circuit in circuits:
            core_hash = self._compute_core_hash(circuit)
            if core_hash not in groups:
                groups[core_hash] = []
            groups[core_hash].append(circuit)

        return groups

    def _measurement_based_batch(
        self, circuits: list[QuantumCircuit]
    ) -> BatchPlan:
        """Create measurement-based batches for circuits sharing a core.

        For each unitary core group, identify circuits that differ
        only in measurement basis. These can share a single quantum
        execution with different basis-change layers.

        Args:
            circuits: List of quantum circuits.

        Returns:
            A BatchPlan with measurement-based grouping.
        """
        core_groups = self._group_by_unitary_core(circuits)

        batches = []
        measurement_groups = {}
        unitary_core_groups = {}

        for core_hash, group in core_groups.items():
            batches.append(group)
            unitary_core_groups[core_hash] = [
                circuits.index(c) for c in group
            ]

            basis_labels = []
            for circuit in group:
                basis = self._detect_measurement_basis(circuit)
                basis_labels.append(basis)

            measurement_groups[core_hash] = basis_labels

        speedup = self._estimate_speedup(circuits, core_groups)

        batch_sizes = [len(b) for b in batches]

        return BatchPlan(
            batches=batches,
            measurement_groups=measurement_groups,
            estimated_speedup=speedup,
            total_circuits=len(circuits),
            num_batches=len(batches),
            batch_sizes=batch_sizes,
            unitary_core_groups=unitary_core_groups,
        )

    def _structural_batch(
        self, circuits: list[QuantumCircuit]
    ) -> BatchPlan:
        """Batch circuits with same depth on non-overlapping qubit subsets.

        Circuits using different qubits of the same device can run
        in parallel, maximizing qubit utilization. Uses the device's
        total qubit count (max_qubits) to determine how many circuits
        can be placed without overlapping.

        Args:
            circuits: List of quantum circuits.

        Returns:
            A BatchPlan with structural grouping.
        """
        if not circuits:
            return BatchPlan()

        depth_groups = {}
        for i, circuit in enumerate(circuits):
            depth = circuit.depth()
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(i)

        batches = []
        batch_sizes = []

        for depth, indices in depth_groups.items():
            current_batch = []
            total_qubits_used = 0

            for idx in indices:
                circuit = circuits[idx]
                n_qubits = circuit.num_qubits

                if total_qubits_used + n_qubits <= self.max_qubits:
                    current_batch.append(circuit)
                    total_qubits_used += n_qubits
                else:
                    if current_batch:
                        batches.append(current_batch)
                        batch_sizes.append(len(current_batch))
                    current_batch = [circuit]
                    total_qubits_used = n_qubits

            if current_batch:
                batches.append(current_batch)
                batch_sizes.append(len(current_batch))

        if not batches:
            batches = [[c] for c in circuits]
            batch_sizes = [1] * len(circuits)

        speedup = self._estimate_structural_speedup(circuits, batches)

        return BatchPlan(
            batches=batches,
            estimated_speedup=speedup,
            total_circuits=len(circuits),
            num_batches=len(batches),
            batch_sizes=batch_sizes,
        )

    def _compute_core_hash(self, circuit: QuantumCircuit) -> int:
        """Compute a hash for the unitary core of a circuit.

        The unitary core is the circuit excluding measurement and
        barrier operations. Two circuits with the same core hash
        have the same unitary evolution before measurement.

        Args:
            circuit: The quantum circuit.

        Returns:
            Hash of the unitary core.
        """
        core_gates = []
        for instr in circuit.data:
            gate_name = instr.operation.name
            if gate_name in ("measure", "barrier", "reset", "snapshot"):
                continue
            qubits = tuple(circuit.find_bit(q).index for q in instr.qubits)
            params = tuple(
                float(p) if hasattr(p, '__float__') else str(p)
                for p in instr.operation.params
            )
            core_gates.append((gate_name, qubits, params))

        return int(hashlib.sha256(str(tuple(core_gates)).encode()).hexdigest(), 16)

    def _detect_measurement_basis(
        self, circuit: QuantumCircuit
    ) -> str:
        """Detect the measurement basis of a circuit.

        Checks the single-qubit gates between the last two-qubit
        gate (or start) and the first measurement for each qubit
        to determine the measurement basis.

        Args:
            circuit: The quantum circuit.

        Returns:
            Measurement basis label ('Z', 'X', 'Y', or 'custom').
        """
        measured_qubits = set()
        measure_indices = set()
        for idx, instr in enumerate(circuit.data):
            if instr.operation.name == "measure":
                measure_indices.add(idx)
                for q in instr.qubits:
                    measured_qubits.add(circuit.find_bit(q).index)

        if not measured_qubits:
            return "none"

        last_two_qubit_idx = -1
        for idx, instr in enumerate(circuit.data):
            if len(instr.qubits) >= 2 and instr.operation.name not in (
                "barrier", "measure"
            ):
                last_two_qubit_idx = idx

        pre_measure_gates = {q: [] for q in measured_qubits}

        for idx in range(last_two_qubit_idx + 1, len(circuit.data)):
            instr = circuit.data[idx]
            if instr.operation.name in ("measure", "barrier", "reset", "snapshot"):
                continue
            if len(instr.qubits) == 1:
                qubit_idx = circuit.find_bit(instr.qubits[0]).index
                if qubit_idx in measured_qubits:
                    pre_measure_gates[qubit_idx].append(
                        instr.operation.name
                    )

        bases = set()
        for qubit_idx, gates in pre_measure_gates.items():
            gate_tuple = tuple(gates)
            if gate_tuple == tuple(MEASUREMENT_BASIS["X"]):
                bases.add("X")
            elif gate_tuple == tuple(MEASUREMENT_BASIS["Y"]):
                bases.add("Y")
            elif gate_tuple == () or gate_tuple == tuple(MEASUREMENT_BASIS["Z"]):
                bases.add("Z")
            else:
                bases.add("custom")

        if len(bases) == 1:
            return bases.pop()
        return "mixed"

    def _estimate_speedup(
        self,
        circuits: list[QuantumCircuit],
        core_groups: dict,
    ) -> float:
        """Estimate speedup from measurement-based batching.

        Speedup comes from sharing the unitary execution across
        circuits that differ only in measurement. If k circuits
        share a core, the unitary is executed once instead of k times.

        Args:
            circuits: All input circuits.
            core_groups: Mapping from core hash to circuit group.

        Returns:
            Estimated speedup factor.
        """
        if not core_groups:
            return 1.0

        total_circuits = len(circuits)
        if total_circuits == 0:
            return 1.0

        total_savings = 0
        for group in core_groups.values():
            if len(group) > 1:
                core_depth = group[0].depth()
                total_measure_steps = sum(c.depth() for c in group)
                total_original = sum(c.depth() for c in group)
                total_batched = core_depth + total_measure_steps / len(
                    group
                )
                total_savings += max(0, total_original - total_batched)

        avg_original_depth = sum(c.depth() for c in circuits) / total_circuits
        if avg_original_depth == 0:
            return 1.0

        speedup = 1.0 + (total_savings / (avg_original_depth * total_circuits))
        return max(1.0, min(speedup, total_circuits))

    def _estimate_structural_speedup(
        self,
        circuits: list[QuantumCircuit],
        batches: list[list[QuantumCircuit]],
    ) -> float:
        """Estimate speedup from structural batching.

        Speedup comes from executing circuits in parallel on
        non-overlapping qubit subsets.

        Args:
            circuits: All input circuits.
            batches: List of circuit batches.

        Returns:
            Estimated speedup factor.
        """
        if not batches:
            return 1.0

        total_sequential = len(circuits)
        total_parallel = len(batches)

        if total_sequential == 0:
            return 1.0

        return max(1.0, total_sequential / total_parallel)