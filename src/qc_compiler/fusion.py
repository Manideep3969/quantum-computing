"""Gate fusion optimization for quantum circuits.

Analogous to kernel fusion in GPU compilers, this module merges
sequential single-qubit gates into a single unitary operation and
re-decomposes to the target basis, reducing circuit depth and
accumulated gate error.

The GPU analogy: just as fusing CUDA kernels eliminates global memory
round-trips and kernel launch overhead, fusing quantum gates reduces
circuit depth (latency) and gate error (accumulated imprecision).

Two fusion strategies are implemented:

    1. Chain fusion: Identify maximal sequences of consecutive
       single-qubit gates on the same qubit. Replace each chain
       with its product unitary, then re-decompose to the target
       basis gates. If the decomposition produces fewer gates,
       the fusion is beneficial.

    2. Cost-guided fusion: Only apply fusion when the cost model
       estimates that the fused version has higher fidelity than
       the original. This prevents fusion that increases error.
"""

from dataclasses import dataclass

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qiskit.synthesis import OneQubitEulerDecomposer

from qc_compiler.cost_model import CircuitMetrics, CostModel


@dataclass
class FusionResult:
    """Result of gate fusion optimization.

    Attributes:
        original_circuit: The input circuit before fusion.
        optimized_circuit: The output circuit after fusion.
        original_metrics: Metrics of the original circuit.
        optimized_metrics: Metrics of the optimized circuit.
        chains_fused: Number of single-qubit chains that were fused.
        total_gates_before: Total gate count before fusion.
        total_gates_after: Total gate count after fusion.
        depth_before: Circuit depth before fusion.
        depth_after: Circuit depth after fusion.
        fidelity_before: Estimated fidelity of the original circuit.
        fidelity_after: Estimated fidelity of the optimized circuit.
        improvement: Fidelity improvement (after - before).
    """

    original_circuit: QuantumCircuit = None
    optimized_circuit: QuantumCircuit = None
    original_metrics: CircuitMetrics = None
    optimized_metrics: CircuitMetrics = None
    chains_fused: int = 0
    total_gates_before: int = 0
    total_gates_after: int = 0
    depth_before: int = 0
    depth_after: int = 0
    fidelity_before: float = 0.0
    fidelity_after: float = 0.0

    @property
    def improvement(self) -> float:
        """Fidelity improvement from fusion (after - before)."""
        return self.fidelity_after - self.fidelity_before

    @property
    def gate_reduction_pct(self) -> float:
        """Percentage reduction in total gate count."""
        if self.total_gates_before == 0:
            return 0.0
        return (
            (self.total_gates_before - self.total_gates_after)
            / self.total_gates_before
            * 100
        )

    @property
    def depth_reduction_pct(self) -> float:
        """Percentage reduction in circuit depth."""
        if self.depth_before == 0:
            return 0.0
        return (self.depth_before - self.depth_after) / self.depth_before * 100


# Gates that should not be fused (they are barriers or measurements)
BOUNDARY_GATES = {"measure", "reset", "barrier", "snapshot"}

# Two-qubit gates that act as boundaries for single-qubit chains
TWO_QUBIT_GATES = {
    "cx", "cz", "ecr", "swap", "rxx", "rzz", "ryy", "crx", "cry", "crz"
}


