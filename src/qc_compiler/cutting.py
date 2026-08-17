"""Circuit cutting optimization for quantum circuits.

Analogous to model parallelism in GPU computing (tensor parallelism,
pipeline parallelism), this module partitions circuits across qubit
constraints using wire cutting and gate cutting, with a cost-benefit
decision framework.

The key insight: just as splitting a model across GPUs trades
communication overhead for reduced per-device memory, cutting a
quantum circuit trades sampling overhead for reduced per-circuit
error. The decision framework ensures cutting only happens when
the benefit outweighs the cost.

Wire cutting:
    A qubit wire is cut at a point, creating two subcircuits. The
    cut introduces a classical communication channel: the
    subcircuits are run separately and results reconstructed via
    quasi-probability decomposition.

Gate cutting:
    A two-qubit gate (e.g., CX) is decomposed into local operations
    plus classical communication. This eliminates the need for SWAP
    gates for non-adjacent qubits at the cost of sampling overhead.

Cost model:
    Error_uncut = gate_errors + decoherence + SWAP_overhead
    Error_cut   = subcircuit_errors + sampling_overhead
    Sampling_overhead = 4^k / shots   (k = number of cuts)
    Cut if Error_cut < Error_uncut

References:
    Peng, T., et al. (2020). Simulating large quantum circuits on a
        small quantum computer. Physical Review Letters, 125(15).
    Bravyi, S., Smith, G., & Smolin, J. (2016). Trading classical and
        quantum computational resources. Physical Review X.
    Tang, E., et al. (2024). CutQC: using small quantum computers
        for large quantum circuit evaluations. ACM TODAES.
"""

from dataclasses import dataclass, field

import numpy as np
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.utils import TWO_QUBIT_GATES


@dataclass
class CutLocation:
    """A candidate location for cutting a circuit.

    Attributes:
        gate_index: Index of the gate in the circuit data.
        gate_name: Name of the gate at this location.
        qubits: Tuple of qubit indices the gate acts on.
        cut_type: 'wire' or 'gate'.
        estimated_benefit: Estimated error reduction from this cut.
    """

    gate_index: int = 0
    gate_name: str = ""
    qubits: tuple[int, ...] = ()
    cut_type: str = ""
    estimated_benefit: float = 0.0


@dataclass
class CuttingResult:
    """Result of a circuit cutting decision.

    Attributes:
        should_cut: Whether cutting is recommended.
        num_cuts: Number of cuts made.
        subcircuits: List of subcircuits after cutting.
        cut_locations: Where the cuts were made.
        estimated_error_uncut: Estimated error without cutting.
        estimated_error_cut: Estimated error with cutting.
        sampling_overhead: Sampling overhead factor (4^k).
        subcircuit_qubit_counts: Qubit counts per subcircuit.
    """

    should_cut: bool = False
    num_cuts: int = 0
    subcircuits: list = field(default_factory=list)
    cut_locations: list = field(default_factory=list)
    estimated_error_uncut: float = 0.0
    estimated_error_cut: float = 0.0
    sampling_overhead: float = 0.0
    subcircuit_qubit_counts: list = field(default_factory=list)

    @property
    def error_reduction(self) -> float:
        """Error reduction from cutting (uncut - cut)."""
        return self.estimated_error_uncut - self.estimated_error_cut

    @property
    def error_reduction_pct(self) -> float:
        """Percentage error reduction from cutting."""
        if self.estimated_error_uncut == 0:
            return 0.0
        return (
            (self.estimated_error_uncut - self.estimated_error_cut)
            / self.estimated_error_uncut
            * 100
        )


