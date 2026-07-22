# 4 — Quantum Error Correction

> Personal research notes — Manideep

---

## 4.1 The Need for Error Correction

Quantum states are fragile. Errors arise from:

| Error Source | Description | Timescale |
|---|---|---|
| **Decoherence** | Interaction with environment causes relaxation (T₁) and dephasing (T₂) | ~50-500 μs (superconducting) |
| **Gate errors** | Imperfect control pulses | ~0.1-1% per gate |
| **Measurement errors** | Readout infidelity | ~1-3% |
| **Crosstalk** | Unwanted coupling between qubits | Device-dependent |

**Threshold theorem:** If the error rate per physical operation is below a threshold (~1% for surface codes), arbitrarily long quantum computations are possible with polylogarithmic overhead.

### Three Types of Quantum Errors

1. **Bit-flip (X error):** |0⟩ → |1⟩, |1⟩ → |0⟩
2. **Phase-flip (Z error):** |0⟩ → |0⟩, |1⟩ → −|1⟩
3. **Bit-phase-flip (Y error):** Combination of X and Z

An arbitrary error on a qubit can be decomposed as:

$$E = \alpha_0 I + \alpha_1 X + \alpha_2 Y + \alpha_3 Z$$

Correcting X, Y, and Z errors corrects any arbitrary single-qubit error.

---

## 4.2 Repetition Codes (Classical Warmup)

### Bit-Flip Repetition Code

Encode 1 logical bit into 3 physical bits:

| Logical | Encoding |
|---|---|
| 0 | 000 |
| 1 | 111 |

**Syndrome measurement:** Compare bits pairwise
- 000 → no error
- 001, 010, 100 → bit 1, 2, or 3 flipped → correct by flipping back

This corrects any single bit-flip error (distance-3 code, corrects ⌊(d−1)/2⌋ = 1 error).

### Why Classical Repetition Fails for Phase Errors

A phase flip in the Hadamard basis is a bit-flip in the computational basis, but measuring directly collapses superpositions. Quantum error correction must work without measuring (and collapsing) the encoded information.

---

## 4.3 Three-Qubit Phase-Flip Code

Encodes |ψ⟩ = α|0⟩ + β|1⟩ into:

$$|\psi\rangle \rightarrow \alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$$

where |±⟩ = (|0⟩ ± |1⟩)/√2. A phase flip Z on any one qubit changes a |+⟩ to |−⟩ or vice versa, which is detected by measuring in the X basis.

Corrects any single phase-flip error.

---

## 4.4 The Shor Code

The first **fully fault-tolerant** quantum error-correcting code. Encodes 1 logical qubit into 9 physical qubits, correcting any arbitrary single-qubit error.

### Structure

Concatenation of the bit-flip and phase-flip codes:

$$|0\rangle_L = \frac{1}{2\sqrt{2}}(|000\rangle + |111\rangle)^{\otimes 3}$$

$$|1\rangle_L = \frac{1}{2\sqrt{2}}(|000\rangle - |111\rangle)^{\otimes 3}$$

Each block of 3 protects against bit-flips. The sign across blocks protects against phase-flips.

### Error Correction Procedure

1. Measure bit-flip syndromes within each 3-qubit block (as in the bit-flip code)
2. Measure phase-flip syndromes across blocks (as in the phase-flip code)
3. Apply corrections based on syndromes

---

## 4.5 Stabilizer Codes

The modern framework for quantum error correction. Most important QEC codes are stabilizer codes.

### Definition

A stabilizer code is defined by its **stabilizer group** S — an abelian subgroup of the n-qubit Pauli group that does not contain −I.

- **Code space:** The +1 eigenspace of all stabilizers
- **Logical qubits:** k = n − log₂|S| logical qubits
- **Distance d:** Minimum weight of a Pauli operator that commutes with all stabilizers but is not in S
- **Notation:** [[n, k, d]] — n physical qubits, k logical qubits, distance d

### Error Detection

