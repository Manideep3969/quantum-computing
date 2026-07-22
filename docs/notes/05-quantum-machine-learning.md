# 5 — Quantum Machine Learning

> Personal research notes — Manideep

---

## 5.1 Motivation and Landscape

Quantum Machine Learning (QML) sits at the intersection of quantum computing and machine learning. There are four possible paradigms:

| Abbreviation | Description | Example |
|---|---|---|
| **CC** | Classical data, Classical algorithm | Standard ML (CNNs, transformers) |
| **QC** | Quantum data, Classical algorithm | Classical post-processing of quantum experiments |
| **CQ** | Classical data, Quantum algorithm | Quantum-enhanced ML (variational classifiers, QNNs) |
| **QQ** | Quantum data, Quantum algorithm | Learning from quantum sensors, QPE + ML |

Most current research focuses on **CQ** (running quantum circuits on classical data) since near-term devices process classical datasets.

---

## 5.2 Quantum Feature Maps

### Kernel Methods

The central idea: map classical data x into a high-dimensional quantum Hilbert space via a feature map:

$$\phi: \mathcal{X} \rightarrow \mathcal{H}, \quad x \mapsto |\phi(x)\rangle$$

The quantum kernel is then:

$$K(x_i, x_j) = |\langle\phi(x_i)|\phi(x_j)\rangle|^2$$

If this kernel is classically hard to compute, the quantum embedding may provide an advantage.

### Explicit Feature Maps in Qiskit

```python
from qiskit.circuit.library import ZZFeatureMap

feature_map = ZZFeatureMap(
    feature_dimension=2,
    reps=2,
    entanglement='linear'
)
```

The ZZ feature map applies: $U_{\Phi(x)} = \exp\left(i\sum_{S \subseteq [n]} \phi_S(x) \bigotimes_{i \in S} Z_i\right)$

This creates entanglement-dependent features that are classically intractable for sufficiently deep circuits.

### Quantum Kernel Advantage

Havlíček et al. (2018) showed that for certain classification problems:
- The quantum kernel can separate data that no classical kernel can
- This requires the feature map to be classically hard to simulate
- However, for easy feature maps, classical kernels can replicate the quantum kernel

---

## 5.3 Variational Quantum Classifiers (VQC)

### Architecture

1. **Feature map** U_Φ(x): encodes classical data into quantum states
2. **Variational ansatz** W(θ): trainable parameterized circuit
3. **Measurement**: extract a classical output (e.g., expectation of Z⊗n)

```
|0⟩ⁿ ── U_Φ(x) ── W(θ) ── Measure ── f(x; θ)
```

### Training

- **Loss:** Binary cross-entropy, MSE, or hinge loss on measured expectations
- **Optimizer:** COBYLA, SPSA, Adam (gradient via parameter-shift rule)
- **Parameter-shift rule:** For a Pauli expectation ⟨P⟩(θ):
  $$\frac{\partial}{\partial \theta_i}\langle P\rangle = \frac{\langle P\rangle(\theta_i + \frac{\pi}{2}) - \langle P\rangle(\theta_i - \frac{\pi}{2})}{2}$$

### Advantages
- Can run on NISQ devices (shallow circuits)
- Trainable with classical optimizers

### Challenges
- **Barren plateaus**: gradients vanish exponentially with system size for deep/random circuits
- **Limited expressivity**: shallow circuits may not capture complex decision boundaries
- **Noise**: hardware errors corrupt training signals
- **Generalization**: risk of overfitting to quantum noise

---

## 5.4 Quantum Neural Networks (QNNs)

### Structure

A QNN generalizes the VQC by allowing multiple measurement-feedback cycles:

1. Encode input → parameterized unitary → measure (partial) → feed forward → repeat
2. Or: single unitary with many parameterized layers

### Quantum Perceptron

$$y = \text{sign}\left(\sum_i w_i x_i + b\right) \quad \rightarrow \quad y = \text{sign}\left(\langle\psi(x)|U^\dagger(\theta) O U(\theta)|\psi(x)\rangle\right)$$

### Quantum Convolutional Neural Networks (QCNN)

Inspired by classical CNNs:

1. **Convolution**: parameterized two-qubit gates on nearest neighbors
2. **Pooling**: measure half the qubits, condition remaining gates on outcomes
3. **Repeat**: reduce qubits until 1 remains for classification

```
q₀ ──■─── ─── M ───
q₁ ──┼─── ─── M ───
q₂ ──■─── ───■─── M ───
q₃ ──┼─── ───■─── M ───
q₄ ─────── ───■─── ───■─── M
q₅ ─────── ───■─── ───■─── M
q₆ ─────── ─────── ───■─── ───■─── M
q₇ ─────── ─────── ───■─── ───■─── M
      conv1    conv2    conv3   → output
```

**Advantages:** Reduces qubit count progressively, naturally hierarchical, translation-equivariant.

---

## 5.5 Quantum Generative Models

