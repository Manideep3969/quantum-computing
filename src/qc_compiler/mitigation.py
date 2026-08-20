"""Adaptive error mitigation for quantum circuits.

Analogous to mixed-precision training in deep learning, this module
allocates more measurement resources (shots and noise scales) to
circuit segments that contribute most to the final expectation value.

The key insight: just as mixed-precision training uses FP16 for
low-sensitivity operations and FP32 for high-sensitivity ones, we
use fewer noise scales and shots for low-sensitivity circuit
segments and more for high-sensitivity ones.

Three mitigation methods are supported:

    1. ZNE (Zero-Noise Extrapolation): Run the circuit at multiple
       noise scales and extrapolate to the zero-noise limit.
       Richardson extrapolation is used for 3+ scales, linear
       extrapolation for 2 scales.

    2. PEC (Probabilistic Error Cancellation): Characterize gate
       errors and apply quasi-probability decomposition to
       cancel them statistically.

    3. CDR (Clifford Data Regression): Run classically simulable
       Clifford circuits alongside the target circuit and use
       regression to correct the noisy output.

Adaptive allocation:
    For each circuit segment, sensitivity is computed based on:
    - Two-qubit gate count (non-variational circuits)
    - Gradient magnitude (variational circuits, if observable provided)

References:
    Temme, K., Bravyi, S., & Gambetta, J. M. (2017). Error mitigation
        for short-depth quantum circuits. Physical Review Letters, 119(18).
    Li, Y., & Benjamin, S. C. (2017). Efficient variational quantum
        simulator employing active error minimization. Physical Review X.
    Kandala, A., et al. (2019). Error-mitigated quantum gates exceeding
        99.9% fidelity. Nature.

    Shots are then allocated proportional to sensitivity, and
    noise scale count is determined by sensitivity tier:
    - High sensitivity: 3+ noise scales (full ZNE)
    - Medium sensitivity: 2 scales (linear extrapolation)
    - Low sensitivity: 1 scale (no mitigation)
"""

from dataclasses import dataclass, field

import numpy as np
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.utils import TWO_QUBIT_GATES


@dataclass
class MitigationPlan:
    """Execution plan for adaptive error mitigation.

    Attributes:
        noise_scales: List of noise scale factors for ZNE.
        shots_per_scale: Mapping from noise scale to shot count.
        subcircuit_sensitivity: Mapping from segment index to
            sensitivity score.
        total_shots: Total number of shots across all scales.
        method: Mitigation method ('zne', 'adaptive', 'pec', or 'cdr').
        segments: Number of circuit segments identified.
        shots_per_segment: Mapping from segment index to shot count.
        scales_per_segment: Mapping from segment index to list of
            noise scale factors.
    """

    noise_scales: list[float] = field(default_factory=list)
    shots_per_scale: dict[int, int] = field(default_factory=dict)
    subcircuit_sensitivity: dict[int, float] = field(default_factory=dict)
    total_shots: int = 0
    method: str = "zne"
    segments: int = 0
    shots_per_segment: dict[int, int] = field(default_factory=dict)
    scales_per_segment: dict[int, list[float]] = field(default_factory=dict)

    @property
    def total_noise_scales(self) -> int:
        """Total number of noise scale factors."""
        return len(self.noise_scales)

    @property
    def avg_shots_per_scale(self) -> float:
        """Average shots per noise scale."""
        if not self.shots_per_scale:
            return 0.0
        return sum(self.shots_per_scale.values()) / len(
            self.shots_per_scale
        )

    @property
    def max_sensitivity(self) -> float:
        """Maximum sensitivity across segments."""
        if not self.subcircuit_sensitivity:
            return 0.0
        return max(self.subcircuit_sensitivity.values())

    @property
    def min_sensitivity(self) -> float:
        """Minimum sensitivity across segments."""
        if not self.subcircuit_sensitivity:
            return 0.0
        return min(self.subcircuit_sensitivity.values())


