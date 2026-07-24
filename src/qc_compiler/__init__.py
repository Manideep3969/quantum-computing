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

from qc_compiler.cost_model import CostModel
from qc_compiler.fusion import GateFusion
from qc_compiler.cutting import CircuitCutter
from qc_compiler.mitigation import AdaptiveErrorMitigation
from qc_compiler.scheduling import CoherenceAwareScheduler
from qc_compiler.batching import CircuitBatcher
from qc_compiler.autotuning import AutoTuner

__all__ = [
    "CostModel",
    "GateFusion",
    "CircuitCutter",
    "AdaptiveErrorMitigation",
    "CoherenceAwareScheduler",
    "CircuitBatcher",
    "AutoTuner",
]