"""Transpiler integration module for qc-compiler.

Provides a unified interface that composes all six optimizations
into a single pipeline, analogous to how a GPU compiler chains
kernel fusion, memory optimization, precision scaling, and
autotuning into a single compilation pass.

The pipeline applies optimizations in order:

    1. Autotuning: Find the best transpilation configuration
    2. Gate Fusion: Merge sequential single-qubit gates
    3. Circuit Cutting: Partition if circuit exceeds device qubits
    4. Coherence-Aware Scheduling: Minimize idle qubit time
    5. Adaptive Error Mitigation: Allocate shots and noise scales
    6. Circuit Batching: Group circuits sharing the same unitary core

Each pass can be individually enabled/disabled via OptimizerConfig.
The pipeline returns a QCompilerResult with the optimized circuit,
all intermediate results, and a comparison of fidelity before and
after optimization.
"""

from dataclasses import dataclass, field

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2

from qc_compiler.autotuning import AutoTuner, AutotuneResult
from qc_compiler.batching import BatchPlan, CircuitBatcher
from qc_compiler.cost_model import CostModel
from qc_compiler.cutting import CircuitCutter, CuttingResult
from qc_compiler.fusion import FusionResult, GateFusion
from qc_compiler.mitigation import (
    AdaptiveErrorMitigation,
    MitigationPlan,
)
from qc_compiler.scheduling import CoherenceAwareScheduler, ScheduleResult


@dataclass
class OptimizerConfig:
    """Configuration for which optimizations to apply.

    Attributes:
        fusion: Whether to apply gate fusion.
        cutting: Whether to apply circuit cutting when beneficial.
        mitigation: Error mitigation strategy — 'adaptive', 'zne',
            'pec', 'cdr', or 'none' to disable.
        scheduling: Scheduling method — 'asap', 'alap',
            'coherence_aware', or 'none' to disable.
        batch: Whether to enable circuit batching.
        autotune: Whether to search for optimal transpile config.
    """

    fusion: bool = True
    cutting: bool = True
    mitigation: str = "adaptive"
    scheduling: str = "coherence_aware"
    batch: bool = True
    autotune: bool = False


@dataclass
class QCompilerResult:
    """Result of the full optimization pipeline.

    Attributes:
        original_circuit: The input circuit before optimization.
        optimized_circuit: The final optimized circuit.
        fidelity_before: Estimated fidelity before optimization.
        fidelity_after: Estimated fidelity after optimization.
        fusion_result: Result from gate fusion pass (if applied).
        cutting_result: Result from circuit cutting pass (if applied).
        schedule_result: Result from scheduling pass (if applied).
        mitigation_plan: Mitigation plan (if applied).
        batch_plan: Batch plan (if applied).
        autotune_result: Autotune result (if applied).
        passes_applied: List of optimization pass names that were applied.
        config: The OptimizerConfig used.
    """

    original_circuit: QuantumCircuit = None
    optimized_circuit: QuantumCircuit = None
    fidelity_before: float = 0.0
    fidelity_after: float = 0.0
    fusion_result: FusionResult | None = None
    cutting_result: CuttingResult | None = None
    schedule_result: ScheduleResult | None = None
    mitigation_plan: MitigationPlan | None = None
    autotune_result: AutotuneResult | None = None
    batch_plan: BatchPlan | None = None
    subcircuits: list[QuantumCircuit] | None = None
    passes_applied: list[str] = field(default_factory=list)
    config: OptimizerConfig = None

    @property
    def fidelity_improvement(self) -> float:
        """Absolute fidelity improvement (after - before)."""
        return self.fidelity_after - self.fidelity_before

    @property
    def fidelity_improvement_pct(self) -> float:
        """Percentage fidelity improvement."""
        if self.fidelity_before == 0:
            return 0.0
        return (self.fidelity_after - self.fidelity_before) / self.fidelity_before * 100