class GateFusion:
    """Optimizes quantum circuits by fusing sequential single-qubit gates.

    Inspired by GPU kernel fusion: merge sequential operations to
    reduce overhead (circuit depth, gate count, and accumulated error).

    The optimizer finds maximal chains of consecutive single-qubit
    gates on the same qubit, computes their product unitary, and
    re-decomposes to the target basis. If the decomposition produces
    fewer or equal gates with higher estimated fidelity, the fusion
    is kept.

    Usage::

        from qc_compiler import CostModel, GateFusion
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        fusion = GateFusion(cost_model=model)

        result = fusion.optimize(circuit)
        print(f"Chains fused: {result.chains_fused}")
        print(f"Fidelity: {result.fidelity_before:.4f} -> {result.fidelity_after:.4f}")
    """

    def __init__(
        self,
        cost_model: CostModel,
        basis_gates: list[str] | None = None,
    ):
        """Initialize the gate fusion optimizer.

        Args:
            cost_model: Cost model for estimating circuit fidelity.
            basis_gates: Target basis gates for decomposition.
                If None, uses ['rz', 'sx', 'ecr', 'x'] (IBM basis).
        """
        self.cost_model = cost_model
        self.basis_gates = basis_gates or ["rz", "sx", "ecr", "x"]
        self._decomposer = OneQubitEulerDecomposer(basis="ZSX")

    def optimize(
        self,
        circuit: QuantumCircuit,
        min_chain_length: int = 2,
        cost_guided: bool = True,
    ) -> FusionResult:
        """Apply gate fusion optimization to a quantum circuit.

        Finds all maximal chains of consecutive single-qubit gates
        on the same qubit, fuses each chain into a unitary, re-decomposes
        to basis gates, and keeps the fused version only if it improves
        estimated fidelity (when cost_guided=True).

        Args:
            circuit: The quantum circuit to optimize.
            min_chain_length: Minimum number of gates in a chain
                to consider for fusion. Chains shorter than this
                are left unchanged.
            cost_guided: If True, only keep fusion when it improves
                estimated fidelity. If False, always keep fusion
                that reduces gate count.

        Returns:
            A FusionResult with the optimized circuit and metrics.
        """
        original_metrics = self.cost_model.compute_metrics(circuit)
        original_fidelity = self.cost_model.estimate_fidelity(
            circuit
        ).total_fidelity

        chains = self._find_single_qubit_chains(circuit)
        fused_circuit = circuit.copy()
        chains_fused = 0

        for qubit_idx, chain_list in chains.items():
            for start_idx, end_idx, gate_indices in chain_list:
                if len(gate_indices) < min_chain_length:
                    continue

                chain_unitary = self._compute_chain_unitary(
                    circuit, gate_indices
                )
                if chain_unitary is None:
                    continue

                decomposed = self._decompose_to_basis(chain_unitary)
                if decomposed is None:
                    continue

                original_gate_count = len(gate_indices)
                decomposed_gate_count = sum(decomposed.count_ops().values())

                if decomposed_gate_count >= original_gate_count:
                    continue

                fused_circuit = self._replace_chain(
                    fused_circuit, qubit_idx, gate_indices, decomposed
                )
                if fused_circuit is not None:
                    chains_fused += 1

        if chains_fused == 0:
            return FusionResult(
                original_circuit=circuit,
                optimized_circuit=circuit.copy(),
                original_metrics=original_metrics,
                optimized_metrics=original_metrics,
                chains_fused=0,
                total_gates_before=sum(circuit.count_ops().values()),
                total_gates_after=sum(circuit.count_ops().values()),
                depth_before=circuit.depth(),
                depth_after=circuit.depth(),
                fidelity_before=original_fidelity,
                fidelity_after=original_fidelity,
            )

        optimized_metrics = self.cost_model.compute_metrics(fused_circuit)
        optimized_fidelity = self.cost_model.estimate_fidelity(
            fused_circuit
        ).total_fidelity

        if cost_guided and optimized_fidelity < original_fidelity:
            fused_circuit = circuit.copy()
            optimized_metrics = original_metrics
            optimized_fidelity = original_fidelity
            chains_fused = 0

        return FusionResult(
            original_circuit=circuit,
            optimized_circuit=fused_circuit,
            original_metrics=original_metrics,
            optimized_metrics=optimized_metrics,
            chains_fused=chains_fused,
            total_gates_before=sum(circuit.count_ops().values()),
            total_gates_after=sum(fused_circuit.count_ops().values()),
            depth_before=circuit.depth(),
            depth_after=fused_circuit.depth(),
            fidelity_before=original_fidelity,
            fidelity_after=optimized_fidelity,
        )

    def _find_single_qubit_chains(
        self, circuit: QuantumCircuit
    ) -> dict[int, list[tuple[int, int, list[int]]]]:
        """Find maximal chains of consecutive single-qubit gates per qubit.

        Scans the circuit instruction-by-instruction and identifies
        maximal sequences of single-qubit gates on the same qubit
        that are not interrupted by two-qubit gates, measurements,
        or barriers.

        Args:
            circuit: The quantum circuit to scan.

        Returns:
            Dictionary mapping qubit index to list of
            (start_index, end_index, [instruction_indices]) tuples.
        """
        chains = {}

        active_chains = {}

        for idx, instr in enumerate(circuit.data):
            gate_name = instr.operation.name

            if gate_name in BOUNDARY_GATES:
                for q, chain_info in active_chains.items():
                    if len(chain_info[2]) >= 2:
                        if q not in chains:
                            chains[q] = []
                        chains[q].append(chain_info)
                active_chains = {}
                continue

            if len(instr.qubits) >= 2:
                for q, chain_info in active_chains.items():
                    if len(chain_info[2]) >= 2:
                        if q not in chains:
                            chains[q] = []
                        chains[q].append(chain_info)

                affected_qubits = set()
                for q in instr.qubits:
                    qidx = circuit.find_bit(q).index
                    affected_qubits.add(qidx)
                for q in affected_qubits:
                    if q in active_chains:
                        if len(active_chains[q][2]) >= 2:
                            if q not in chains:
                                chains[q] = []
                            chains[q].append(active_chains[q])
                        del active_chains[q]
                continue

            if len(instr.qubits) == 1:
                qubit_idx = circuit.find_bit(instr.qubits[0]).index

                if qubit_idx in active_chains:
                    active_chains[qubit_idx][2].append(idx)
                    active_chains[qubit_idx] = (
                        active_chains[qubit_idx][0],
                        idx,
                        active_chains[qubit_idx][2],
                    )
                else:
                    active_chains[qubit_idx] = (idx, idx, [idx])

        for q, chain_info in active_chains.items():
            if len(chain_info[2]) >= 2:
                if q not in chains:
                    chains[q] = []
                chains[q].append(chain_info)

        return chains

    def _compute_chain_unitary(
        self, circuit: QuantumCircuit, gate_indices: list[int]
    ) -> Operator | None:
        """Compute the product unitary of a chain of single-qubit gates.

        Args:
            circuit: The original circuit.
            gate_indices: List of instruction indices forming the chain.

        Returns:
            Operator representing the product unitary, or None on error.
        """
        chain_qc = QuantumCircuit(1)
        for idx in gate_indices:
            instr = circuit.data[idx]
            gate = instr.operation
            try:
                chain_qc.append(gate, [0])
            except Exception:  # noqa: BLE001
                return None

        try:
            return Operator(chain_qc)
        except Exception:  # noqa: BLE001
            return None

    def _decompose_to_basis(
        self, unitary: Operator
    ) -> QuantumCircuit | None:
        """Decompose a single-qubit unitary to the target basis.

        Args:
            unitary: The unitary operator to decompose.

        Returns:
            A QuantumCircuit implementing the unitary in basis gates,
            or None if decomposition fails.
        """
        try:
            decomposed = self._decomposer(unitary)
            return decomposed
        except Exception:  # noqa: BLE001
            return None

    def _replace_chain(
        self,
        circuit: QuantumCircuit,
        qubit_idx: int,
        gate_indices: list[int],
        decomposed: QuantumCircuit,
    ) -> QuantumCircuit | None:
        """Replace a chain of single-qubit gates with a decomposed unitary.

        Builds a new circuit by:
        1. Copying all instructions before the chain
        2. Inserting the decomposed unitary on the target qubit
        3. Copying all instructions after the chain

        Args:
            circuit: The original circuit.
            qubit_idx: The qubit index where the chain lives.
            gate_indices: Instruction indices forming the chain.
            decomposed: The decomposed replacement circuit.

        Returns:
            A new QuantumCircuit with the chain replaced, or None on error.
        """
        new_qc = QuantumCircuit(*circuit.qregs, *circuit.cregs)

        skip_indices = set(gate_indices)
        chain_replaced = False

        for idx, instr in enumerate(circuit.data):
            if idx in skip_indices and not chain_replaced:
                for dep_instr in decomposed.data:
                    new_qc.append(
                        dep_instr.operation,
                        [circuit.qubits[qubit_idx]],
                        dep_instr.clbits if dep_instr.clbits else [],
                    )
                chain_replaced = True
                continue

            if idx in skip_indices:
                continue

            new_qc.append(instr.operation, instr.qubits, instr.clbits)

        return new_qc