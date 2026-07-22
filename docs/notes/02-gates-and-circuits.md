# 2 — Quantum Gates and Circuits

> Personal research notes — Manideep

---

## 2.1 Quantum Gates

Quantum gates are **unitary operators** that act on qubits. Unitarity (U†U = I) ensures:
1. Reversibility — every gate can be inverted
2. Probability conservation — normalization is preserved

### Single-Qubit Gates

| Gate | Matrix | Action |
|---|---|---|
| **I** (Identity) | [[1,0],[0,1]] | No operation |
| **X** (NOT / Pauli-X) | [[0,1],[1,0]] | Flips \|0⟩ ↔ \|1⟩ |
| **Y** (Pauli-Y) | [[0,-i],[i,0]] | Rotation about Y-axis |
| **Z** (Pauli-Z) | [[1,0],[0,-1]] | Phase flip: \|1⟩ → −\|1⟩ |
| **H** (Hadamard) | 1/√2 [[1,1],[1,-1]] | Creates equal superposition |
| **S** (Phase) | [[1,0],[0,i]] | π/2 phase on \|1⟩ |
| **T** (π/8) | [[1,0],[0,e^{iπ/4}]] | π/4 phase on \|1⟩ |
| **Rₓ(θ)** | [[cos(θ/2), -isin(θ/2)], [-isin(θ/2), cos(θ/2)]] | Rotation about X |
| **R_y(θ)** | [[cos(θ/2), -sin(θ/2)], [sin(θ/2), cos(θ/2)]] | Rotation about Y |
| **R_z(θ)** | [[e^{-iθ/2}, 0], [0, e^{iθ/2}]] | Rotation about Z |

### The Hadamard Gate in Detail

$$H|0\rangle = \frac{1}{\sqrt{2}}(|0\rangle + |1\rangle) = |+\rangle$$

$$H|1\rangle = \frac{1}{\sqrt{2}}(|0\rangle - |1\rangle) = |-\rangle$$

$$H|+\rangle = |0\rangle, \quad H|-\rangle = |1\rangle$$

The Hadamard creates superposition from basis states and collapses superposition back to basis states. It is its own inverse: H² = I.

### Universality of {H, T}

The set {H, T} is approximately universal for single-qubit operations — any single-qubit unitary can be approximated to arbitrary precision by a sequence of H and T gates. This is the **Solovay-Kitaev theorem**: the overhead grows only polylogarithmically in 1/ε.

---

## 2.2 Two-Qubit Gates

### CNOT (Controlled-NOT)

The most important two-qubit gate. Flips the target qubit iff the control qubit is |1⟩:

$$\text{CNOT}|00\rangle = |00\rangle, \quad \text{CNOT}|01\rangle = |01\rangle$$
$$\text{CNOT}|10\rangle = |11\rangle, \quad \text{CNOT}|11\rangle = |10\rangle$$

Matrix form:
```
[[1, 0, 0, 0],
 [0, 1, 0, 0],
 [0, 0, 0, 1],
 [0, 0, 1, 0]]
```

### Other Controlled Gates

| Gate | Control Condition |
|---|---|
| CNOT | Flip target if control = 1 |
| CZ (Controlled-Z) | Phase flip on \|11⟩ |
| CPHASE(φ) | Phase e^{iφ} on \|11⟩ |
| SWAP | Exchange two qubit states |
| iSWAP | SWAP with additional i phase |

### Entangling Capability

Any two-qubit gate that can create entanglement from product states, combined with all single-qubit gates, forms a **universal gate set**. CNOT + all single-qubit gates is the standard universal set.

---

## 2.3 Quantum Circuits

### Circuit Diagram Conventions

- Time flows **left to right**
- Wires carry qubits (single lines) and classical bits (double lines)
- Gates are boxes or symbols on qubit wires
- Measurement is denoted by a meter symbol, producing a classical output

### Example: Bell State Preparation

```
|0⟩ ── H ──●──
            │
|0⟩ ───────⊕──
```

Steps:
1. Apply H to qubit 1: |00⟩ → (|0⟩ + |1⟩)/√2 ⊗ |0⟩ = (|00⟩ + |10⟩)/√2
2. Apply CNOT: (|00⟩ + |10⟩)/√2 → (|00⟩ + |11⟩)/√2 = |Φ⁺⟩

### Circuit Depth and Width

- **Width**: number of qubits used
- **Depth**: longest path (in gate count) from input to output — measures circuit time
- **Gate count**: total number of gates — measures circuit complexity

Minimizing depth is critical on NISQ devices due to decoherence and gate errors.

---

## 2.4 Circuit Identities

Useful equivalences for circuit optimization:

1. **HZH = X** — Z gate conjugated by Hadamard gives X
2. **HXH = Z** — X gate conjugated by Hadamard gives Z
3. **CNOT(b,a) = H_a H_b · CNOT(a,b) · H_a H_b** — reversing CNOT direction
4. **SWAP = CNOT₁₂ · CNOT₂₁ · CNOT₁₂** — SWAP from three CNOTs
5. **Toffoli (CCNOT)** — controlled-controlled-NOT, universal for classical reversible computation

---

## 2.5 Measurement in Circuits

Measurement collapses a qubit to the computational basis. It is **irreversible** and produces a classical bit.

```
|ψ⟩ ──── M ─── 0 or 1 (classical)
```

- Measurement in other bases is achieved by rotating before measuring in the computational basis (e.g., measure in X-basis: apply H, then measure)
- Mid-circuit measurement is possible but collapses the state, affecting subsequent operations
- **Deferred measurement principle**: measurements can always be moved to the end of a circuit without changing the output distribution (in principle)

---

## 2.6 NISQ Considerations

On real quantum hardware:

| Constraint | Impact |
|---|---|
| Limited qubit connectivity | Requires SWAP gates, increasing depth |
| Gate infidelity (~99.5% for 2-qubit) | Shallow circuits preferred |
| Decoherence time (T₁, T₂ ~ 100μs) | Circuit must finish before qubits decohere |
| Measurement errors (~1-3%) | Error mitigation needed |
| Limited qubit count (50-1000+) | Constrains problem size |

**Transpilation** maps a logical circuit to a physical device's native gate set and qubit topology. This is done by Qiskit's transpiler, Cirq's routing, etc.

---

## References

1. Nielsen, M. A., & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Cambridge University Press. Chapters 4-5.
2. Barenco, A., et al. (1995). *Elementary gates for quantum computation*. Physical Review A, 52(5), 3457.
3. Dawson, C. M., & Nielsen, M. A. (2006). *The Solovay-Kitaev algorithm*. Quantum Information & Computation, 6(1), 81-95.