### Quantum Circuit Born Machine (QCBM)

Generates samples from a probability distribution defined by a parameterized quantum circuit:

$$p_\theta(x) = |\langle x|U(\theta)|0\rangle|^2$$

Training: minimize the maximum mean discrepancy (MMD) between the model distribution and the data distribution.

$$\mathcal{L}(\theta) = \mathbb{E}_{x,y \sim p_\theta}[k(x,y)] - 2\mathbb{E}_{x \sim p_\theta, y \sim p_{\text{data}}}[k(x,y)] + \mathbb{E}_{x,y \sim p_{\text{data}}}[k(x,y)]$$

### Quantum GANs (qGAN)

Two competing quantum circuits:
- **Generator**: produces synthetic quantum states
- **Discriminator**: distinguishes real from generated data

Both can be quantum circuits (QQ) or the discriminator can be classical (CQ).

### Quantum Boltzmann Machines

Quantum analogue of restricted Boltzmann machines with:
- Visible and hidden units as qubits
- Transverse field terms (Pauli-X) enabling quantum tunneling
- Training via quantum annealing or gate-model simulation

---

## 5.6 Hybrid Quantum-Classical ML

### Data Embedding Strategies

| Strategy | Method | Qubits |
|---|---|---|
| Basis encoding | x → \|x⟩ (binary) | ⌈log₂(max_x)⌉ |
| Amplitude encoding | x → amplitude vector | ⌈log₂(N)⌉ for N features |
| Angle encoding | x → rotation angle | N qubits for N features |
| Higher-order encoding | x → feature map kernels | N qubits, multiple layers |

**Amplitude encoding** is exponentially efficient in data representation but costly to prepare.

### Dimensionality Reduction

For datasets larger than the available qubits:
- PCA (classical) → reduced features → quantum circuit
- Autoencoder (classical or quantum) → latent space → quantum circuit
- Quantum random access memory (QRAM) — theoretical, not yet practical

### Transfer Learning

Pre-train a classical model (e.g., ResNet) → use its penultimate layer as features → feed into a quantum classifier. Demonstrated to work well for image classification with limited quantum resources.

---

## 5.7 Barren Plateaus

The most serious challenge for QML on near-term devices.

### Definition

A **barren plateau** occurs when the variance of the cost function gradient vanishes exponentially with the number of qubits:

$$\text{Var}\left[\frac{\partial C}{\partial \theta_i}\right] \in O\left(\frac{1}{2^n}\right)$$

This means gradient-based optimization becomes exponentially hard as the system grows.

### Causes

1. **Expressibility**: Highly expressive (random-like) ansätze have flat landscapes
2. **Entanglement**: Deep entangling circuits induce barren plateaus
3. **Global cost functions**: Measuring all qubits (vs. local measurements)
4. **Noise**: Hardware noise flattens the landscape further

### Mitigations

| Strategy | Description |
|---|---|
| Local cost functions | Measure only a subset of qubits |
| Shallow circuits | Limit circuit depth |
| Structured ansätze | Use problem-inspired architectures (e.g., Hamiltonian-inspired) |
| Parameter initialization | Identity-block initialization, layer-wise training |
| Gradient-free optimizers | CMA-ES, Powell, SPSA |

---

## 5.8 QML Resource Comparison

| Model | Qubits | Depth | Trainable | Advantage? |
|---|---|---|---|---|
| VQC | O(N) | O(1)-O(N) | O(N) | Potential kernel advantage |
| QNN | O(N) | O(poly(N)) | O(poly(N)) | Unproven |
| QCNN | O(N) | O(log N) | O(N) | Efficient hierarchical |
| QCBM | O(N) | O(poly(N)) | O(poly(N)) | Quantum sampling advantage |
| QGAN | O(N) | O(poly(N)) | O(poly(N)) | Unproven |

---

## 5.9 Open Questions

1. **Quantum advantage in ML**: Is there a provable, practical advantage for any real-world ML task?
2. **Barren plateaus**: Can we design architectures that provably avoid them?
3. **Data loading**: How to efficiently load classical data into quantum states (the input problem)?
4. **Noise resilience**: Which QML models degrade gracefully under hardware noise?
5. **Generalization**: What is the sample complexity of quantum learners?

---

## References

1. Biamonte, J., et al. (2017). *Quantum machine learning*. Nature, 549(7671), 195-202.
2. Havlíček, V., et al. (2018). *Supervised learning with quantum-enhanced feature spaces*. Nature, 567(7747), 209-212.
3. Schuld, M., & Killoran, N. (2019). *Quantum machine learning in feature Hilbert spaces*. Physical Review Letters, 122(4), 040504.
4. McClean, J. R., et al. (2016). *The theory of variational hybrid quantum-classical algorithms*. New Journal of Physics, 18(2), 023023.
5. Cong, I., Choi, S., & Lukin, M. D. (2019). *Quantum convolutional neural networks*. Nature Physics, 15(12), 1273-1278.