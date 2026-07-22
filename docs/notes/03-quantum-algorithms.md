# 3 — Quantum Algorithms

> Personal research notes — Manideep

---

## 3.1 Overview of Quantum Algorithmic Advantage

Quantum algorithms exploit two key resources:

1. **Superposition** — evaluate a function on many inputs simultaneously
2. **Interference** — amplify correct answers and cancel wrong ones

The art of quantum algorithm design is structuring interference patterns so that measuring the output yields the desired answer with high probability.

---

## 3.2 Deutsch-Jozsa Algorithm

**Problem:** Given a function f : {0,1}ⁿ → {0,1} that is either constant (same output for all inputs) or balanced (outputs 0 for exactly half the inputs), determine which type f is.

**Classical:** In the worst case, requires 2ⁿ⁻¹ + 1 queries.

**Quantum:** Requires exactly **1** query.

### Circuit

```
|0⟩ⁿ ── H⊗n ── Uf ── H⊗n ── Measure
|1⟩   ── H    ── Uf ─────────────────
```

### Key Insight

After the oracle query, the Hadamard transform interferes the amplitudes such that:
- If f is constant, measurement yields |0⟩ⁿ with certainty
- If f is balanced, measurement never yields |0⟩ⁿ

### Limitations

This is a promise problem — f is guaranteed to be either constant or balanced. The practical advantage is limited, but it was the first demonstration that quantum can be exponentially faster than classical.

---

## 3.3 Grover's Search Algorithm

**Problem:** Given an unsorted database of N items, find the one satisfying a condition f(x) = 1.

**Classical:** O(N) queries.

**Quantum:** O(√N) queries — **quadratic speedup**.

### Algorithm Steps

1. Initialize n = ⌈log₂N⌉ qubits to |0⟩ⁿ, apply H⊗n to get |s⟩ = (1/√N) Σ|x⟩
2. **Grover iteration** (repeat ≈ π√N/4 times):
   a. **Oracle:** Apply Uf where Uf|x⟩ = (-1)^{f(x)}|x⟩ (flips the phase of the target)
   b. **Diffusion:** Apply 2|s⟩⟨s| - I (reflect about the mean)
3. Measure — with high probability, the target state is observed

### Geometric Interpretation

The state vector rotates in a 2D plane spanned by the target |w⟩ and the uniform superposition |s⟩. Each Grover iteration rotates the state by angle 2θ where sin(θ) = 1/√N toward |w⟩. After ≈ π/(4θ) iterations, the state is nearly aligned with |w⟩.

### Over-rotation

Too many iterations overshoot — the state rotates past |w⟩ and probability decreases. Optimal iterations: ⌊π√N/4⌋.

### Generalizations

- **Multiple targets (k solutions):** O(√(N/k)) iterations
- **Amplitude amplification:** General framework for boosting success probability of any probabilistic algorithm

---

## 3.4 Shor's Factoring Algorithm

**Problem:** Given an integer N, find a non-trivial factor.

**Classical:** Best known algorithms are sub-exponential: O(e^{(log N)^{1/3}(log log N)^{2/3}}).

**Quantum:** O((log N)³) — **exponential speedup**. This is the most impactful known quantum algorithm.

### Reduction to Period Finding

Factoring N reduces to finding the **order** (period) of a random integer a modulo N. If r is the period of a^x mod N, then:

$$\gcd(a^{r/2} \pm 1, N)$$

yields a non-trivial factor of N (with probability ≥ 1/2 for random a).

### Quantum Period Finding (The Core)

1. Prepare superposition: (1/√Q) Σₓ |x⟩|a^x mod N⟩
2. Measure second register — collapses to some value, leaving a superposition of x's that are congruent modulo r
3. Apply **Quantum Fourier Transform (QFT)** to the first register
4. Measure — with high probability, yields a value close to kQ/r, from which r can be extracted via continued fractions

### QFT

The Quantum Fourier Transform on n qubits:

$$\text{QFT}|x\rangle = \frac{1}{\sqrt{2^n}} \sum_{k=0}^{2^n - 1} e^{2\pi i xk / 2^n} |k\rangle$$

