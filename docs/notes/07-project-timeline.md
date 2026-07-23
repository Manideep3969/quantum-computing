# Project Timeline: Hardware-Aware Quantum Circuit Optimization

**Paper Target:** IEEE TQE or Quantum (quantum-journal.org)
**Start Date:** July 2026
**Target Submission:** January 2027 (6 months)
**Backup Submission:** March 2027 (8 months)

---

## Phase 1: Foundation (Weeks 1–4, July 2026)

### Week 1–2: Literature Deep Dive
- [ ] Read 15–20 core papers in quantum circuit compilation and optimization
  - Murali et al. (2019) — noise-adaptive compiler
  - t|ket⟩ papers — routing and synthesis
  - Circuit cutting papers (Peng 2020, Tang 2024)
  - ZNE and PEC papers (Temme 2017, Kandala 2019)
  - FlashAttention, Triton, AutoTVM papers (classical analogs)
- [ ] Read 5–10 GPU compiler papers for formal analogy grounding
  - CUDA compilation pipeline documentation
  - TensorRT optimization passes
  - Triton language and autotuning
- [ ] Create annotated bibliography in `docs/papers/`

### Week 3–4: Environment Setup and Baseline Benchmarks
- [ ] Set up Qiskit 1.x + IBM Quantum account (free tier)
- [ ] Set up PennyLane for VQE experiments
- [ ] Implement baseline transpilation pipeline for all benchmark circuits
  - QFT (4, 8, 16, 32 qubits)
  - QAOA Max-Cut (4, 8, 16, 32 qubits)
  - VQE (H₂, LiH, BeH₂)
  - GHZ state preparation (4, 8, 16, 32 qubits)
  - Random circuits (4–32 qubits)
- [ ] Run baseline benchmarks on ibm_brisbane, ibm_sherbrooke, ibm_osaka
- [ ] Store all baseline data in `results/baselines/`
- [ ] Create reproducible benchmark scripts in `benchmarks/`

**Deliverable:** Baseline benchmark dataset + annotated bibliography

---

## Phase 2: Core Algorithms (Weeks 5–10, August–September 2026)

### Week 5–6: Gate Fusion (Optimization 1)
- [ ] Implement gate fusion algorithm (Section 5 of paper outline)
- [ ] Integrate with Qiskit transpiler as custom pass
- [ ] Run Experiment 1 benchmarks
- [ ] Analyze depth reduction and fidelity improvement
- [ ] Write up preliminary results in `results/gate_fusion/`

### Week 7–8: Circuit Cutting Cost Model (Optimization 2)
- [ ] Implement cost-benefit decision framework for circuit cutting
- [ ] Use Qiskit Circuit Knitting Toolbox
- [ ] Run Experiment 2 benchmarks (simulator for >127 qubit circuits)
- [ ] Validate decision framework predictions against measured results
- [ ] Write up in `results/circuit_cutting/`

### Week 9–10: Adaptive Error Mitigation (Optimization 3)
- [ ] Implement gradient-aware shot allocation for ZNE
- [ ] Compare against uniform ZNE on VQE and QAOA circuits
- [ ] Run Experiment 3 benchmarks
- [ ] Analyze shots-to-fidelity efficiency curves
- [ ] Write up in `results/error_mitigation/`

**Deliverable:** Three working optimization modules + preliminary results

---

## Phase 3: Advanced Optimizations (Weeks 11–16, October–November 2026)

### Week 11–12: Decoherence Budget Optimization (Optimization 4)
- [ ] Implement coherence-aware scheduling algorithm
- [ ] Fetch real-time calibration data from IBM Quantum
- [ ] Run Experiment 4 benchmarks
- [ ] Compare ASAP, ALAP, and coherence-aware schedules
- [ ] Write up in `results/decoherence_scheduling/`

### Week 13–14: Circuit Batching (Optimization 5)
- [ ] Implement measurement-based batching for VQE observables
- [ ] Implement structural batching for QAOA parameter sweeps
- [ ] Run Experiment 5 benchmarks
- [ ] Measure throughput improvement (wall-clock time)
- [ ] Write up in `results/circuit_batching/`

### Week 15–16: Hardware-Aware Autotuning (Optimization 6)
- [ ] Implement autotuning search over transpiler configurations
- [ ] Build configuration cache per circuit family
- [ ] Run Experiment 6 (216 configurations per circuit)
- [ ] Compare autotuned vs. default Qiskit transpiler
- [ ] Write up in `results/autotuning/`

**Deliverable:** All six optimization modules + experimental data

