# 1 — Foundations of Quantum Computing

> Personal research notes — Manideep

---

## 1.1 From Classical to Quantum

### The Classical Bit

A classical bit exists in exactly one of two states: `0` or `1`. All digital computation is built on this abstraction. A register of *n* bits can represent exactly one of 2ⁿ possible values at any given time.

### The Qubit

A **qubit** (quantum bit) is a two-level quantum system whose state is a vector in a 2-dimensional complex Hilbert space. It is described by:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$$

where $\alpha, \beta \in \mathbb{C}$ and $|\alpha|^2 + |\beta|^2 = 1$ (normalization constraint).

**Key differences from classical bits:**

| Property | Classical Bit | Qubit |
|---|---|---|
| States | 0 or 1 | Superposition of \|0⟩ and \|1⟩ |
| Measurement | Deterministic | Probabilistic (collapses state) |
| n-system state space | 1 of 2ⁿ | Vector in 2ⁿ-dim Hilbert space |
| Copying | Trivial | Forbidden (no-cloning theorem) |

### Superposition

Superposition means a qubit can simultaneously exist in a combination of |0⟩ and |1⟩. Upon measurement, the qubit collapses to |0⟩ with probability |α|² or |1⟩ with probability |β|².

A register of *n* qubits exists in a superposition of all 2ⁿ basis states simultaneously:

$$|\psi\rangle = \sum_{i=0}^{2^n - 1} \alpha_i |i\rangle$$

This exponential state space is the source of quantum parallelism.

### Entanglement

**Entanglement** is a correlation between qubits that has no classical analogue. An entangled state cannot be written as a tensor product of individual qubit states.

Example — the Bell state:

$$|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$$

Measuring the first qubit as |0⟩ guarantees the second is also |0⟩, regardless of distance. This non-local correlation is what Einstein called "spooky action at a distance."

**Properties:**
- Violates Bell inequalities
- Cannot be described by local hidden variable theories
- Enables quantum teleportation, superdense coding, and quantum key distribution

### The No-Cloning Theorem

It is impossible to create an identical copy of an arbitrary unknown quantum state. Formally, there is no unitary operator *U* such that:

$$U|\psi\rangle|0\rangle = |\psi\rangle|\psi\rangle \quad \forall |\psi\rangle$$

**Implications:**
- Quantum states cannot be copied for backup or error checking (necessitating quantum error correction)
- Eavesdropping on quantum channels can be detected (basis for QKD)

---

## 1.2 Mathematical Framework

### Dirac Notation

| Symbol | Meaning |
|---|---|
| \|ψ⟩ (ket) | Column vector — a quantum state |
| ⟨ψ\| (bra) | Row vector — the dual (conjugate transpose) |
| ⟨φ\|ψ⟩ | Inner product between \|φ⟩ and \|ψ⟩ |
| \|φ⟩⟨ψ\| | Outer product (operator) |
| ⟨ψ\|ψ⟩ | Norm squared (must equal 1 for valid state) |

### Bloch Sphere

Any single-qubit pure state can be written as:

$$|\psi\rangle = \cos\frac{\theta}{2}|0\rangle + e^{i\phi}\sin\frac{\theta}{2}|1\rangle$$

This maps every qubit state to a point on the unit sphere (θ ∈ [0, π], φ ∈ [0, 2π)):

- **North pole (θ=0):** |0⟩
- **South pole (θ=π):** |1⟩
- **Equator:** equal superpositions with different phases

The Bloch vector is: **r** = (sin θ cos φ, sin θ sin φ, cos θ)

### The Computational Basis

The standard basis for an n-qubit system:

$$\{|00\cdots0\rangle, |00\cdots1\rangle, \ldots, |11\cdots1\rangle\}$$

Numbered |0⟩ through |2ⁿ−1⟩. All measurements are expressed in this basis by default.

### Tensor Products

The state space of a composite system is the **tensor product** of the individual spaces:

$$\mathcal{H}_{AB} = \mathcal{H}_A \otimes \mathcal{H}_B$$

For two qubits: dim = 2 × 2 = 4. Basis states are |00⟩, |01⟩, |10⟩, |11⟩.

---

## 1.3 Measurement

### Projective Measurement (Von Neumann)

Given an observable with eigenvalues {mᵢ} and eigenstates {|mᵢ⟩}, measuring |ψ⟩ yields outcome mᵢ with probability:

$$P(m_i) = |\langle m_i|\psi\rangle|^2$$

The post-measurement state collapses to |mᵢ⟩.

### Born Rule

For a state $|\psi\rangle = \sum_i \alpha_i |i\rangle$, the probability of measuring outcome *j* is:

$$P(j) = |\alpha_j|^2$$

### Partial Measurement

Measuring a subset of qubits in an entangled system collapses only the measured subsystem. The remaining qubits are left in a state consistent with the measurement outcome.

Example: measuring the first qubit of $|\Phi^+\rangle$ as |0⟩ leaves the second qubit in |0⟩.

---

## 1.4 Quantum vs Classical: Computational Complexity

| Problem | Classical | Quantum | Speedup |
|---|---|---|---|
| Unstructured search | O(N) | O(√N) | Quadratic (Grover) |
| Integer factoring | Sub-exponential | Polynomial | Exponential (Shor) |
| Simulation of quantum systems | Exponential | Polynomial | Exponential |
| Deutsch-Jozsa (n-bit) | O(2ⁿ⁄²) worst case | O(1) | Exponential |

**Important caveat:** Not all problems admit quantum speedup. Quantum computers are not universally faster — they excel where quantum structure (interference, entanglement) can be exploited.

---

## References

1. Nielsen, M. A., & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Cambridge University Press.
2. Preskill, J. (2018). *Quantum Computing in the NISQ era and beyond*. Quantum, 2, 79.
3. Benenti, G., Casati, G., & Strini, G. (2004). *Principles of Quantum Computation and Information*. World Scientific.