class QCompiler:
    """Main interface for hardware-aware quantum circuit optimization.

    Composes all six optimization passes into a single pipeline.
    Each pass can be individually enabled/disabled via OptimizerConfig.

    Usage::

        from qc_compiler import QCompiler, OptimizerConfig
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        backend = FakeBrisbane()
        compiler = QCompiler(backend=backend)

        result = compiler.optimize(circuit)
        print(f"Fidelity: {result.fidelity_before:.4f} -> {result.fidelity_after:.4f}")
        print(f"Passes applied: {result.passes_applied}")
    """

    def __init__(
        self,
        backend: BackendV2 | None = None,
        max_qubits: int = 127,
    ):
        self.backend = backend
        self.cost_model = CostModel(backend=backend)
        self.fusion = GateFusion(cost_model=self.cost_model)
        self.cutter = CircuitCutter(
            cost_model=self.cost_model, max_qubits=max_qubits
        )
        self.mitigation = AdaptiveErrorMitigation(
            cost_model=self.cost_model
        )
        self.scheduler = CoherenceAwareScheduler(
            cost_model=self.cost_model
        )
        self.batcher = CircuitBatcher(cost_model=self.cost_model)
        self.autotuner = AutoTuner(
            cost_model=self.cost_model, backend=backend
        )

    def optimize(
        self,
        circuit: QuantumCircuit,
        config: OptimizerConfig | None = None,
    ) -> QCompilerResult:
        """Apply all enabled optimizations to a quantum circuit.

        The pipeline applies optimizations in the following order:
        1. Autotuning (find best transpile config)
        2. Gate fusion (merge sequential single-qubit gates)
        3. Circuit cutting (partition if needed)
        4. Scheduling (minimize idle time)
        5. Error mitigation (create mitigation plan)

        Args:
            circuit: The quantum circuit to optimize.
            config: Configuration for which optimizations to apply.

        Returns:
            A QCompilerResult with the optimized circuit and metrics.
        """
        if config is None:
            config = OptimizerConfig()

        result = QCompilerResult(
            original_circuit=circuit.copy(),
            config=config,
        )

        current_circuit = circuit.copy()
        passes_applied = []

        fidelity_before = self.cost_model.estimate_fidelity(
            current_circuit
        ).total_fidelity
        result.fidelity_before = fidelity_before

        # Pass 1: Autotuning
        if config.autotune:
            autotune_result = self.autotuner.search(
                current_circuit, circuit_family="default"
            )
            result.autotune_result = autotune_result
            if autotune_result.best_circuit is not None:
                current_circuit = autotune_result.best_circuit
            passes_applied.append("autotune")

        # Pass 2: Gate Fusion
        if config.fusion:
            fusion_result = self.fusion.optimize(current_circuit)
            if fusion_result.chains_fused > 0:
                current_circuit = fusion_result.optimized_circuit
            result.fusion_result = fusion_result
            passes_applied.append("fusion")

        # Pass 3: Circuit Cutting
        if config.cutting:
            cutting_result = self.cutter.analyze(current_circuit)
            result.cutting_result = cutting_result
            passes_applied.append("cutting")

            if cutting_result.should_cut and cutting_result.num_cuts > 0:
                subcircuits = self.cutter.cut(current_circuit)
                if subcircuits and len(subcircuits) > 1:
                    result.subcircuits = subcircuits

                    sub_results = []
                    for sub in subcircuits:
                        sub_result = QCompilerResult(
                            original_circuit=sub.copy(),
                            config=config,
                        )
                        sub_current = sub.copy()

                        sub_fidelity_before = self.cost_model.estimate_fidelity(
                            sub_current
                        ).total_fidelity
                        sub_result.fidelity_before = sub_fidelity_before

                        if config.scheduling != "none":
                            sub_schedule = self.scheduler.schedule(
                                sub_current, method=config.scheduling
                            )
                            sub_current = sub_schedule.circuit
                            sub_result.schedule_result = sub_schedule
                            sub_result.passes_applied.append(
                                f"scheduling:{config.scheduling}"
                            )

                        if config.mitigation != "none":
                            sub_mitigation = self.mitigation.create_plan(
                                sub_current, method=config.mitigation
                            )
                            sub_result.mitigation_plan = sub_mitigation
                            sub_result.passes_applied.append(
                                f"mitigation:{config.mitigation}"
                            )

                        sub_fidelity_after = self.cost_model.estimate_fidelity(
                            sub_current
                        ).total_fidelity
                        sub_result.fidelity_after = sub_fidelity_after
                        sub_result.optimized_circuit = sub_current

                        sub_results.append(sub_result)

                    sampling_overhead = cutting_result.sampling_overhead
                    sub_fidelities = [r.fidelity_after for r in sub_results]
                    combined_fidelity = 1.0
                    for f in sub_fidelities:
                        combined_fidelity *= f
                    combined_fidelity /= max(sampling_overhead, 1e-10)

                    result.fidelity_after = combined_fidelity
                    result.optimized_circuit = subcircuits[0]
                    result.passes_applied = passes_applied

                    return result

        # Pass 4: Scheduling
        if config.scheduling != "none":
            schedule_result = self.scheduler.schedule(
                current_circuit, method=config.scheduling
            )
            current_circuit = schedule_result.circuit
            result.schedule_result = schedule_result
            passes_applied.append(f"scheduling:{config.scheduling}")

        # Pass 5: Error Mitigation
        if config.mitigation != "none":
            mitigation_plan = self.mitigation.create_plan(
                current_circuit, method=config.mitigation
            )
            result.mitigation_plan = mitigation_plan
            passes_applied.append(f"mitigation:{config.mitigation}")

        fidelity_after = self.cost_model.estimate_fidelity(
            current_circuit
        ).total_fidelity
        result.fidelity_after = fidelity_after

        result.optimized_circuit = current_circuit
        result.passes_applied = passes_applied

        return result

    def optimize_batch(
        self,
        circuits: list[QuantumCircuit],
        config: OptimizerConfig | None = None,
    ) -> list[QCompilerResult]:
        """Optimize a batch of circuits.

        Applies the optimization pipeline to each circuit, then
        optionally groups them for batched execution.

        Args:
            circuits: List of quantum circuits to optimize.
            config: Configuration for which optimizations to apply.

        Returns:
            List of QCompilerResults, one per circuit.
        """
        if config is None:
            config = OptimizerConfig()

        results = []
        for circuit in circuits:
            result = self.optimize(circuit, config)
            results.append(result)

        if config.batch:
            optimized_circuits = [r.optimized_circuit for r in results]
            batch_plan = self.batcher.create_batch_plan(optimized_circuits)
            for result in results:
                result.batch_plan = batch_plan

        return results