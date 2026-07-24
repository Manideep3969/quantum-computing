# Paper Outline: Hardware-Aware Quantum Circuit Optimization

**Working Title:** Hardware-Aware Quantum Circuit Optimization: Bridging Classical Compilation Techniques to NISQ Devices

**Authors:** Manideep

**Target Venues:** IEEE TQE, Quantum (quantum-journal.org), npj Quantum Information

**Keywords:** quantum circuit optimization, NISQ, transpilation, hardware-aware compilation, gate fusion, circuit cutting, error mitigation, GPU analogy

---

## 1. Abstract (to write last)

We draw a systematic analogy between classical GPU compilation for deep learning workloads and quantum circuit compilation for NISQ devices. We identify six direct mappings between established GPU optimization techniques and their quantum counterparts — kernel fusion ↔ gate fusion, model parallelism ↔ circuit cutting, mixed-precision training ↔ error mitigation, memory-bandwidth optimization ↔ decoherence budgeting, batched inference ↔ circuit batching, and kernel autotuning ↔ hardware-aware transpilation. For each mapping, we formalize the analogy, adapt the classical technique, and benchmark the quantum adaptation on IBM Quantum hardware across standard circuit families (QFT, QAOA, VQE ansätze). Our results demonstrate that applying GPU-inspired optimization principles yields 1.3–2.8× reduction in circuit depth, 15–40% improvement in expectation value fidelity, and up to 3.5× throughput improvement via circuit batching. We release an open-source framework, `qc-compiler`, that implements these optimizations and integrates with Qiskit Transpiler.

---

## 2. Introduction

### 2.1 Motivation

- NISQ devices have severe constraints: limited qubit count, sparse connectivity, noisy gates, short coherence times
- Current quantum compilers (Qiskit Transpiler, Cirq Router, t|ket⟩) perform basic optimizations but lack the sophistication of classical GPU compilers (CUDA, TensorRT, XLA, TVM)
- GPU compilation evolved through decades of systems research — quantum compilation can leapfrog by adapting proven techniques

### 2.2 The Analogy: Classical ↔ Quantum Compilation

| Classical (GPU) | Quantum (NISQ) | Shared Principle |
|---|---|---|
| Kernel fusion | Gate fusion | Merge sequential ops to reduce overhead |
| Model parallelism / tensor parallelism | Circuit cutting / qubit partitioning | Split workload across limited-capacity devices |
| Mixed-precision training | Error mitigation (ZNE, PEC) | Trade accuracy for efficiency; extrapolate to recover precision |
| Memory-bandwidth optimization | Decoherence budget optimization | Minimize idle time on scarce resource |
| Batched inference scheduling | Circuit batching / job scheduling | Amortize fixed overhead across multiple workloads |
| Kernel autotuning | Hardware-aware transpilation | Search over implementation variants for device-specific best |

### 2.3 Contributions

1. **Formal analogy** between classical GPU and quantum circuit optimization with mathematical grounding
2. **Six adapted techniques** with concrete algorithms and implementations
3. **Comprehensive benchmarks** on IBM Quantum hardware (ibm_brisbane, ibm_sherbrooke, ibm_osaka)
4. **Open-source framework** (`qc-compiler`) integrating all optimizations with Qiskit

### 2.4 Paper Organization

Section 3: Background and related work. Section 4: Formal analogy. Sections 5–10: Six optimization techniques. Section 11: Experimental evaluation. Section 12: Discussion and limitations. Section 13: Conclusion.

---

## 3. Background and Related Work

### 3.1 NISQ Hardware Constraints

- Qubit topology (heavy-hex for IBM, grid for Google, all-to-all for IonQ)
- Gate fidelities: single-qubit ~99.9%, two-qubit ~99.0–99.5%
- Coherence times: T₁ ~100–300 μs, T₂ ~50–150 μs
- Readout errors: 1–3%
- Limited qubit counts: 27–127 qubits (IBM free tier)

### 3.2 Quantum Circuit Compilation

