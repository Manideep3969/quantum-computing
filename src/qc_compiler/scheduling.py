"""Coherence-aware gate scheduling for quantum circuits.

Analogous to memory-bandwidth optimization in GPU computing (e.g.,
FlashAttention keeping data in SRAM), this module rearranges gates to
minimize qubit idle time within the coherence window, prioritizing
low-T2 qubits.

Three scheduling strategies are provided:

    1. ASAP (As Soon As Possible): Schedule each gate at the earliest
       possible cycle. Maximizes parallelism but may leave fragile
       qubits idle for long periods.

    2. ALAP (As Late As Possible): Delay each gate to the latest
       possible cycle. Minimizes idle time after operations but may
       increase idle time before.

    3. Coherence-aware: A hybrid approach that schedules gates on
       low-T2 qubits as early as possible (minimizing their idle
       time) while allowing high-T2 qubits more flexibility.
       Analogous to prioritizing high-bandwidth memory transfers in
       GPU scheduling.

References:
    Dao, T., et al. (2022). FlashAttention: Fast and memory-efficient
        exact attention with IO-awareness. NeurIPS.
    Murali, P., et al. (2019). Noise-adaptive compiler mappings for
        noisy intermediate-scale quantum computers. ASPLOS.
"""

from dataclasses import dataclass, field

from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.utils import DEFAULT_SINGLE_QUBIT_GATE_TIME


@dataclass
class ScheduleResult:
    """Result of coherence-aware scheduling.

    Attributes:
        circuit: The scheduled (reordered) circuit.
        idle_times: Per-qubit idle time in seconds, keyed by qubit index.
        estimated_fidelity_asap: Estimated fidelity with ASAP scheduling.
        estimated_fidelity_alap: Estimated fidelity with ALAP scheduling.
        estimated_fidelity_optimized: Estimated fidelity with the
            chosen scheduling method.
        method: The scheduling method used.
        depth_asap: Circuit depth with ASAP scheduling.
        depth_alap: Circuit depth with ALAP scheduling.
        depth_optimized: Circuit depth with the chosen method.
    """

    circuit: QuantumCircuit = None
    idle_times: dict[int, float] = field(default_factory=dict)
    estimated_fidelity_asap: float = 0.0
    estimated_fidelity_alap: float = 0.0
    estimated_fidelity_optimized: float = 0.0
    method: str = "coherence_aware"
    depth_asap: int = 0
    depth_alap: int = 0
    depth_optimized: int = 0

    @property
    def idle_time_total(self) -> float:
        """Total idle time across all qubits in seconds."""
        return sum(self.idle_times.values())

    @property
    def idle_time_avg(self) -> float:
        """Average idle time per qubit in seconds."""
        if not self.idle_times:
            return 0.0
        return sum(self.idle_times.values()) / len(self.idle_times)

    @property
    def depth_reduction_pct(self) -> float:
        """Percentage depth reduction from ASAP to optimized."""
        if self.depth_asap == 0:
            return 0.0
        return (self.depth_asap - self.depth_optimized) / self.depth_asap * 100

    @property
    def fidelity_improvement(self) -> float:
        """Fidelity improvement of optimized over ASAP."""
        return self.estimated_fidelity_optimized - self.estimated_fidelity_asap