---

## Phase 4: Integration and End-to-End Evaluation (Weeks 17–20, December 2026)

### Week 17–18: Framework Integration
- [ ] Create `qc-compiler` package structure in `src/`
- [ ] Integrate all six optimizations into unified API
- [ ] Write documentation and usage examples
- [ ] Package as pip-installable module
- [ ] Create Jupyter notebook demos in `notebooks/`

### Week 19–20: End-to-End Evaluation
- [ ] Run Experiment 7: combined optimization on VQE (BeH₂) and QAOA (16-node Max-Cut)
- [ ] Compare against baseline: fidelity, depth, shots, wall-clock time
- [ ] Statistical analysis: error bars, confidence intervals, hypothesis tests
- [ ] Create all figures and tables for the paper
- [ ] Deposit data on Zenodo

**Deliverable:** Integrated `qc-compiler` framework + final experimental data

---

## Phase 5: Writing and Submission (Weeks 21–26, January–March 2027)

### Week 21–23: First Draft
- [ ] Write Sections 1–4 (Introduction, Background, Formal Analogy)
- [ ] Write Sections 5–10 (Six Optimization Techniques)
- [ ] Write Section 11 (Experimental Evaluation)
- [ ] Create all figures:
  - Figure 1: Classical-quantum analogy overview (main figure)
  - Figure 2: Gate fusion before/after circuit diagrams
  - Figure 3: Circuit cutting cost model visualization
  - Figure 4: Adaptive ZNE vs. uniform ZNE fidelity curves
  - Figure 5: Decoherence budget comparison (ASAP vs. ALAP vs. coherence-aware)
  - Figure 6: Batching throughput comparison
  - Figure 7: Autotuning configuration search results
  - Figure 8: End-to-end combined optimization results

### Week 24–25: Revision and Peer Review
- [ ] Internal revision: check all claims, verify all numbers
- [ ] Send to 2–3 colleagues for feedback (if possible)
- [ ] Revise based on feedback
- [ ] Format for target journal (IEEE TQE or Quantum)
- [ ] Final proofread

### Week 26: Submission
- [ ] Submit to **IEEE TQE** (primary) or **Quantum** (backup)
- [ ] Post preprint on arXiv (quant-ph)
- [ ] Announce on social media / Qiskit community

**Deliverable:** Submitted paper + arXiv preprint

---

## Key Milestones

| Milestone | Target Date | Status |
|---|---|---|
| Literature review complete | August 1, 2026 | ⬜ |
| Baseline benchmarks collected | August 15, 2026 | ⬜ |
| Gate fusion results | September 1, 2026 | ⬜ |
| Circuit cutting results | September 15, 2026 | ⬜ |
| Adaptive ZNE results | September 30, 2026 | ⬜ |
| Decoherence scheduling results | October 15, 2026 | ⬜ |
| Circuit batching results | October 31, 2026 | ⬜ |
| Autotuning results | November 15, 2026 | ⬜ |
| `qc-compiler` v0.1 release | December 15, 2026 | ⬜ |
| End-to-end evaluation complete | December 31, 2026 | ⬜ |
| First draft complete | January 15, 2027 | ⬜ |
| Revisions complete | January 31, 2027 | ⬜ |
| **Paper submitted** | **February 15, 2027** | ⬜ |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| IBM Quantum free tier queue times too long | Delays experiments by weeks | Use local Aer simulator for development; batch hardware runs; use multiple IBM devices |
| Optimization improvements are marginal | Weak paper contribution | Focus on techniques that show >10% improvement; if all are marginal, pivot to "why classical analogies fail" paper |
| IBM Quantum device calibration changes mid-experiment | Inconsistent results | Record calibration data with each run; run all experiments for one technique in a short window (1–2 days) |
| Qiskit API breaking changes | Code breaks | Pin Qiskit version; use stable APIs only |
| Reviewer skepticism about analogy novelty | Paper rejected | Emphasize empirical results (not just analogy); provide mathematical formalization; open-source code |

---

## Weekly Time Commitment

Assuming 15–20 hours/week (part-time alongside platform engineering work):

- **Phase 1:** 15 hrs/week × 4 weeks = 60 hours
- **Phase 2:** 20 hrs/week × 6 weeks = 120 hours
- **Phase 3:** 20 hrs/week × 6 weeks = 120 hours
- **Phase 4:** 15 hrs/week × 4 weeks = 60 hours
- **Phase 5:** 20 hrs/week × 6 weeks = 120 hours

**Total estimated effort:** ~480 hours over 6 months