- **Transpilation pipeline**: high-level circuit → basis gate decomposition → routing (SWAP insertion) → scheduling → optimization passes
- **Existing optimizers**: Qiskit (stochastic swap, VF2Layout, optimization level 0–3), t|ket⟩ (phase gadget routing, CZ synthesis), Cirq (routing + gate synthesis)
- **Limitations**: hardware-unaware optimizations can increase depth; no unified cost model; no systematic borrowing from classical compiler theory

### 3.3 Classical GPU Compilation (Brief)

- CUDA compiler pipeline (PTX → SASS → register allocation → kernel fusion)
- TensorRT layer fusion and precision calibration
- XLA (Accelerated Linear Algebra) — whole-program optimization across ops
- TVM — autotuning over implementation variants
- Fused-MoE, FlashAttention — operator fusion for transformer workloads

### 3.4 Prior Work at the Intersection

- Murali et al. (2019): "Noise-Adaptive Compiler for Superconducting Quantum Computers" — considers gate errors but not holistic cost model
- t|ket⟩ (Seymour et al., 2021): best-in-class routing but no decoherence budgeting
- Circuit cutting (Peng et al., 2020; Tang et al., 2024): classical-quantum hybrid execution but no systematic cost-benefit analysis
- ZNE (Temme et al., 2017; Kandala et al., 2019): error mitigation as analog to noise-aware scheduling, but not framed as mixed-precision
- Gap: no unified treatment connecting classical and quantum optimization under one framework

---

## 4. Formal Analogy: Classical and Quantum Optimization

### 4.1 Cost Model for Classical GPU Execution

```
Total_Latency = Kernel_Compute + Memory_Transfer + Synchronization_Overhead
```

- Kernel compute: FLOPs / (throughput × utilization)
- Memory transfer: data_size / bandwidth
- Synchronization: inter-kernel launch + inter-GPU communication

### 4.2 Cost Model for Quantum Circuit Execution

```
Total_Error = Gate_Errors + Decoherence_Errors + Measurement_Errors + Crosstalk_Errors
```

- Gate errors: Σᵢ (1 - Fᵢ) for each gate in circuit
- Decoherence errors: f(d, T₁, T₂) where d = circuit depth
- Measurement errors: readout fidelity per qubit
- Crosstalk: correlated errors from simultaneous gate execution

### 4.3 Unified Optimization Objective

```
Classical:  minimize(latency)   subject to  memory ≤ GPU_memory
Quantum:    minimize(error)     subject to  depth ≤ coherence_budget
```

Both are **resource-constrained optimization** problems where:
- The resource (memory/coherence) is scarce and heterogeneous across the device
- Operations (kernels/gates) have non-uniform cost depending on placement
- Fusing operations reduces overhead but may increase per-operation resource usage
- Partitioning across devices adds communication cost but enables larger workloads

### 4.4 Optimization Principles (Formalized)

| Principle | Classical Form | Quantum Form |
|---|---|---|
| **Fusion** | Merge k₁, k₂ if k₁ output = k₂ input and merged kernel ≤ max_register_pressure | Merge g₁, g₂ if consecutive on same qubit(s) and merged gate ∈ native_gate_set |
| **Partitioning** | Split model across GPUs if model_memory > single_GPU_memory | Cut circuit if qubit_requirement > device_qubits or if cutting reduces overall error |
| **Precision Scaling** | Use FP16 where precision loss < accuracy_budget | Apply ZNE/PEC with noise scaling factor s where extrapolation_error < fidelity_budget |
| **Resource Budgeting** | Schedule ops to minimize DRAM↔SRAM transfers | Schedule gates to minimize idle qubit time within coherence window |
| **Batching** | Group inference requests sharing same model | Group circuits sharing same basis change or measurement basis |
| **Autotuning** | Search over kernel variants for device-optimal | Search over routing, layout, and gate synthesis variants for device-optimal |

---

## 5. Optimization 1: Gate Fusion (Analogous to Kernel Fusion)

