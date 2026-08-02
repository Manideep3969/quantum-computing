"""qc-compiler: Hardware-aware quantum circuit optimization framework.

Bridges classical GPU compilation techniques to NISQ quantum devices.
Provides six optimizations inspired by GPU compiler analogies:
  1. Gate fusion (kernel fusion)
  2. Circuit cutting (model parallelism)
  3. Adaptive error mitigation (mixed-precision training)
  4. Decoherence budget optimization (memory-bandwidth optimization)
  5. Circuit batching (batched inference)
  6. Hardware-aware autotuning (kernel autotuning)
"""

__version__ = "0.1.0"

from qc_compiler.cost_model import CostModel, DeviceCharacterization, CircuitMetrics, ErrorBreakdown
from qc_compiler.fusion import GateFusion
from qc_compiler.cutting import CircuitCutter, CuttingResult
from qc_compiler.mitigation import AdaptiveErrorMitigation, MitigationPlan, MitigationResult
from qc_compiler.scheduling import CoherenceAwareScheduler, ScheduleResult
from qc_compiler.batching import CircuitBatcher, BatchPlan
from qc_compiler.autotuning import AutoTuner, TranspileConfig, AutotuneResult
from qc_compiler.transpiler import QCompiler, OptimizerConfig, QCompilerResult
from qc_compiler.utils import get_backend_properties, compute_circuit_depth, compute_cnot_count, compute_idle_fraction, get_avg_gate_time

__all__ = [
    "CostModel",
    "DeviceCharacterization",
    "CircuitMetrics",
    "ErrorBreakdown",
    "GateFusion",
    "CircuitCutter",
    "CuttingResult",
    "AdaptiveErrorMitigation",
    "MitigationPlan",
    "MitigationResult",
    "CoherenceAwareScheduler",
    "ScheduleResult",
    "CircuitBatcher",
    "BatchPlan",
    "AutoTuner",
    "TranspileConfig",
    "AutotuneResult",
    "QCompiler",
    "OptimizerConfig",
    "QCompilerResult",
    "get_backend_properties",
    "compute_circuit_depth",
    "compute_cnot_count",
    "compute_idle_fraction",
    "get_avg_gate_time",
]