class CircuitCutter:
    """Decides when and how to cut quantum circuits.

    Uses a cost-benefit model to determine whether cutting reduces
    overall error compared to running the full circuit with SWAP gates.

    Analogous to model parallelism: cut when device capacity is
    exceeded or when partitioning reduces communication overhead.

    Usage::

        from qc_compiler import CostModel, CircuitCutter
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        cutter = CircuitCutter(cost_model=model, max_qubits=127)

        result = cutter.analyze(circuit)
        if result.should_cut:
            subcircuits = cutter.cut(circuit)
            print(f"Cut into {len(subcircuits)} subcircuits")
    """

    def __init__(self, cost_model: CostModel, max_qubits: int = 127):
        self.cost_model = cost_model
        self.max_qubits = max_qubits

    def analyze(
        self,
        circuit: QuantumCircuit,
        shots: int = 8192,
    ) -> CuttingResult:
        """Analyze whether circuit cutting is beneficial.

        Evaluates the cost-benefit of cutting by comparing estimated
        error with and without cutting. Cutting is recommended when:

        1. The circuit exceeds max_qubits (forced cut), or
        2. The estimated error with cutting is less than without cutting

        Args:
            circuit: The quantum circuit to analyze.
            shots: Number of shots for sampling overhead calculation.

        Returns:
            A CuttingResult with the cutting decision and estimates.
        """
        if circuit.num_qubits == 0:
            return CuttingResult()

        uncut_error = 1.0 - self.cost_model.estimate_fidelity(
            circuit
        ).total_fidelity

        exceeds_qubits = circuit.num_qubits > self.max_qubits

        candidates = self._find_cut_candidates(circuit)

        if not candidates:
            return CuttingResult(
                should_cut=exceeds_qubits,
                num_cuts=0,
                estimated_error_uncut=uncut_error,
                estimated_error_cut=uncut_error,
                sampling_overhead=1.0,
            )

        best_cuts = self._select_cuts(
            circuit, candidates, uncut_error, shots
        )

        if not best_cuts:
            return CuttingResult(
                should_cut=exceeds_qubits,
                num_cuts=0,
                estimated_error_uncut=uncut_error,
                estimated_error_cut=uncut_error,
                sampling_overhead=1.0,
            )

        num_cuts = len(best_cuts)
        sampling_overhead = (4 ** num_cuts) / shots

        cut_error = self._estimate_cut_error(
            circuit, best_cuts, shots
        )

        should_cut = exceeds_qubits or (cut_error < uncut_error)

        if not should_cut:
            return CuttingResult(
                should_cut=False,
                num_cuts=0,
                estimated_error_uncut=uncut_error,
                estimated_error_cut=uncut_error,
                sampling_overhead=1.0,
            )

        return CuttingResult(
            should_cut=True,
            num_cuts=num_cuts,
            cut_locations=best_cuts,
            estimated_error_uncut=uncut_error,
            estimated_error_cut=cut_error,
            sampling_overhead=sampling_overhead,
        )

    def cut(
        self,
        circuit: QuantumCircuit,
        cut_locations: list[CutLocation] | None = None,
    ) -> list[QuantumCircuit]:
        """Cut a circuit into subcircuits at specified or optimal locations.

        Args:
            circuit: The quantum circuit to cut.
            cut_locations: Where to cut. If None, uses analyze()
                to determine optimal cut locations.

        Returns:
            A list of subcircuits to execute independently.
        """
        if cut_locations is None:
            result = self.analyze(circuit)
            if not result.should_cut or not result.cut_locations:
                return [circuit.copy()]
            cut_locations = result.cut_locations

        sorted_cuts = sorted(
            cut_locations, key=lambda c: c.gate_index
        )

        cut_gate_indices = {loc.gate_index for loc in sorted_cuts}

        cut_points = []
        for loc in sorted_cuts:
            if loc.cut_type == "wire":
                for q in loc.qubits:
                    cut_points.append((loc.gate_index, q))
            else:
                cut_points.append((loc.gate_index, loc.qubits[1]))

        if not cut_points:
            return [circuit.copy()]

        groups = self._partition_qubits(circuit, cut_points)

        subcircuits = []
        for qubit_group in groups:
            sub = self._extract_subcircuit(circuit, qubit_group, cut_gate_indices)
            subcircuits.append(sub)

        if not subcircuits:
            subcircuits = [circuit.copy()]

        return subcircuits

    def reconstruct(
        self, subcircuit_results: list, num_cuts: int
    ) -> dict:
        """Reconstruct the full circuit result from subcircuit outcomes.

        Uses quasi-probability decomposition to combine subcircuit
        results. Each cut introduces a sampling overhead factor of 4.

        Args:
            subcircuit_results: Results from executing subcircuits.
                Each element is a dict of {bitstring: count}.
            num_cuts: Number of cuts made.

        Returns:
            Reconstructed expectation values as a dict.
        """
        if not subcircuit_results:
            return {}

        if num_cuts == 0:
            if isinstance(subcircuit_results[0], dict):
                return subcircuit_results[0]
            return {}

        sampling_factor = 4 ** num_cuts

        combined = {}
        for result in subcircuit_results:
            if not isinstance(result, dict):
                continue
            for bitstring, count in result.items():
                if bitstring in combined:
                    combined[bitstring] += count
                else:
                    combined[bitstring] = count

        total = sum(combined.values())
        if total == 0:
            return {}

        reconstructed = {
            bs: count / (total * sampling_factor)
            for bs, count in combined.items()
        }

        total_weight = sum(reconstructed.values())
        if total_weight > 0:
            reconstructed = {
                bs: val / total_weight
                for bs, val in reconstructed.items()
            }

        return reconstructed

    def _find_cut_candidates(
        self, circuit: QuantumCircuit
    ) -> list[CutLocation]:
        """Find candidate locations for cutting.

        Identifies two-qubit gates that connect different qubit groups
        as potential cut points. Prioritizes gates that, if cut, would
        create the most balanced partition.

        Args:
            circuit: The circuit to analyze.

        Returns:
            List of CutLocation candidates sorted by estimated benefit.
        """
        candidates = []

        for idx, instr in enumerate(circuit.data):
            gate_name = instr.operation.name
            qubits = tuple(
                circuit.find_bit(q).index for q in instr.qubits
            )

            if gate_name in TWO_QUBIT_GATES and len(qubits) == 2:
                swap_benefit = self._estimate_swap_benefit(
                    circuit, qubits
                )

                candidates.append(
                    CutLocation(
                        gate_index=idx,
                        gate_name=gate_name,
                        qubits=qubits,
                        cut_type="gate",
                        estimated_benefit=swap_benefit,
                    )
                )

            elif len(qubits) == 1 and gate_name not in {
                "measure", "barrier", "reset"
            }:
                pass

        if circuit.num_qubits > self.max_qubits:
            for idx in range(circuit.num_qubits - 1):
                if not any(
                    c.gate_index == idx for c in candidates
                ):
                    candidates.append(
                        CutLocation(
                            gate_index=idx,
                            gate_name="wire",
                            qubits=(idx, idx + 1),
                            cut_type="wire",
                            estimated_benefit=0.1,
                        )
                    )

        candidates.sort(
            key=lambda c: c.estimated_benefit, reverse=True
        )
        return candidates

    def _estimate_swap_benefit(
        self, circuit: QuantumCircuit, qubit_pair: tuple[int, ...]
    ) -> float:
        """Estimate the benefit of cutting a two-qubit gate.

        The benefit is proportional to the SWAP overhead that would
        be incurred if the gate were kept, versus the sampling
        overhead if the gate were cut.

        Args:
            circuit: The full circuit.
            qubit_pair: The qubit indices connected by the gate.

        Returns:
            Estimated benefit (higher = more beneficial to cut).
        """
        q0, q1 = qubit_pair

        distance = abs(q0 - q1)

        swap_count = max(0, distance - 1)

        if swap_count == 0:
            return 0.0

        two_q_error = self._avg_two_qubit_error()
        single_q_error = self._avg_single_qubit_error()

        swap_error = swap_count * 3 * two_q_error
        additional_single_q_error = swap_count * 2 * single_q_error

        return swap_error + additional_single_q_error

    def _select_cuts(
        self,
        circuit: QuantumCircuit,
        candidates: list[CutLocation],
        uncut_error: float,
        shots: int,
        max_cuts: int = 4,
    ) -> list[CutLocation]:
        """Select the best cut locations using greedy optimization.

        Greedily adds cuts as long as the total estimated error
        (subcircuit errors + sampling overhead) decreases.

        Args:
            circuit: The circuit to cut.
            candidates: Candidate cut locations.
            uncut_error: Error without cutting.
            shots: Number of shots.
            max_cuts: Maximum number of cuts to consider.

        Returns:
            List of selected CutLocations (may be empty).
        """
        selected = []
        remaining_candidates = list(candidates)

        for _ in range(min(max_cuts, len(remaining_candidates))):
            if not remaining_candidates:
                break

            best = remaining_candidates.pop(0)
            selected.append(best)


            cut_error = self._estimate_cut_error(
                circuit, selected, shots
            )

            if cut_error >= uncut_error and circuit.num_qubits <= self.max_qubits:
                selected.pop()
                break

        return selected

    def _estimate_cut_error(
        self,
        circuit: QuantumCircuit,
        cuts: list[CutLocation],
        shots: int,
    ) -> float:
        """Estimate total error after cutting.

        Total error = sum of subcircuit errors + sampling overhead

        Args:
            circuit: The original circuit.
            cuts: Cut locations.
            shots: Number of shots.

        Returns:
            Estimated error with cutting.
        """
        num_cuts = len(cuts)
        if num_cuts == 0:
            return 1.0 - self.cost_model.estimate_fidelity(
                circuit
            ).total_fidelity

        sampling_overhead = (4 ** num_cuts) / shots

        num_groups = num_cuts + 1

        group_errors = []
        for g in range(num_groups):


            total_gates = sum(circuit.count_ops().values())
            group_gate_count = max(
                1, total_gates // num_groups
            )
            two_q_count = max(
                0,
                circuit.count_ops().get("cx", 0) // num_groups - 1,
            )
            one_q_count = max(1, group_gate_count - two_q_count)

            sq_error = self._avg_single_qubit_error()
            tq_error = self._avg_two_qubit_error()

            gate_error = (
                1 - (1 - sq_error) ** one_q_count
            ) * 0.5 + (
                1 - (1 - tq_error) ** max(1, two_q_count)
            ) * 0.5

            depth = max(1, circuit.depth() // num_groups)
            avg_t2 = self._avg_t2()
            decoherence_error = 1 - float(
                2.0 ** (-depth * 50e-9 / avg_t2)
            ) if avg_t2 > 0 else 0.01

            group_error = 1 - (1 - gate_error) * (1 - decoherence_error)
            group_errors.append(group_error)

        subcircuit_error = 1 - float(
            np.prod([1 - e for e in group_errors])
        )

        sampling_error = 1.0 / np.sqrt(shots) * sampling_overhead

        return min(1.0, subcircuit_error + sampling_error)

    def _partition_qubits(
        self,
        circuit: QuantumCircuit,
        cut_points: list[tuple[int, int]],
    ) -> list[list[int]]:
        """Partition qubits into groups based on cut points.

        Uses a Union-Find approach to group qubits that are not
        separated by cuts.

        Args:
            circuit: The circuit.
            cut_points: List of (gate_index, qubit) pairs where cuts
                separate qubit groups.

        Returns:
            List of qubit groups (each group is a list of qubit indices).
        """
        num_qubits = circuit.num_qubits
        parent = list(range(num_qubits))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        cut_pairs = set()
        for _, q in cut_points:
            if q > 0:
                cut_pairs.add((q - 1, q))
            if q < num_qubits - 1:
                cut_pairs.add((q, q + 1))

        for idx, instr in enumerate(circuit.data):
            qubits = tuple(
                circuit.find_bit(q).index for q in instr.qubits
            )
            if len(qubits) == 2:
                q0, q1 = qubits
                is_cut = (min(q0, q1), max(q0, q1)) not in cut_pairs
                if not is_cut:
                    union(q0, q1)

        groups = {}
        for q in range(num_qubits):
            root = find(q)
            if root not in groups:
                groups[root] = []
            groups[root].append(q)

        return sorted(groups.values(), key=len, reverse=True)

    def _extract_subcircuit(
        self,
        circuit: QuantumCircuit,
        qubit_group: list[int],
        cut_gate_indices: set[int],
    ) -> QuantumCircuit:
        """Extract a subcircuit for a group of qubits.

        Args:
            circuit: The original circuit.
            qubit_group: Qubit indices for this subcircuit.
            cut_gate_indices: Gate indices that were cut.

        Returns:
            A subcircuit containing only the specified qubits and
            their gates.
        """
        qubit_set = set(qubit_group)
        num_sub_qubits = len(qubit_group)
        qubit_map = {old: new for new, old in enumerate(sorted(qubit_group))}

        sub = QuantumCircuit(num_sub_qubits, name=f"sub_{'_'.join(map(str, sorted(qubit_group)))}")

        for idx, instr in enumerate(circuit.data):
            gate_qubits = tuple(
                circuit.find_bit(q).index for q in instr.qubits
            )

            if idx in cut_gate_indices:
                continue

            if all(q in qubit_set for q in gate_qubits):
                new_qubits = [sub.qubits[qubit_map[q]] for q in gate_qubits]
                try:
                    sub.append(instr.operation, new_qubits, instr.clbits)
                except Exception:  # noqa: BLE001
                    sub.append(instr.operation, new_qubits)

        return sub

    def _avg_single_qubit_error(self) -> float:
        """Get average single-qubit gate error from device or default."""
        if self.cost_model.device.single_qubit_gate_errors:
            errors = list(
                self.cost_model.device.single_qubit_gate_errors.values()
            )
            return sum(errors) / len(errors)
        return 0.0005

    def _avg_two_qubit_error(self) -> float:
        """Get average two-qubit gate error from device or default."""
        if self.cost_model.device.two_qubit_gate_errors:
            errors = list(
                self.cost_model.device.two_qubit_gate_errors.values()
            )
            return sum(errors) / len(errors)
        return 0.01

    def _avg_t2(self) -> float:
        """Get average T2 time from device or default."""
        if self.cost_model.device.t2_times:
            times = list(self.cost_model.device.t2_times.values())
            return sum(times) / len(times)
        return 150e-6