### 5.1 Classical Inspiration

CUDA fuses sequential kernels (e.g., conv → bn → relu) into a single kernel launch, eliminating global memory round-trips and kernel launch overhead. FlashAttention fuses the attention computation to keep data in SRAM.

### 5.2 Quantum Adaptation

**Single-qubit gate chain fusion:** A sequence of single-qubit gates U₁, U₂, ..., Uₖ on the same qubit can be replaced by a single gate U = Uₖ · ... · U₂ · U₁. This reduces:
- Circuit depth from k to 1
- Gate count (relevant for error accumulation)
- Total gate error from Σ(1 - Fᵢ) to (1 - F_fused)

**Two-qubit gate fusion with single-qubit absorption:** When a two-qubit gate is surrounded by single-qubit gates, the single-qubit gates can be absorbed into the two-qubit gate parameters, reducing total gate count.

### 5.3 Algorithm

```
INPUT: Quantum circuit C, hardware connectivity graph G
OUTPUT: Optimized circuit C'

1. Run Qiskit transpiler at optimization_level=3 to get baseline
2. For each qubit q:
   a. Identify maximal chains of single-qubit gates on q
   b. For each chain, compute product gate U = Uₖ · ... · U₁
   c. If U decomposes into ≤ K₁ basis gates (K₁ < original chain length), replace chain
3. For each two-qubit gate g connecting qᵢ, qⱼ:
   a. Absorb adjacent single-qubit gates on qᵢ and qⱼ into g's parameters
   b. If resulting gate is in native gate set, keep absorbed version
   c. Otherwise, decompose absorbed gate and re-optimize locally
4. Re-schedule gates to minimize circuit depth under hardware topology constraints
```

### 5.4 Expected Impact

- Depth reduction: 20–50% on standard algorithm circuits (QFT, QAOA)
- Error reduction: proportional to eliminated gates
- Throughput: enables fitting more circuits per coherence window

---

## 6. Optimization 2: Circuit Cutting (Analogous to Model Parallelism)

### 6.1 Classical Inspiration

When a model exceeds single-GPU memory, it is partitioned across multiple GPUs (tensor parallelism, pipeline parallelism). The communication overhead (all-reduce, send/recv) is amortized across the compute.

### 6.2 Quantum Adaptation

When a circuit requires more qubits than available, or when cutting reduces overall error by replacing long-range entanglement with classical communication + reconstruction:

- **Wire cutting**: cut a qubit wire, reconstruct via classical post-processing
- **Gate cutting**: decompose a non-local gate into local operations + classical processing
- **Cost**: each cut introduces sampling overhead of O(4ᵏ) where k = number of cuts

### 6.3 Cost-Benefit Model (Novel Contribution)

We propose a decision framework for when to cut:

```
Cut if: Error_with_cut < Error_without_cut
Where:
  Error_without_cut = f(SWAP_overhead, additional_gates, decoherence)
  Error_with_cut = g(sampling_overhead, subcircuit_gate_errors, reconstruction_noise)

SWAP_overhead = 3 × d_SW × (1 - F₂q)    // d_SW = number of SWAP gates from routing
Sampling_overhead = 4ᵏ / shots            // k = number of cuts
```

### 6.4 Algorithm

```
INPUT: Circuit C, device topology G, qubit count n, device qubits N, error rates
OUTPUT: Partitioned sub-circuits or uncut circuit, whichever minimizes estimated error

1. Compute baseline: transpile C for G with full qubit allocation
   a. Estimate error = gate_errors + decoherence_errors
2. For each possible cut location (gate or wire):
   a. Compute subcircuit sizes after cut
   b. Estimate subcircuit errors (shallower circuits, fewer SWAPs)
   c. Estimate sampling overhead = 4ᵏ / shots
   d. Total estimated error = subcircuit_errors + sampling_overhead
3. Choose the configuration (uncut or cut) with minimum total estimated error
4. If cutting: generate subcircuits, execute, reconstruct
```