QFT circuit uses O(n²) gates (vs. classical FFT's O(n2ⁿ)). This exponential compression of the transform is possible because we only need the output distribution, not the full transformed vector.

### Impact

- Breaks RSA, Diffie-Hellman, and ECC (with sufficient qubits)
- Requires ~2n logical qubits for an n-bit number
- With error correction, estimated ~millions of physical qubits needed for 2048-bit RSA

---

## 3.5 Quantum Phase Estimation (QPE)

**Problem:** Given a unitary U with eigenstate |u⟩ and eigenvalue e^{2πiφ}, estimate φ.

**Quantum:** Requires O(1/ε) queries to estimate φ to precision ε. Classical simulation requires O(1/ε) in general.

### Circuit

Uses n ancilla qubits (for precision) plus a register holding |u⟩:

```
|0⟩ⁿ ── H ⊗ controlled-U^{2^j} ── QFT† ── Measure → φ (binary)
|u⟩   ────────────────────────────────────────────────────
```

The j-th ancilla controls U^{2ʲ}. After inverse QFT, measurement yields an n-bit approximation to φ.

### Applications

- Order finding (used in Shor's)
- Eigenvalue computation for Hamiltonians
- Amplitude estimation
- HHL algorithm (quantum linear systems)

---

## 3.6 Variational Quantum Eigensolver (VQE)

**Problem:** Find the ground state energy of a Hamiltonian H.

**Approach:** Hybrid quantum-classical optimization.

### Algorithm

1. **Ansatz:** Prepare a parameterized quantum state |ψ(θ)⟩ using a parameterized circuit
2. **Measurement:** Measure expectation values ⟨Hᵢ⟩ for each term in H = ΣcᵢHᵢ on the quantum device
3. **Classical optimization:** Use a classical optimizer (COBYLA, SPSA, etc.) to minimize ⟨ψ(θ)|H|ψ(θ)⟩
4. **Repeat** until convergence

### Ansatz Choices

| Ansatz | Description | Pros | Cons |
|---|---|---|---|
| Hardware-efficient | Alternating layers of parameterized single-qubit rotations + entangling CNOTs | Shallow, hardware-friendly | Barren plateaus, poor expressibility |
| UCCSD | Unitary Coupled Cluster with Singles and Doubles | Chemically motivated, size-consistent | Deep circuits, many parameters |
| Adaptive (ADAPT-VQE) | Grow ansatz by adding operators that reduce energy most | Compact ansatz | Many measurements per iteration |

### Challenges

- **Barren plateaus**: gradients vanish exponentially with system size for random ansätze
- **Noise**: NISQ devices introduce errors into expectation values
- **Local minima**: optimization landscape is non-convex
- **Measurement overhead**: O(N⁴) measurements for molecular Hamiltonians

---

## 3.7 Quantum Approximate Optimization Algorithm (QAOA)

**Problem:** Find approximate solutions to combinatorial optimization problems.

### Algorithm

Prepare a state by alternating t layers of:

$$|\gamma, \beta\rangle = e^{-i\beta_p H_M} e^{-i\gamma_p H_C} \cdots e^{-i\beta_1 H_M} e^{-i\gamma_1 H_C} |+\rangle^{\otimes n}$$

- H_C = cost Hamiltonian (encodes the objective function)
- H_M = mixer Hamiltonian (typically Σ Xᵢ)
- γ, β = variational parameters optimized classically

At p → ∞, QAOA converges to the exact optimum (adiabatic limit). At finite p, it provides a p-level approximation.

### Applications

- Max-Cut
- MaxSAT
- Portfolio optimization
- Graph coloring

### Performance

- QAOA at p=1 achieves a 0.694-approximation for Max-Cut on 3-regular graphs (better than random but worse than the best classical Goemans-Williamson 0.878)
- Open question: can finite-p QAOA beat the best classical algorithms for any problem?

---

## 3.8 Algorithm Comparison Summary

| Algorithm | Speedup Type | Speedup | Input Model | Practical? |
|---|---|---|---|---|
| Deutsch-Jozsa | Exponential | 2ⁿ → 1 | Oracle | Pedagogical only |
| Grover | Quadratic | N → √N | Oracle | Yes, broad applicability |
| Shor | Exponential | Sub-exp → Poly | Classical | Yes, factoring (needs FTQC) |
| QPE | Exponential | Exp → Poly | Quantum state | Yes (needs FTQC) |
| VQE | Heuristic | N/A | Classical + quantum | Yes, NISQ |
| QAOA | Heuristic | N/A | Classical + quantum | Yes, NISQ (limited) |

FTQC = Fault-Tolerant Quantum Computing

---

## References

1. Nielsen, M. A., & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Chapters 5-6.
2. Shor, P. W. (1997). *Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer*. SIAM J. Comput., 26(5), 1484-1509.
3. Grover, L. K. (1996). *A fast quantum mechanical algorithm for database search*. STOC '96.
4. Peruzzo, A., et al. (2014). *A variational eigenvalue solver on a photonic quantum processor*. Nature Communications, 5, 4213.
5. Farhi, E., et al. (2014). *A Quantum Approximate Optimization Algorithm*. arXiv:1411.4028.