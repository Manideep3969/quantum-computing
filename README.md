# qc-compiler

[![CI](https://github.com/Manideep3969/quantum-computing/actions/workflows/ci.yml/badge.svg)](https://github.com/Manideep3969/quantum-computing/actions/workflows/ci.yml)
[![Notebooks](https://github.com/Manideep3969/quantum-computing/actions/workflows/notebooks.yml/badge.svg)](https://github.com/Manideep3969/quantum-computing/actions/workflows/notebooks.yml)
[![License](https://img.shields.io/github/license/Manideep3969/quantum-computing)](LICENSE)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

Hardware-aware quantum circuit optimization framework bridging classical compilation techniques to NISQ devices.

## Overview

`qc-compiler` maps six proven GPU compilation techniques to quantum circuit compilation, providing a unified pipeline that adapts optimizations to real hardware characteristics. It targets IBM Quantum devices and uses device calibration data to drive every optimization decision.

| Classical (GPU) | Quantum (NISQ) | Module |
|---|---|---|
| Kernel fusion | Gate fusion | `fusion.py` |
| Model parallelism | Circuit cutting | `cutting.py` |
| Mixed-precision training | Adaptive error mitigation | `mitigation.py` |
| Memory-bandwidth optimization | Decoherence budget scheduling | `scheduling.py` |
| Batched inference | Circuit batching | `batching.py` |
| Kernel autotuning | Hardware-aware transpilation | `autotuning.py` |

All passes are composed through a `CostModel` that estimates per-gate error, decoherence, and readout fidelity, enabling cross-pass optimization.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

For development (includes pytest, ruff, jupyter):

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qc_compiler import QCompiler, OptimizerConfig

qc = QuantumCircuit(4)
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)
qc.cx(2, 3)

backend = FakeBrisbane()

compiler = QCompiler(backend=backend)
config = OptimizerConfig(
    fusion=True,
    scheduling="coherence_aware",
    mitigation="adaptive",
    cutting=True,
    autotune=True,
)
result = compiler.optimize(qc, config=config)

print(f"Fidelity: {result.fidelity_before:.4f} -> {result.fidelity_after:.4f}")
print(f"Passes applied: {result.passes_applied}")
```

## Modules

### CostModel (`cost_model.py`)

Unified error estimation using device calibration data. Provides `DeviceCharacterization`, `CircuitMetrics`, and `ErrorBreakdown` dataclasses.

```python
from qc_compiler import CostModel

model = CostModel(backend=backend)
breakdown = model.estimate_fidelity(circuit)
print(breakdown)
```

### Gate Fusion (`fusion.py`)

Fuses chains of single-qubit gates into fewer basis gates, reducing circuit depth and accumulated error.

```python
from qc_compiler import GateFusion

fusion = GateFusion(cost_model=model)
result = fusion.optimize(circuit)
gate_reduction = 1 - result.total_gates_after / max(result.total_gates_before, 1)
print(f"Gate reduction: {gate_reduction:.1%}")
```

### Circuit Cutting (`cutting.py`)

Partitions large circuits into smaller subcircuits that fit within device qubit limits, using cost-benefit analysis to decide where to cut.

```python
from qc_compiler import CircuitCutter

cutter = CircuitCutter(cost_model=model, max_qubits=5)
result = cutter.analyze(circuit)
print(f"Subcircuits: {len(result.subcircuits)}")
```

### Adaptive Error Mitigation (`mitigation.py`)

Implements ZNE (Richardson extrapolation), PEC, and CDR with adaptive shot allocation based on qubit sensitivity.

```python
from qc_compiler import AdaptiveErrorMitigation

mitigation = AdaptiveErrorMitigation(cost_model=model)
plan = mitigation.create_plan(circuit, method="zne")
print(f"Total shots: {plan.total_shots}")
```

### Coherence-Aware Scheduling (`scheduling.py`)

Reorders gates to minimize idle time on qubits with short T1/T2 coherence times. Supports ASAP, ALAP, and coherence-aware scheduling.

```python
from qc_compiler import CoherenceAwareScheduler

scheduler = CoherenceAwareScheduler(cost_model=model)
result = scheduler.schedule(circuit, method="coherence_aware")
fidelity_improvement = result.estimated_fidelity_optimized - result.estimated_fidelity_asap
print(f"Fidelity improvement: {fidelity_improvement:.4f}")
```

### Circuit Batching (`batching.py`)

Groups independent circuits that share measurement bases into combined execution batches.

```python
from qc_compiler import CircuitBatcher

batcher = CircuitBatcher(cost_model=model)
plan = batcher.create_batch_plan(circuits)
print(f"Batches: {plan.num_batches}")
```

### AutoTuner (`autotuning.py`)

Searches over 216 transpilation configurations (routing, layout, optimization level, scheduling, fusion) using the cost model for fast estimation, with JSON caching.

```python
from qc_compiler import AutoTuner

tuner = AutoTuner(cost_model=model, backend=backend)
result = tuner.search(circuit, circuit_family="ghz")
print(f"Best config: {result.best_config}")
```

### QCompiler Pipeline (`transpiler.py`)

Composes all six passes into a single optimization pipeline with configurable enable/disable flags.

```python
from qc_compiler import QCompiler, OptimizerConfig

compiler = QCompiler(backend=backend)
config = OptimizerConfig(fusion=True, cutting=True)
result = compiler.optimize(circuit, config=config)
```

## Project Structure

```
src/qc_compiler/
  __init__.py           # Public API and __all__
  cost_model.py         # Unified error cost model
  fusion.py             # Gate fusion
  cutting.py            # Circuit cutting
  mitigation.py         # Adaptive error mitigation
  scheduling.py         # Decoherence budget optimization
  batching.py           # Circuit batching
  autotuning.py         # Hardware-aware autotuning
  transpiler.py         # QCompiler pipeline
  utils.py              # Shared utilities
tests/                  # 316 tests
notebooks/              # Validation notebooks (01-08)
docs/
  notes/                # Research notes and paper outline
  paper-proposal.md     # Paper proposal
```

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## Validation Notebooks

| Notebook | Module |
|---|---|
| `01-cost-model-validation.ipynb` | CostModel |
| `02-gate-fusion-validation.ipynb` | GateFusion |
| `03-scheduling-validation.ipynb` | CoherenceAwareScheduler |
| `04-circuit-cutting-validation.ipynb` | CircuitCutter |
| `05-mitigation-validation.ipynb` | AdaptiveErrorMitigation |
| `06-batching-validation.ipynb` | CircuitBatcher |
| `07-autotuning-validation.ipynb` | AutoTuner |
| `08-transpiler-pipeline-validation.ipynb` | QCompiler |

## Research

This framework is the basis for the paper **"Hardware-Aware Quantum Circuit Optimization: Bridging Classical Compilation Techniques to NISQ Devices"**.

- Paper outline: `docs/notes/06-paper-outline.md`
- Paper proposal: `docs/paper-proposal.md`
- Target venue: IEEE TQE / Quantum
- Target submission: January 2027

## Tools & Frameworks

- [Qiskit](https://qiskit.org/) - IBM's open-source quantum computing SDK
- [Cirq](https://quantumai.google/cirq) - Google's quantum computing library
- [PennyLane](https://pennylane.ai/) - Quantum machine learning framework

## License

MIT License - see the [LICENSE](LICENSE) file for details.