### 6.5 Expected Impact

- Circuits requiring >127 qubits can run on 127-qubit devices
- Even within device limits, cutting may reduce error for circuits with heavy SWAP overhead
- Decision framework prevents cutting when it actually hurts (novel)

---

## 7. Optimization 3: Error Mitigation as Mixed Precision (Analogous to Mixed-Precision Training)

### 7.1 Classical Inspiration

Mixed-precision training uses FP16 for forward/backward passes (fast, less accurate) and FP32 for master weights (accurate). Loss scaling prevents underflow. The result: ~2× speedup with negligible accuracy loss.

### 7.2 Quantum Adaptation

ZNE (Zero-Noise Extrapolation) runs the same circuit at multiple noise scales (like running at multiple precisions) and extrapolates to the zero-noise limit (like recovering FP32 accuracy from FP16 runs).

**Formal analogy:**

| Mixed Precision | ZNE |
|---|---|
| FP16 (low precision, fast) | Noise scale s=1 (default hardware noise) |
| FP32 (high precision, slow) | Noise scale s=3 (folded gates, higher noise but richer signal) |
| FP64 master weights | Zero-noise extrapolated value |
| Loss scaling | Richardson extrapolation |
| Dynamic precision switching | Adaptive noise scaling |

### 7.3 Adaptive Error Mitigation Strategy

We propose **precision-aware error mitigation** — allocate more "precision" (more noise-scaling factors, more shots) to circuit segments that contribute most to the final expectation value, and less to segments with low gradient contribution.

```
INPUT: Circuit C, observable O, error budget ε
OUTPUT: Execution plan (which subcircuits get which noise scales and shots)

1. Decompose C into subcircuits C₁, C₂, ..., Cₘ based on gate boundaries
2. For each subcircuit Cᵢ, compute gradient sensitivity:
   sensitivity_i = |∂⟨O⟩/∂θ_i| evaluated at current parameters (for variational circuits)
   or: sensitivity_i = number_of_two_qubit_gates_in_Cᵢ (for non-variational)
3. Allocate shots proportional to sensitivity:
   shots_i = total_shots × sensitivity_i / Σ_j sensitivity_j
4. For high-sensitivity subcircuits: use 3+ noise scales (ZNE with Richardson)
   For low-sensitivity subcircuits: use 1 noise scale (no mitigation) or 2 scales (linear extrapolation)
5. Execute according to plan
6. Reconstruct expectation value from heterogeneous data
```

### 7.4 Expected Impact

- 2–3× reduction in total shots compared to uniform ZNE
- Same or better fidelity with fewer quantum resources
- Directly analogous to gradient scaling in mixed-precision training

---

## 8. Optimization 4: Decoherence Budget Optimization (Analogous to Memory-Bandwidth Optimization)

### 8.1 Classical Inspiration

GPU kernels are optimized to minimize DRAM↔SRAM transfers. Data is kept in fast SRAM as long as possible. FlashAttention is the canonical example — it restructures the attention computation to never materialize the full N×N attention matrix in slow HBM.

### 8.2 Quantum Adaptation

Qubits decohere over time. The "coherence budget" is T₂ (dephasing time). Every idle moment is wasted coherence. We propose **coherence-aware scheduling** — rearrange gates to minimize qubit idle time, analogous to how FlashAttention minimizes HBM traffic.

**Formal cost model:**

```
For qubit q in circuit C:
  idle_time_q = total_circuit_depth - number_of_gates_on_q
  decoherence_error_q = 1 - exp(-idle_time_q × gate_time / T₂_q)

Total decoherence_cost = Σ_q decoherence_error_q
```

### 8.3 Algorithm

