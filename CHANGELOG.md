# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-05

### Added

- **CostModel**: Unified error estimation with `DeviceCharacterization`, `CircuitMetrics`, and `ErrorBreakdown` dataclasses. Supports backend calibration data from IBM Quantum devices.
- **GateFusion**: Chain fusion and cost-guided mode. Decomposes fused single-qubit chains into ZSX basis gates. Returns `FusionResult` with gate/depth reduction metrics.
- **CoherenceAwareScheduler**: ASAP, ALAP, and coherence-aware scheduling. Prioritizes gate execution on qubits with shorter T1/T2 times. Returns `ScheduleResult` with idle time metrics.
- **CircuitCutter**: Cost-benefit analysis for gate cutting, Union-Find based qubit partitioning, and automatic subcircuit reconstruction. Returns `CuttingResult` with subcircuits and error metrics.
- **AdaptiveErrorMitigation**: ZNE (Richardson extrapolation), PEC, and CDR methods with adaptive shot allocation based on qubit sensitivity. Returns `MitigationPlan` and `MitigationResult`.
- **CircuitBatcher**: Measurement-based, structural, and unitary-core grouping strategies for batching independent circuits. Returns `BatchPlan` with estimated speedup.
- **AutoTuner**: 216-configuration search space across routing, layout, optimization level, scheduling, and fusion. Cost-model-based estimation with JSON caching. Returns `TranspileConfig` and `AutotuneResult`.
- **QCompiler**: Full optimization pipeline composing all six passes with `OptimizerConfig` for per-pass enable/disable control. Returns `QCompilerResult` with fidelity metrics and applied passes.
- 234 unit tests covering all modules.
- 8 validation notebooks (01-08) for interactive exploration.
- CI workflow with ruff lint, pytest matrix (3.10-3.13), and coverage reporting.
- PyPI publish workflow on release.