@dataclass
class MitigationResult:
    """Result of executing a mitigation plan.

    Attributes:
        mitigated_value: The mitigated expectation value.
        raw_values: Raw expectation values at each noise scale.
        noise_scales: Noise scale factors used.
        extrapolation_coefficients: Coefficients from Richardson
            extrapolation.
        shots_used: Total shots actually used.
        method: Mitigation method used.
        placeholder: Whether this result is from a placeholder implementation
            that does not perform true error mitigation.
    """

    mitigated_value: float = 0.0
    raw_values: list[float] = field(default_factory=list)
    noise_scales: list[float] = field(default_factory=list)
    extrapolation_coefficients: list[float] = field(default_factory=list)
    shots_used: int = 0
    method: str = "zne"
    placeholder: bool = False


class AdaptiveErrorMitigation:
    """Applies gradient-aware shot allocation for error mitigation.

    Inspired by mixed-precision training: allocate more "precision"
    (shots and noise scales) to high-sensitivity circuit segments
    and fewer to low-sensitivity segments.

    Usage::

        from qc_compiler import CostModel, AdaptiveErrorMitigation

        model = CostModel()
        mitigation = AdaptiveErrorMitigation(cost_model=model)

        plan = mitigation.create_plan(circuit, total_shots=8192)
        result = mitigation.execute(circuit, plan, raw_values=[0.85, 0.72, 0.58])
        print(f"Mitigated value: {result.mitigated_value:.4f}")
    """

    def __init__(self, cost_model: CostModel):
        self.cost_model = cost_model

    def create_plan(
        self,
        circuit: QuantumCircuit,
        observable: dict | None = None,
        total_shots: int = 8192,
        method: str = "zne",
        num_segments: int | None = None,
    ) -> MitigationPlan:
        """Create an adaptive mitigation plan.

        Decomposes the circuit into segments, computes sensitivity
        for each segment, and allocates shots and noise scales
        proportionally.

        Args:
            circuit: The quantum circuit to mitigate.
            observable: Optional observable specification for
                variational sensitivity. If None, uses two-qubit
                gate count as a proxy for sensitivity.
            total_shots: Total shot budget.
            method: Mitigation method ('zne', 'adaptive', 'pec', or 'cdr').
            num_segments: Number of circuit segments. If None,
                segments are determined by two-qubit gate boundaries.

        Returns:
            A MitigationPlan with allocation details.
        """
        if method not in ("zne", "pec", "cdr", "adaptive"):
            raise ValueError(
                f"Unknown mitigation method '{method}'. "
                "Use 'zne', 'pec', 'cdr', or 'adaptive'."
            )

        resolved_method = "zne" if method == "adaptive" else method

        if circuit.num_qubits == 0 or circuit.depth() == 0:
            return MitigationPlan(
                noise_scales=[1.0],
                shots_per_scale={0: total_shots},
                total_shots=total_shots,
                method=method,
                segments=1,
            )

        sensitivity = self._compute_sensitivity(circuit, observable or {})

        if num_segments is None:
            num_segments = max(1, len(sensitivity))
        num_segments = max(1, min(num_segments, len(sensitivity)))

        shots_per_segment = self._allocate_shots(
            sensitivity, total_shots
        )

        scales_per_segment = self._assign_noise_scales(
            sensitivity, resolved_method
        )

        all_scales = sorted(
            {s for scales in scales_per_segment.values() for s in scales}
        )

        shots_per_scale = {}
        for seg_idx, scales in scales_per_segment.items():
            seg_shots = shots_per_segment.get(seg_idx, 0)
            shots_per_scale_entry = max(1, seg_shots // len(scales))
            for scale in scales:
                scale_key = int(scale * 10)
                shots_per_scale[scale_key] = shots_per_scale.get(
                    scale_key, 0
                ) + shots_per_scale_entry

        return MitigationPlan(
            noise_scales=all_scales,
            shots_per_scale=shots_per_scale,
            subcircuit_sensitivity=sensitivity,
            total_shots=total_shots,
            method=method,
            segments=num_segments,
            shots_per_segment=shots_per_segment,
            scales_per_segment=scales_per_segment,
        )

    def execute(
        self,
        circuit: QuantumCircuit,
        plan: MitigationPlan,
        raw_values: list[float] | None = None,
    ) -> MitigationResult:
        """Execute the mitigation plan and return results.

        For ZNE: uses Richardson extrapolation on raw_values.
        For PEC and CDR: returns the raw values with metadata.

        Args:
            circuit: The quantum circuit (used for metadata only).
            plan: The mitigation plan to follow.
            raw_values: Measured expectation values at each noise
                scale. Must match the number of noise scales in the
                plan. If None, uses simulated values from the cost
                model.

        Returns:
            A MitigationResult with mitigated values.
        """
        resolved_method = "zne" if plan.method == "adaptive" else plan.method

        self._last_circuit = circuit

        if resolved_method == "zne":
            return self._extrapolate_zne(plan, raw_values)
        elif resolved_method == "pec":
            return self._execute_pec(plan, raw_values)
        elif resolved_method == "cdr":
            return self._execute_cdr(plan, raw_values)
        else:
            return MitigationResult(method=plan.method)

    def _compute_sensitivity(
        self, circuit: QuantumCircuit, observable: dict
    ) -> dict[int, float]:
        """Compute sensitivity for each circuit segment.

        For non-variational circuits, sensitivity is based on
        two-qubit gate count per segment. For variational circuits
        with an observable, gradient sensitivity is used.

        Args:
            circuit: The quantum circuit.
            observable: Observable specification (may be empty).

        Returns:
            Dictionary mapping segment index to sensitivity score.
        """
        segments = self._segment_circuit(circuit)
        sensitivity = {}

        for seg_idx, (start, end) in enumerate(segments):
            seg_gates = 0
            seg_2q_gates = 0
            for i in range(start, end):
                if i < len(circuit.data):
                    instr = circuit.data[i]
                    gate_name = instr.operation.name
                    if gate_name not in ("barrier", "measure", "reset"):
                        seg_gates += 1
                        if gate_name in TWO_QUBIT_GATES:
                            seg_2q_gates += 1

            if observable and "gradient" in observable:
                grad_values = observable["gradient"]
                if seg_idx < len(grad_values):
                    sensitivity[seg_idx] = abs(grad_values[seg_idx])
                else:
                    sensitivity[seg_idx] = float(seg_2q_gates)
            else:
                sensitivity[seg_idx] = float(seg_2q_gates)

        total = sum(sensitivity.values())
        if total > 0:
            sensitivity = {k: v / total for k, v in sensitivity.items()}

        return sensitivity

    def _segment_circuit(
        self, circuit: QuantumCircuit
    ) -> list[tuple[int, int]]:
        """Segment a circuit at two-qubit gate boundaries.

        Each segment contains gates between consecutive two-qubit
        gates. This creates natural boundaries for sensitivity
        analysis.

        Args:
            circuit: The circuit to segment.

        Returns:
            List of (start_index, end_index) tuples for each segment.
        """
        if len(circuit.data) == 0:
            return [(0, 0)]

        segment_starts = [0]
        for i, instr in enumerate(circuit.data):
            if instr.operation.name in TWO_QUBIT_GATES and i > 0:
                segment_starts.append(i)

        segment_starts.append(len(circuit.data))

        segments = []
        for i in range(len(segment_starts) - 1):
            start = segment_starts[i]
            end = segment_starts[i + 1]
            if start < end:
                segments.append((start, end))

        if not segments:
            segments = [(0, len(circuit.data))]

        return segments

    def _allocate_shots(
        self, sensitivity: dict[int, float], total_shots: int
    ) -> dict[int, int]:
        """Allocate shots proportional to segment sensitivity.

        Segments with higher sensitivity get more shots, analogous
        to how mixed-precision training allocates more compute to
        high-gradient layers.

        Args:
            sensitivity: Mapping from segment index to sensitivity.
            total_shots: Total shot budget.

        Returns:
            Mapping from segment index to allocated shot count.
        """
        if not sensitivity:
            return {0: total_shots}

        total_sensitivity = sum(sensitivity.values())
        if total_sensitivity == 0:
            n = len(sensitivity)
            return {i: total_shots // n for i in range(n)}

        shots_per_segment = {}
        remaining = total_shots

        sorted_segs = sorted(sensitivity.keys(), key=lambda k: sensitivity[k], reverse=True)

        for i, seg_idx in enumerate(sorted_segs):
            proportion = sensitivity[seg_idx] / total_sensitivity
            allocated = int(proportion * total_shots)
            allocated = max(1, allocated)
            shots_per_segment[seg_idx] = allocated
            remaining -= allocated

        if remaining > 0 and sorted_segs:
            shots_per_segment[sorted_segs[0]] += remaining

        return shots_per_segment

    def _assign_noise_scales(
        self, sensitivity: dict[int, float], method: str
    ) -> dict[int, list[float]]:
        """Assign noise scale factors per segment based on sensitivity.

        High-sensitivity segments get 3+ scales (full ZNE with
        Richardson extrapolation). Medium-sensitivity segments get
        2 scales (linear extrapolation). Low-sensitivity segments
        get 1 scale (no mitigation).

        Args:
            sensitivity: Mapping from segment index to sensitivity.
            method: Mitigation method.

        Returns:
            Mapping from segment index to list of noise scales.
        """

        if not sensitivity:
            return {0: [1.0, 3.0]}

        if method == "pec":
            return {
                idx: [1.0] for idx in sensitivity
            }
        if method == "cdr":
            return {
                idx: [1.0, 2.0] for idx in sensitivity
            }

        scales_per_segment = {}
        values = sorted(sensitivity.values())

        if len(values) <= 1:
            return {idx: [1.0, 3.0] for idx in sensitivity}

        low_threshold = values[len(values) // 3] if len(values) >= 3 else values[0]
        high_threshold = values[2 * len(values) // 3] if len(values) >= 3 else values[-1]

        for idx, sens in sensitivity.items():
            if sens >= high_threshold:
                scales_per_segment[idx] = [1.0, 2.0, 3.0]
            elif sens >= low_threshold:
                scales_per_segment[idx] = [1.0, 2.0]
            else:
                scales_per_segment[idx] = [1.0]

        return scales_per_segment

    def _extrapolate_zne(
        self,
        plan: MitigationPlan,
        raw_values: list[float] | None = None,
    ) -> MitigationResult:
        """Extrapolate to zero noise using Richardson extrapolation.

        For 3+ noise scales, uses Richardson extrapolation:
            O(0) = Σᵢ cᵢ O(λᵢ)
        where cᵢ are the Richardson coefficients.

        For 2 scales, uses linear extrapolation:
            O(0) = 2·O(λ₁) - O(λ₂)

        For 1 scale, returns the raw value.

        Args:
            plan: The mitigation plan.
            raw_values: Measured values at each noise scale.

        Returns:
            A MitigationResult with the extrapolated value.
        """
        scales = plan.noise_scales

        if raw_values is None:
            raw_values = self._simulate_values(plan)

        if not scales or not raw_values:
            return MitigationResult(method=plan.method)

        if len(raw_values) == 1:
            return MitigationResult(
                mitigated_value=raw_values[0],
                raw_values=raw_values,
                noise_scales=scales,
                extrapolation_coefficients=[1.0],
                shots_used=plan.total_shots,
                method=plan.method,
            )

        if len(raw_values) == 2:
            if len(scales) >= 2:
                s1, s2 = scales[0], scales[1]
            else:
                s1, s2 = 1.0, 2.0

            denom = s1 - s2
            if abs(denom) < 1e-12:
                mitigated = raw_values[0]
            else:
                c1 = s1 / (s1 - s2)
                c2 = -s2 / (s1 - s2)
                mitigated = c1 * raw_values[0] + c2 * raw_values[1]

            return MitigationResult(
                mitigated_value=float(mitigated),
                raw_values=raw_values,
                noise_scales=scales[:2],
                extrapolation_coefficients=[c1, c2] if abs(denom) >= 1e-12 else [1.0, 0.0],
                shots_used=plan.total_shots,
                method=plan.method,
            )

        coeffs = self._richardson_coefficients(scales[:len(raw_values)])
        mitigated = sum(c * v for c, v in zip(coeffs, raw_values))

        return MitigationResult(
            mitigated_value=float(mitigated),
            raw_values=raw_values,
            noise_scales=scales[:len(raw_values)],
            extrapolation_coefficients=coeffs,
            shots_used=plan.total_shots,
            method=plan.method,
        )

    def _execute_pec(
        self, plan: MitigationPlan, raw_values: list[float] | None
    ) -> MitigationResult:
        """Execute PEC-style mitigation (placeholder).

        Full PEC requires gate characterization data from the device.
        This implementation returns raw values with metadata and marks
        the result as a placeholder.

        Args:
            plan: The mitigation plan.
            raw_values: Measured values.

        Returns:
            A MitigationResult with PEC metadata (placeholder=True).
        """
        import warnings

        warnings.warn(
            "PEC mitigation is a placeholder implementation that does not "
            "perform true probabilistic error cancellation. Results should "
            "not be relied upon for accuracy.",
            UserWarning,
            stacklevel=2,
        )

        if raw_values is None:
            raw_values = self._simulate_values(plan)

        return MitigationResult(
            mitigated_value=raw_values[0] if raw_values else 0.0,
            raw_values=raw_values,
            noise_scales=plan.noise_scales,
            shots_used=plan.total_shots,
            method="pec",
            placeholder=True,
        )

    def _execute_cdr(
        self, plan: MitigationPlan, raw_values: list[float] | None
    ) -> MitigationResult:
        """Execute CDR-style mitigation (placeholder).

        Full CDR requires classically simulable Clifford circuits.
        This implementation applies linear extrapolation as a rough
        approximation and marks the result as a placeholder.

        Args:
            plan: The mitigation plan.
            raw_values: Measured values.

        Returns:
            A MitigationResult with CDR metadata (placeholder=True).
        """
        import warnings

        warnings.warn(
            "CDR mitigation is a placeholder implementation that applies "
            "linear extrapolation rather than true Clifford data regression. "
            "Results should not be relied upon for accuracy.",
            UserWarning,
            stacklevel=2,
        )

        if raw_values is None:
            raw_values = self._simulate_values(plan)

        if len(raw_values) >= 2:
            mitigated = 2 * raw_values[0] - raw_values[1]
        else:
            mitigated = raw_values[0] if raw_values else 0.0

        return MitigationResult(
            mitigated_value=float(mitigated),
            raw_values=raw_values,
            noise_scales=plan.noise_scales,
            shots_used=plan.total_shots,
            method="cdr",
            placeholder=True,
        )

    def _simulate_values(self, plan: MitigationPlan) -> list[float]:
        """Simulate noisy expectation values from cost model.

        Uses the cost model's fidelity estimate to generate
        plausible noisy values at each noise scale. If no circuit
        is available, falls back to a default fidelity estimate.

        Args:
            plan: The mitigation plan.

        Returns:
            List of simulated expectation values.
        """
        import warnings

        warnings.warn(
            "No raw values provided; using cost model to simulate "
            "expectation values. Results are approximate and should "
            "not be relied upon for accuracy.",
            UserWarning,
            stacklevel=2,
        )

        if (
            hasattr(self, "_last_circuit")
            and self._last_circuit is not None
        ):
            base_fidelity = self.cost_model.estimate_fidelity(
                self._last_circuit
            ).total_fidelity
        else:
            base_fidelity = 0.85

        values = []
        for scale in plan.noise_scales:
            noisy = base_fidelity**scale
            values.append(float(noisy))
        return values

    @staticmethod
    def _richardson_coefficients(
        scales: list[float],
    ) -> list[float]:
        """Compute Richardson extrapolation coefficients.

        For noise scales λ₁, λ₂, ..., λₙ, the coefficients cᵢ
        satisfy: Σᵢ cᵢ · λᵢ^k = δ_{k,0} for k = 0, 1, ..., n-1

        This ensures the extrapolation cancels the first n-1
        noise terms.

        Args:
            scales: List of noise scale factors.

        Returns:
            List of Richardson coefficients.
        """
        n = len(scales)
        if n == 0:
            return []
        if n == 1:
            return [1.0]

        A = np.zeros((n, n))
        b = np.zeros(n)
        b[0] = 1.0

        for i in range(n):
            for j in range(n):
                A[i][j] = scales[j] ** i

        try:
            coeffs = np.linalg.solve(A, b)
            return [float(c) for c in coeffs]
        except np.linalg.LinAlgError:
            return [1.0 / n] * n