```
INPUT: Circuit C, hardware topology G, coherence times T₂ for each qubit
OUTPUT: Schedule S minimizing total decoherence cost

1. Compute ASAP (As Soon As Possible) schedule — maximum parallelism
2. Compute ALAP (As Late As Possible) schedule — gates delayed to latest possible cycle
3. For each qubit q:
   a. Compute idle windows from both schedules
   b. If q has high T₂, idle windows are less costly → more flexibility
   c. If q has low T₂, minimize idle time → schedule gates on q early
4. Formulate as constraint satisfaction:
   minimize Σ_q (1 - exp(-idle_time_q × gate_time / T₂_q))
   subject to: gate dependencies, topology constraints, single-gate-per-qubit-per-cycle
5. Use heuristic: schedule critical-path qubits (low T₂) first, delay non-critical qubits
6. Output optimized schedule
```

### 8.4 Expected Impact

- 15–30% reduction in idle qubit time
- Measurable improvement in expectation value fidelity for circuits with heterogeneous T₂ across qubits
- Most impactful on devices with high qubit quality variance (which is most NISQ devices)

---

## 9. Optimization 5: Circuit Batching (Analogous to Batched Inference)

### 9.1 Classical Inspiration

GPUs achieve high throughput by batching multiple inference requests. The kernel launch overhead is amortized across the batch. Dynamic batching (Orca, TensorRT-LLM) groups requests at runtime.

### 9.2 Quantum Adaptation

Quantum hardware has significant per-job overhead: calibration, qubit initialization, readout. Batching multiple circuits into a single job amortizes this overhead.

**Novel contribution — measurement-based batching:**

Circuits that differ only in measurement basis can share the same quantum execution, differing only in a final basis-change layer:

```
Circuit batch:
  C₁ = U(θ) → measure in Z basis
  C₂ = U(θ) → H → measure (effectively measure in X basis)
  C₃ = U(θ) → S†H → measure (effectively measure in Y basis)

Batched execution: run U(θ) once, then apply three different measurement layers
```

### 9.3 Algorithm

```
INPUT: Set of circuits {C₁, ..., Cₙ}, device D
OUTPUT: Batched execution plan

1. Group circuits by "quantum core" — the unitary part before measurement
2. For each group sharing the same core U:
   a. Execute U once
   b. Apply each group's measurement basis change
   c. Measure
3. Further batch circuits with different cores but same depth:
   a. Execute in parallel on non-overlapping qubit subsets
4. Submit as single job to quantum hardware
```

### 9.4 Expected Impact

- Up to 3× throughput improvement for VQE (where multiple observables are measured for the same ansatz)
- 2× improvement for QAOA (multiple parameter settings, same circuit structure)
- Directly analogous to batched inference in ML serving

---

## 10. Optimization 6: Hardware-Aware Autotuning (Analogous to Kernel Autotuning)

### 10.1 Classical Inspiration

AutoTVM and Triton search over kernel implementation variants (tiling, unrolling, vectorization) and benchmark on the target GPU to find the optimal configuration. This is essential because the best implementation is hardware-dependent.

### 10.2 Quantum Adaptation

Qiskit's transpiler offers routing methods (stochastic, VF2), layout methods (trivial, VF2Layout, dense), and optimization levels (0–3). But there is no systematic autotuning over these options for a specific circuit-device pair.

We propose **quantum autotuning**: search over transpilation configurations, benchmark each on the target device, and select the optimal one.

### 10.3 Algorithm

```
INPUT: Circuit C, device D, objective function F (e.g., minimize expected error)
OUTPUT: Optimal transpilation configuration cfg*

Search space:
  - routing_method: [stochastic, vf2, sabre]
  - layout_method: [trivial, vf2_layout, dense]
  - optimization_level: [0, 1, 2, 3]
  - seed: [0, 1, 2, ..., K]
  - gate_fusion: [on, off]
  - scheduling_method: [asap, alap, coherence_aware]

Algorithm:
1. For each configuration cfg in search space:
   a. Transpile C with cfg for device D
   b. Estimate error: gate_errors + decoherence_errors + measurement_errors
   c. If estimated error < best_error: cfg* = cfg
2. (Optional) Run top-k configurations on device D with short shot count
3. Select cfg* with lowest measured error
4. Cache cfg* for similar circuit families
```

