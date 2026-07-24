# Experiment Results

This directory contains benchmark results for the qc-compiler paper.

## Directory Structure

| Directory | Contents |
|---|---|
| `baselines/` | Baseline transpilation results (Qiskit optimization levels 0-3) |
| `gate_fusion/` | Gate fusion optimization results |
| `circuit_cutting/` | Circuit cutting cost-benefit analysis results |
| `error_mitigation/` | Adaptive error mitigation results |
| `decoherence_scheduling/` | Coherence-aware scheduling results |
| `circuit_batching/` | Circuit batching throughput results |
| `autotuning/` | Hardware-aware autotuning configuration search results |
| `end_to_end/` | Combined optimization end-to-end evaluation results |

## Reproducing Results

1. Install dependencies: `pip install -r requirements.txt`
2. Install qc-compiler: `pip install -e .`
3. Run benchmarks: See `benchmarks/` directory for scripts
4. Results are generated as JSON files (gitignored due to size)

## Hardware

All experiments target IBM Quantum devices:
- ibm_brisbane (127 qubits)
- ibm_sherbrooke (127 qubits)
- ibm_osaka (127 qubits)
- Aer simulator (local, noiseless baseline)