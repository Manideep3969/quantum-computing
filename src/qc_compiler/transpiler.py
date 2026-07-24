"""Transpiler integration module for qc-compiler.

Provides a unified interface that combines all six optimizations
and integrates with Qiskit's transpiler pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2

from qc_compiler.cost_model import CostModel
from qc_compiler.fusion import GateFusion
from qc_compiler.cutting import CircuitCutter
from qc_compiler.mitigation import AdaptiveErrorMitigation
from qc_compiler.scheduling import CoherenceAwareScheduler
from qc_compiler.batching import CircuitBatcher
from qc_compiler.autotuning import AutoTuner


@dataclass
class OptimizerConfig:
    """Configuration for which optimizations to apply."""

    fusion: bool = True
    cutting: bool = True
    mitigation: str = "adaptive"
    scheduling: str = "coherence_aware"
    batch: bool = True
    autotune: bool = True


class QCompiler:
    """Main interface for hardware-aware quantum circuit optimization.

    Usage:
        from qc_compiler import QCompiler
        from qiskit_ibm_runtime import QiskitRuntimeService

        service = QiskitRuntimeService()
        backend = service.backend("ibm_brisbane")
        compiler = QCompiler(backend=backend)
        optimized = compiler.optimize(circuit, config=OptimizerConfig())
    """

    def __init__(
        self,
        backend: Optional[BackendV2] = None,
        max_qubits: int = 127,
    ):
        self.backend = backend
        self.cost_model = CostModel(backend=backend)
        self.fusion = GateFusion(cost_model=self.cost_model)
        self.cutter = CircuitCutter(
            cost_model=self.cost_model, max_qubits=max_qubits
        )
        self.mitigation = AdaptiveErrorMitigation(cost_model=self.cost_model)
        self.scheduler = CoherenceAwareScheduler(cost_model=self.cost_model)
        self.batcher = CircuitBatcher(cost_model=self.cost_model)
        self.autotuner = AutoTuner(cost_model=self.cost_model, backend=backend)

    def optimize(
        self,
        circuit: QuantumCircuit,
        config: Optional[OptimizerConfig] = None,
    ) -> QuantumCircuit:
        """Apply all enabled optimizations to a quantum circuit.

        Args:
            circuit: The quantum circuit to optimize.
            config: Configuration for which optimizations to apply.

        Returns:
            An optimized quantum circuit.
        """
        if config is None:
            config = OptimizerConfig()

        raise NotImplementedError("Full optimization pipeline not yet implemented")