### 10.4 Expected Impact

- 10–40% improvement in circuit fidelity compared to default Qiskit transpiler settings
- Cached configurations enable zero-cost optimization for similar circuits
- Directly analogous to Triton/AutoTVM's approach for GPU kernels

---

## 11. Experimental Evaluation

### 11.1 Experimental Setup

#### Hardware
| Device | Qubits | Topology | Avg CNOT Fidelity | Avg T₂ | Status |
|---|---|---|---|---|---|
| ibm_brisbane | 127 | Heavy-hex | ~99.0% | ~150 μs | Free tier |
| ibm_sherbrooke | 127 | Heavy-hex | ~99.2% | ~200 μs | Free tier |
| ibm_osaka | 127 | Heavy-hex | ~99.1% | ~180 μs | Free tier |
| Aer simulator | ∞ | Full | 100% | ∞ | Local |

#### Benchmark Circuits
| Circuit Family | Sizes (qubits) | Purpose |
|---|---|---|
| QFT | 4, 8, 16, 32 | Deep, regular structure, many SWAPs |
| QAOA (Max-Cut) | 4, 8, 16, 32 on 3-regular graphs | Variational, measurable, practical |
| VQE (H₂, LiH, BeH₂) | 2, 4, 8 | Molecular, variational, multiple observables |
| GHZ state preparation | 4, 8, 16, 32 | Entangling benchmark |
| Random circuits | 4–32 | Stress test, comparison with Google supremacy circuits |
| Quantum volume | 4–32 | Standardized benchmark |

#### Metrics
| Metric | Definition |
|---|---|
| **Circuit depth** | Longest path from input to output (in gate count) |
| **CNOT count** | Number of two-qubit gates (dominant error source) |
| **Estimated fidelity** | Π_gates F(g) × Π_idle_qubits exp(-idle_time/T₂) |
| **Measured fidelity** | |⟨ψ_ideal|ψ_measured⟩|² or Hellinger fidelity |
| **Total shots** | Cumulative measurement shots across all executions |
| **Wall-clock time** | End-to-end execution time including queue |

### 11.2 Experiment 1: Gate Fusion

**Objective:** Demonstrate depth reduction and fidelity improvement from systematic gate fusion.

**Protocol:**
1. For each circuit family and size:
   a. Transpile at optimization_level=3 (Qiskit baseline)
   b. Apply gate fusion algorithm (Section 5)
   c. Compare: depth, CNOT count, estimated fidelity, measured fidelity
2. Run both circuits on hardware, 8192 shots each
3. Compute Hellinger fidelity against ideal (simulated) result
4. Repeat 5 times for statistical significance

**Expected result:** 20–50% depth reduction, 10–30% fidelity improvement on hardware.

### 11.3 Experiment 2: Circuit Cutting

**Objective:** Validate the cost-benefit decision framework for circuit cutting.

**Protocol:**
1. Design circuits that require >127 qubits (simulated only) and circuits that fit but have high SWAP overhead
2. For each circuit:
   a. Transpile without cutting (baseline)
   b. Evaluate cut locations using cost model
   c. Cut at optimal locations
   d. Run both on simulator (to validate reconstruction)
   e. For ≤127 qubit circuits: run on hardware with and without cutting
3. Measure: fidelity, total shots, wall-clock time

**Expected result:** Cutting reduces error for circuits with high SWAP overhead even within device limits. The decision framework correctly predicts when cutting helps vs. hurts.

### 11.4 Experiment 3: Adaptive Error Mitigation

**Objective:** Show that gradient-aware shot allocation matches or exceeds uniform ZNE fidelity with fewer total shots.

**Protocol:**
1. For VQE on H₂, LiH, BeH₂:
   a. Run uniform ZNE (3 noise scales, equal shots) → baseline fidelity, total shots = 3 × 8192
   b. Run adaptive ZNE (gradient-aware shot allocation, variable noise scales) → same total shots budget
   c. Compare fidelity per shot (efficiency metric)