Errors are Pauli operators E. If E anticommutes with any stabilizer S ∈ S, the syndrome bit for S flips. By measuring all stabilizer generators, we get a **syndrome** that identifies the error (up to equivalence classes).

### Important Stabilizer Codes

| Code | Parameters | Description |
|---|---|---|
| Shor code | [[9, 1, 3]] | First QEC code |
| Steane code | [[7, 1, 3]] | CSS code from Hamming(7,4) |
| Laflamme code | [[5, 1, 3]] | Smallest possible distance-3 code |
| Surface code | [[d², 1, d]] | Topological, 2D nearest-neighbor, threshold ~1% |

---

## 4.6 The Surface Code

The leading candidate for fault-tolerant quantum computing due to its high threshold and 2D nearest-neighbor layout.

### Structure

- Qubits live on edges of a 2D lattice
- **Stabilizers:** 
  - Plaquette operators (products of Z on edges around a face) — measure Z-type syndromes
  - Star operators (products of X on edges around a vertex) — measure X-type syndromes
- **Logical qubits:** Created by introducing defects (holes) or twists in the lattice

### Properties

| Property | Value |
|---|---|
| Threshold | ~1.1% (Circuit-level noise) |
| Qubits per logical qubit (d=17) | ~2 × 17² ≈ 578 |
| Code distance | d (odd integer) |
| Correctable errors | ⌊(d−1)/2⌋ |

### Why the Surface Code?

1. **High threshold** — tolerates realistic noise levels
2. **Nearest-neighbor interactions** — compatible with 2D hardware
3. **Scalable** — increasing d improves protection
4. **Mature tooling** — extensive simulation and experimental validation

**Cost:** For a distance-d surface code, roughly 2d² physical qubits per logical qubit. A fault-tolerant factoring of 2048-bit RSA is estimated to require millions of physical qubits.

---

## 4.7 Fault-Tolerant Quantum Computing

Error correction alone is insufficient — the correction procedure itself can introduce errors. **Fault tolerance** ensures errors don't propagate catastrophically.

### Principles

1. **Error propagation is limited:** A single error in any component causes at most one error per logical qubit block
2. **Verification:** Check that corrections are correct before applying them
3. **Transversal gates:** Apply physical gates qubit-wise across blocks — errors cannot propagate between qubits of the same logical block

### Magic State Distillation

The Eastin-Knill theorem proves that no universal gate set can be implemented transversally for any code with d > 1. Solution: non-Clifford gates (like T) are injected via **magic state distillation**:

1. Prepare noisy |T⟩ states on physical qubits
2. Distill high-fidelity |T⟩ states using Clifford operations
3. Inject the distilled state via gate teleportation

This dominates the overhead of fault-tolerant computation.

---

## 4.8 Current Experimental Status

| Platform | Qubits | Demonstrated QEC |
|---|---|---|
| IBM (2024) | 1121 (Condor) | Distance-3 surface code |
| Google (2023) | 70 (Sycamore) | Distance-5 surface code below threshold |
| Quantinuum (2024) | 56 (H2) | Multiple rounds of error correction |
| IonQ (2024) | 36 | Error-mitigated circuits |

**Key milestone achieved (2023):** Google demonstrated that increasing surface code distance from 3 to 5 to 7 reduces logical error rates, showing the threshold theorem works in practice.

---

## References

1. Shor, P. W. (1995). *Scheme for reducing decoherence in quantum computer memory*. Physical Review A, 52(4), R2493.
2. Steane, A. M. (1996). *Error correcting codes in quantum theory*. Physical Review Letters, 77(5), 793.
3. Kitaev, A. Y. (2003). *Fault-tolerant quantum computation by anyons*. Annals of Physics, 303(1), 2-30.
4. Fowler, A. G., et al. (2012). *Surface codes: Towards practical large-scale quantum computation*. Physical Review A, 86(3), 032324.
5. Acharya, R., et al. (2023). *Suppressing quantum errors by scaling a surface code logical qubit*. Nature, 614, 676-681.