# Quantum Computing Research

A research project exploring quantum computing fundamentals, algorithms, and applications.

## Current Paper

**"Hardware-Aware Quantum Circuit Optimization: Bridging Classical Compilation Techniques to NISQ Devices"**

We draw a systematic analogy between classical GPU compilation for deep learning workloads and quantum circuit compilation for NISQ devices. Six direct mappings are formalized, adapted, and benchmarked on IBM Quantum hardware:

| Classical (GPU) | Quantum (NISQ) |
|---|---|
| Kernel fusion | Gate fusion |
| Model parallelism | Circuit cutting |
| Mixed-precision training | Error mitigation (ZNE) |
| Memory-bandwidth optimization | Decoherence budgeting |
| Batched inference | Circuit batching |
| Kernel autotuning | Hardware-aware transpilation |

- **Paper outline:** `docs/notes/06-paper-outline.md`
- **Project timeline:** `docs/notes/07-project-timeline.md`
- **Target venue:** IEEE TQE / Quantum
- **Target submission:** February 2027

## Project Structure

```
quantum-computing/
├── docs/
│   ├── notes/
│   │   ├── 01-foundations.md           # Qubits, superposition, entanglement
│   │   ├── 02-gates-and-circuits.md    # Gates, circuits, NISQ constraints
│   │   ├── 03-quantum-algorithms.md     # Grover, Shor, VQE, QAOA
│   │   ├── 04-quantum-error-correction.md # Stabilizer codes, surface code
│   │   ├── 05-quantum-machine-learning.md # VQC, QNN, barren plateaus
│   │   ├── 06-paper-outline.md         # Paper outline and methodology
│   │   └── 07-project-timeline.md       # 6-month timeline and milestones
│   └── papers/                          # Reference papers and summaries
├── notebooks/              # Jupyter notebooks for experiments and demos
├── src/
│   ├── algorithms/         # Quantum algorithm implementations
│   ├── circuits/           # Quantum circuit constructions
│   ├── simulators/          # Simulation utilities
│   └── utils/              # Helper functions and utilities
├── tests/                  # Test suite
├── results/                # Experiment results and outputs
└── benchmarks/             # Performance benchmarks
```

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running Notebooks

```bash
jupyter notebook notebooks/
```

### Running Tests

```bash
pytest tests/
```

## Research Notes

| # | Topic | Key Focus |
|---|---|---|
| 01 | Foundations | Qubits, superposition, entanglement, no-cloning, Bloch sphere |
| 02 | Gates & Circuits | Single/two-qubit gates, universality, NISQ constraints |
| 03 | Algorithms | Deutsch-Jozsa, Grover, Shor, VQE, QAOA, QPE |
| 04 | Error Correction | Stabilizer codes, surface code, fault tolerance |
| 05 | Quantum ML | Quantum kernels, VQC, QNN, barren plateaus |
| 06 | Paper Outline | Full paper structure, methodology, experiments |
| 07 | Timeline | 6-month plan with milestones and risk mitigation |

## Tools & Frameworks

- [Qiskit](https://qiskit.org/) — IBM's open-source quantum computing SDK
- [Cirq](https://quantumai.google/cirq) — Google's quantum computing library
- [PennyLane](https://pennylane.ai/) — Quantum machine learning framework

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.