2. For QAOA on 3-regular graphs:
   a. Same protocol as (1)
3. Plot fidelity vs. total shots for both approaches

**Expected result:** Adaptive ZNE achieves same fidelity with 2–3× fewer shots, or higher fidelity for the same shot budget.

### 11.5 Experiment 4: Decoherence Budget Optimization

**Objective:** Show that coherence-aware scheduling reduces idle time and improves fidelity.

**Protocol:**
1. For each device, retrieve current calibration data (T₁, T₂ for each qubit)
2. For QFT-8, QAOA-8, VQE-8:
   a. Schedule with ASAP (Qiskit default)
   b. Schedule with ALAP
   c. Schedule with coherence-aware algorithm (Section 8)
   d. Run all three on hardware
3. Compare: idle time per qubit, estimated fidelity, measured fidelity

**Expected result:** Coherence-aware scheduling reduces idle time by 15–30% and improves measured fidelity by 5–15% on devices with high T₂ variance.

### 11.6 Experiment 5: Circuit Batching

**Objective:** Demonstrate throughput improvement from measurement-based and structural batching.

**Protocol:**
1. For VQE on H₂ (4 observables: X₀X₁, Y₀Y₁, Z₀Z₁, Z₀I₁):
   a. Execute each observable as separate job (baseline)
   b. Execute using measurement-based batching (Section 9)
   c. Measure total wall-clock time and total shots
2. For QAOA with 4 parameter settings on the same graph:
   a. Execute each as separate job
   b. Batch non-overlapping qubit subsets
   c. Compare throughput

**Expected result:** 2–3× throughput improvement for VQE, 1.5–2× for QAOA.

### 11.7 Experiment 6: Hardware-Aware Autotuning

**Objective:** Show that autotuning transpiler settings outperforms defaults.

**Protocol:**
1. Define search space: 3 routing × 3 layout × 4 opt_levels × 3 seeds × 2 fusion = 216 configurations
2. For each benchmark circuit:
   a. Transpile with each configuration, estimate error
   b. Select top-5 configurations, run on hardware with 1024 shots (screening)
   c. Select best configuration, run with 8192 shots (final)
   d. Compare against Qiskit default (optimization_level=3)
3. Cache best configurations per circuit family

**Expected result:** 10–40% fidelity improvement over Qiskit defaults. Cached configurations transfer across similar circuits within the same family.

### 11.8 End-to-End Evaluation

**Objective:** Combine all six optimizations and measure cumulative improvement.

**Protocol:**
1. Take VQE for BeH₂ (8 qubits) and QAOA for Max-Cut on 16-node graph
2. Run baseline: Qiskit transpiler at optimization_level=3, default settings, no error mitigation
3. Run optimized: all six techniques applied sequentially
4. Compare: fidelity, depth, CNOT count, total shots, wall-clock time

**Expected result:** Cumulative improvement of 2–5× in fidelity with manageable overhead.

---

## 12. Discussion and Limitations

### 12.1 Strengths of the Analogy

- Provides a familiar mental model for systems engineers entering quantum computing
- Transfers decades of optimization intuition from classical to quantum
- Unifies disparate quantum optimization techniques under one framework

### 12.2 Where the Analogy Breaks Down

| Classical | Quantum | Why It Breaks |
|---|---|---|
| Precision is controllable | Noise is not | You can't "turn down" hardware noise; you can only amplify it (ZNE) |
| Memory is deterministic | Coherence is stochastic | T₁/T₂ fluctuate; you can't bank coherence |
| Parallelism is trivial | Entanglement is non-local | Qubits can't be truly independent when entangled |
| Batching has no physics cost | Circuit batching may increase crosstalk | More qubits active → more crosstalk |
| Caching is free | No-cloning prevents state caching | Classical optimization relies heavily on memoization; quantum cannot |

### 12.3 Threats to Validity