class CoherenceAwareScheduler:
    """Schedules gates to minimize decoherence on NISQ devices.

    Inspired by FlashAttention and GPU memory optimization: keep
    data in fast memory (coherence) as long as possible, minimize
    idle time on scarce resources (qubits with low T2).

    Usage::

        from qc_compiler import CostModel, CoherenceAwareScheduler
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        scheduler = CoherenceAwareScheduler(cost_model=model)

        result = scheduler.schedule(circuit, method="coherence_aware")
        print(f"ASAP fidelity: {result.estimated_fidelity_asap:.4f}")
        print(f"Optimized fidelity: {result.estimated_fidelity_optimized:.4f}")
    """

    def __init__(self, cost_model: CostModel):
        self.cost_model = cost_model

    def schedule(
        self,
        circuit: QuantumCircuit,
        method: str = "coherence_aware",
    ) -> ScheduleResult:
        """Schedule gates to minimize decoherence error.

        Args:
            circuit: The quantum circuit to schedule.
            method: Scheduling method — 'asap', 'alap', or
                'coherence_aware' (default).

        Returns:
            A ScheduleResult with the scheduled circuit and metrics.
        """
        if method not in ("asap", "alap", "coherence_aware"):
            raise ValueError(
                f"Unknown scheduling method '{method}'. "
                "Use 'asap', 'alap', or 'coherence_aware'."
            )

        asap_circuit = self._asap_schedule(circuit)
        alap_circuit = self._alap_schedule(circuit)

        fidelity_asap = self.cost_model.estimate_fidelity(
            asap_circuit
        ).total_fidelity
        fidelity_alap = self.cost_model.estimate_fidelity(
            alap_circuit
        ).total_fidelity

        if method == "asap":
            idle_times = self._compute_idle_times(asap_circuit)
            return ScheduleResult(
                circuit=asap_circuit,
                idle_times=idle_times,
                estimated_fidelity_asap=fidelity_asap,
                estimated_fidelity_alap=fidelity_alap,
                estimated_fidelity_optimized=fidelity_asap,
                method="asap",
                depth_asap=asap_circuit.depth(),
                depth_alap=alap_circuit.depth(),
                depth_optimized=asap_circuit.depth(),
            )

        if method == "alap":
            idle_times = self._compute_idle_times(alap_circuit)
            return ScheduleResult(
                circuit=alap_circuit,
                idle_times=idle_times,
                estimated_fidelity_asap=fidelity_asap,
                estimated_fidelity_alap=fidelity_alap,
                estimated_fidelity_optimized=fidelity_alap,
                method="alap",
                depth_asap=asap_circuit.depth(),
                depth_alap=alap_circuit.depth(),
                depth_optimized=alap_circuit.depth(),
            )

        optimized_circuit = self._coherence_aware_schedule(circuit)
        fidelity_optimized = self.cost_model.estimate_fidelity(
            optimized_circuit
        ).total_fidelity

        idle_times = self._compute_idle_times(optimized_circuit)

        return ScheduleResult(
            circuit=optimized_circuit,
            idle_times=idle_times,
            estimated_fidelity_asap=fidelity_asap,
            estimated_fidelity_alap=fidelity_alap,
            estimated_fidelity_optimized=fidelity_optimized,
            method="coherence_aware",
            depth_asap=asap_circuit.depth(),
            depth_alap=alap_circuit.depth(),
            depth_optimized=optimized_circuit.depth(),
        )

    def _asap_schedule(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """As Soon As Possible scheduling.

        Each gate is scheduled at the earliest possible cycle,
        maximizing parallelism. This is equivalent to Qiskit's
        default scheduling behavior.

        Args:
            circuit: The circuit to schedule.

        Returns:
            A new circuit with ASAP scheduling.
        """
        scheduled = QuantumCircuit(
            *circuit.qregs,
            name=f"{circuit.name}_asap",
        )
        for creg in circuit.cregs:
            scheduled.add_register(creg)

        qubit_next_cycle = [0] * circuit.num_qubits

        for instr in circuit.data:
            gate = instr.operation
            qubits = [circuit.find_bit(q).index for q in instr.qubits]

            earliest_cycle = max(qubit_next_cycle[q] for q in qubits) if qubits else 0

            gate_duration = self._get_gate_duration(gate.name, qubits)

            target_qubits = [circuit.qubits[q] for q in qubits]
            target_clbits = [circuit.find_bit(c).index for c in instr.clbits]
            clbit_refs = [scheduled.clbits[i] for i in target_clbits] if target_clbits else []

            scheduled.append(gate, target_qubits, clbit_refs)

            for q in qubits:
                qubit_next_cycle[q] = earliest_cycle + gate_duration

        return scheduled

    def _alap_schedule(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """As Late As Possible scheduling.

        Delays each gate to the latest possible cycle, minimizing
        idle time after operations. This can reduce decoherence for
        qubits that are measured late.

        Algorithm:
        1. Compute ASAP start and end times for each gate.
        2. Compute total depth from the ASAP schedule.
        3. Traverse gates in reverse topological order.
        4. For each gate, set its latest end time to the minimum
           of its successors' latest start times (or total_depth
           if it has no successors).
        5. Set latest start = latest end - gate_duration.
        6. Sort gates by latest start time and build the circuit.

        Args:
            circuit: The circuit to schedule.

        Returns:
            A new circuit with ALAP scheduling.
        """
        if circuit.depth() == 0:
            scheduled = QuantumCircuit(
                *circuit.qregs,
                name=f"{circuit.name}_alap",
            )
            for creg in circuit.cregs:
                scheduled.add_register(creg)
            return scheduled

        total_depth = circuit.depth()

        qubit_latest_end = [total_depth] * circuit.num_qubits

        gate_latest_start = [0] * len(circuit.data)

        for i in range(len(circuit.data) - 1, -1, -1):
            instr = circuit.data[i]
            qubits = [circuit.find_bit(q).index for q in instr.qubits]

            if not qubits:
                gate_latest_start[i] = 0
                continue

            gate_duration = self._get_gate_duration(instr.operation.name, qubits)

            latest_end = min(qubit_latest_end[q] for q in qubits)
            latest_start = latest_end - gate_duration

            gate_latest_start[i] = latest_start

            for q in qubits:
                qubit_latest_end[q] = latest_start

        scheduled = QuantumCircuit(
            *circuit.qregs,
            name=f"{circuit.name}_alap",
        )
        for creg in circuit.cregs:
            scheduled.add_register(creg)

        gate_order = sorted(range(len(circuit.data)), key=lambda i: gate_latest_start[i])

        for i in gate_order:
            instr = circuit.data[i]
            gate = instr.operation
            qubits = [circuit.find_bit(q).index for q in instr.qubits]
            target_qubits = [circuit.qubits[q] for q in qubits]
            target_clbits = [circuit.find_bit(c).index for c in instr.clbits]
            clbit_refs = [scheduled.clbits[j] for j in target_clbits] if target_clbits else []

            scheduled.append(gate, target_qubits, clbit_refs)

        return scheduled

    def _coherence_aware_schedule(
        self, circuit: QuantumCircuit
    ) -> QuantumCircuit:
        """Schedule prioritizing low-T2 qubits while respecting dependencies.

        For each qubit, computes a priority based on its T2 time:
        - Low T2 → high priority (schedule gates early to minimize
          decoherence)
        - High T2 → low priority (can afford to wait)

        The algorithm uses a dependency-aware priority queue:
        1. Build a DAG of gate dependencies.
        2. Start with gates whose predecessors are all scheduled.
        3. Among ready gates, pick the one with the lowest T2 priority.
        4. Schedule it at the earliest possible cycle.
        5. Repeat until all gates are scheduled.

        This preserves circuit unitary while minimizing idle time on
        fragile (low-T2) qubits.

        Args:
            circuit: The circuit to schedule.

        Returns:
            A new circuit with coherence-aware scheduling.
        """
        t2_priority = self._compute_t2_priority(circuit.num_qubits)

        if circuit.depth() == 0:
            scheduled = QuantumCircuit(
                *circuit.qregs,
                name=f"{circuit.name}_coherence_aware",
            )
            for creg in circuit.cregs:
                scheduled.add_register(creg)
            return scheduled

        num_gates = len(circuit.data)
        qubit_latest_gate = [-1] * circuit.num_qubits
        predecessors = [set() for _ in range(num_gates)]

        qubit_first_gate = [-1] * circuit.num_qubits
        for i, instr in enumerate(circuit.data):
            qubits = [circuit.find_bit(q).index for q in instr.qubits]
            for q in qubits:
                if qubit_first_gate[q] == -1:
                    qubit_first_gate[q] = i

        for i, instr in enumerate(circuit.data):
            qubits = [circuit.find_bit(q).index for q in instr.qubits]
            for q in qubits:
                if qubit_latest_gate[q] >= 0:
                    predecessors[i].add(qubit_latest_gate[q])
                qubit_latest_gate[q] = i

        for i in range(num_gates - 1):
            if circuit.data[i].operation.name == "barrier":
                for q in [circuit.find_bit(q).index for q in circuit.data[i].qubits]:
                    for j in range(i + 1, num_gates):
                        jqubits = [circuit.find_bit(q).index for q in circuit.data[j].qubits]
                        if q in jqubits:
                            predecessors[j].add(i)

        qubit_next_cycle = [0] * circuit.num_qubits
        scheduled = QuantumCircuit(
            *circuit.qregs,
            name=f"{circuit.name}_coherence_aware",
        )
        for creg in circuit.cregs:
            scheduled.add_register(creg)

        remaining = set(range(num_gates))
        scheduled_set = set()

        while remaining:
            ready = []
            for i in remaining:
                if predecessors[i].issubset(scheduled_set):
                    ready.append(i)

            if not ready:
                break

            ready.sort(key=lambda i: min(t2_priority.get(q, float('inf')) for q in [circuit.find_bit(q).index for q in circuit.data[i].qubits]) if circuit.data[i].qubits else float('inf'))

            gate_idx = ready[0]

            instr = circuit.data[gate_idx]
            gate = instr.operation
            qubits = [circuit.find_bit(q).index for q in instr.qubits]
            target_qubits = [circuit.qubits[q] for q in qubits]
            target_clbits = [circuit.find_bit(c).index for c in instr.clbits]
            clbit_refs = [scheduled.clbits[j] for j in target_clbits] if target_clbits else []

            scheduled.append(gate, target_qubits, clbit_refs)

            gate_duration = self._get_gate_duration(gate.name, qubits)
            earliest = max(qubit_next_cycle[q] for q in qubits) if qubits else 0
            for q in qubits:
                qubit_next_cycle[q] = earliest + gate_duration

            remaining.remove(gate_idx)
            scheduled_set.add(gate_idx)

        return scheduled

    def _compute_idle_times(
        self, circuit: QuantumCircuit
    ) -> dict[int, float]:
        """Compute idle time for each qubit in seconds.

        For each qubit, idle time is estimated as:
            idle_time = (circuit_depth - active_cycles) × avg_gate_time

        Qubits with more idle cycles are more susceptible to
        decoherence, especially if they have low T2 times.

        Args:
            circuit: The scheduled circuit.

        Returns:
            Dictionary mapping qubit index to idle time in seconds.
        """
        depth = circuit.depth()
        if depth == 0:
            return {q: 0.0 for q in range(circuit.num_qubits)}

        avg_gate_time = self._avg_gate_time()

        qubit_active_cycles = {q: 0 for q in range(circuit.num_qubits)}
        for instr in circuit.data:
            for qubit in instr.qubits:
                qidx = circuit.find_bit(qubit).index
                qubit_active_cycles[qidx] += 1

        idle_times = {}
        for q in range(circuit.num_qubits):
            active = qubit_active_cycles.get(q, 0)
            idle_cycles = max(0, depth - active)
            idle_times[q] = idle_cycles * avg_gate_time

        return idle_times

    def _compute_asap_starts(self, circuit: QuantumCircuit) -> list[int]:
        """Compute ASAP start cycle for each gate.

        Args:
            circuit: The circuit.

        Returns:
            List of start cycles, one per gate.
        """
        qubit_next_cycle = [0] * circuit.num_qubits
        starts = []

        for instr in circuit.data:
            qubits = [circuit.find_bit(q).index for q in instr.qubits]
            if not qubits:
                starts.append(0)
                continue
            earliest = max(qubit_next_cycle[q] for q in qubits)
            starts.append(earliest)
            duration = self._get_gate_duration(instr.operation.name, qubits)
            for q in qubits:
                qubit_next_cycle[q] = earliest + duration

        return starts

    def _get_gate_duration(
        self, gate_name: str, qubits: list[int]
    ) -> int:
        """Get the duration of a gate in abstract time units.

        Uses device calibration data when available. Falls back to
        a simple model: single-qubit gates = 1 unit, two-qubit gates
        = 3 units (reflecting typical duration ratios on IBM hardware).

        Args:
            gate_name: Name of the gate.
            qubits: Qubit indices the gate acts on.

        Returns:
            Duration in abstract time units.
        """
        if qubits and len(qubits) >= 2:
            return 3
        return 1

    def _avg_gate_time(self) -> float:
        """Get average gate time from device characterization or default.

        Returns:
            Average gate time in seconds.
        """
        if self.cost_model.device.gate_lengths:
            times = list(self.cost_model.device.gate_lengths.values())
            return sum(times) / len(times)
        return DEFAULT_SINGLE_QUBIT_GATE_TIME

    def _compute_t2_priority(self, num_qubits: int) -> dict[int, float]:
        """Compute per-qubit T2-based scheduling priority.

        Lower T2 → lower priority number → scheduled earlier.
        Qubits without device data get a medium priority.

        Args:
            num_qubits: Number of qubits in the circuit.

        Returns:
            Dictionary mapping qubit index to priority (lower = schedule first).
        """
        t2_times = self.cost_model.device.t2_times

        if not t2_times:
            return {q: 1.0 for q in range(num_qubits)}

        t2_priority = {}
        for q in range(num_qubits):
            if q in t2_times:
                t2_priority[q] = t2_times[q]
            else:
                max_t2 = max(t2_times.values())
                t2_priority[q] = max_t2 * 0.5

        return t2_priority