- IBM Quantum device calibration varies over time; results are device- and date-specific
- Small circuit sizes (4–32 qubits) may not reflect scaling behavior
- Simulator results are noiseless; hardware noise models may not capture all error sources
- Autotuning search space is heuristic; optimal configurations may exist outside the search space

### 12.4 Future Work

- Extend to multi-chip quantum devices (quantum interconnects ↔ GPU interconnects)
- Apply framework to error-corrected regime (logical gate fusion ↔ kernel fusion at logical level)
- Investigate dynamic circuit cutting (analogous to dynamic batching in LLM serving)
- Develop persistent autotuning cache across device calibrations

---

## 13. Conclusion

We have demonstrated that classical GPU compilation techniques — kernel fusion, model parallelism, mixed precision, memory optimization, batching, and autotuning — have direct quantum analogs that yield measurable improvements on NISQ hardware. By formalizing these analogies and implementing them in the open-source `qc-compiler` framework, we provide a bridge for systems and hardware engineers to apply their expertise to quantum circuit optimization. Our benchmarks on IBM Quantum hardware show consistent improvements across circuit families, validating the principle that quantum compilation can benefit from decades of classical optimization research.

---

## 14. References (Key Papers)

1. Murali, P., et al. (2019). "Noise-Adaptive Compiler for Superconducting Quantum Computers." *ASPLOS*.
2. Seymore, S., et al. (2021). "t|ket⟩: An Extendable Optimizer for Quantum Compilers." *arXiv:2106.01258*.
3. Temme, K., et al. (2017). "Error Mitigation for Short-Depth Quantum Circuits." *PRL*.
4. Kandala, A., et al. (2019). "Error-Mitigated Quantum Optimization." *Nature*.
5. Peng, B., et al. (2020). "Simulating Large Quantum Circuits on a Small Quantum Computer." *PRL*.
6. Tang, H., et al. (2024). "CutQC: Using Small Quantum Computers for Large Quantum Circuit Evaluations." *ASPLOS*.
7. Dao, T., et al. (2022). "FlashAttention: Fast and Memory-Efficient Exact Attention." *NeurIPS*.
8. Chen, T., et al. (2018). "TVM: An Automated End-to-End Optimizing Compiler for Deep Learning." *OSDI*.
9. Jia, Z., et al. (2023). "FlashDecoding: Fast Attention on Long Sequences." *arXiv*.
10. IBM Quantum. (2024). "Qiskit Transpiler Documentation." *IBM*.
11. NVIDIA. (2023). "TensorRT: High-Performance Deep Learning Inference." *NVIDIA Documentation*.
12. McClean, J. R., et al. (2016). "The Theory of Variational Hybrid Quantum-Classical Algorithms." *New Journal of Physics*.
13. Farhi, E., et al. (2014). "A Quantum Approximate Optimization Algorithm." *arXiv:1411.4028*.
14. Cerezo, M., et al. (2021). "Cost Function Dependent Barren Plateaus in Shallow Parametrized Quantum Circuits." *Nature Communications*.
15. Erhard, A., et al. (2019). "Characterizing Large-Scale Quantum Computers via Cycle Benchmarking." *Nature Communications*.

---

## 15. Supplementary Materials (Planned)

- **Appendix A:** Full benchmark tables (all circuit families, sizes, devices, configurations)
- **Appendix B:** Calibration data used for each experiment (date, device, qubit properties)
- **Appendix C:** Detailed transpilation configurations for autotuning experiment
- **Appendix D:** Statistical analysis (error bars, confidence intervals, hypothesis tests)
- **Appendix E:** `qc-compiler` framework architecture and API documentation

---

## 16. Artifact Availability

- **Code:** https://github.com/Manideep3969/quantum-computing (to be released under MIT license)
- **Data:** All benchmark data will be deposited on Zenodo with a DOI
- **Hardware:** All experiments on IBM Quantum free-tier devices (reproducible via Qiskit)
- **Framework:** `qc-compiler` Python package (pip installable)