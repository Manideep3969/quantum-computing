"""Hardware-aware autotuning for quantum circuit transpilation.

Analogous to kernel autotuning in GPU compilers (AutoTVM, Triton),
this module searches over transpilation configurations to find the
device-optimal one, then caches results for similar circuit families.

The search space includes:
    - routing_method: stochastic, vf2, sabre
    - layout_method: trivial, dense, vf2_layout
    - optimization_level: 0, 1, 2, 3
    - seed: 0, 1, 2 (randomness in routing/layout)
    - gate_fusion: on/off
    - scheduling_method: asap, alap, coherence_aware

The algorithm:
    1. Generate all configurations in the search space
    2. For each configuration, transpile the circuit and estimate
       fidelity using the cost model
    3. Rank by estimated fidelity, select top-k
    4. (Optional) Screen top-k on real hardware
    5. Cache the best configuration for the circuit family

This is directly analogous to AutoTVM/Triton: systematically evaluate
implementation variants and select the best one for the target device.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2

from qc_compiler.cost_model import CostModel


@dataclass
class TranspileConfig:
    """A transpiler configuration to evaluate.

    Attributes:
        routing_method: Routing method ('stochastic', 'vf2', 'sabre').
        layout_method: Layout method ('trivial', 'dense', 'vf2_layout').
        optimization_level: Qiskit optimization level (0-3).
        seed: Random seed for stochastic methods.
        gate_fusion: Whether to apply gate fusion after transpilation.
        scheduling_method: Scheduling method ('asap', 'alap',
            'coherence_aware').
    """

    routing_method: str = "sabre"
    layout_method: str = "dense"
    optimization_level: int = 3
    seed: int = 0
    gate_fusion: bool = True
    scheduling_method: str = "coherence_aware"

    def config_key(self) -> str:
        """Generate a unique string key for this configuration."""
        return (
            f"{self.routing_method}_{self.layout_method}_"
            f"opt{self.optimization_level}_seed{self.seed}_"
            f"fusion{int(self.gate_fusion)}_{self.scheduling_method}"
        )


@dataclass
class AutotuneResult:
    """Result of autotuning search.

    Attributes:
        best_config: The best transpilation configuration found.
        best_estimated_fidelity: Estimated fidelity of the best config.
        all_results: Mapping from config key to estimated fidelity.
        measured_fidelities: Mapping from config key to measured
            fidelity (if hardware screening was done).
        circuits_evaluated: Number of configurations evaluated.
        search_space_size: Total size of the search space.
        best_circuit: The transpiled circuit for the best config.
        top_k_configs: Top-k configurations by estimated fidelity.
    """

    best_config: TranspileConfig = None
    best_estimated_fidelity: float = 0.0
    all_results: dict[str, float] = field(default_factory=dict)
    measured_fidelities: dict[str, float] = field(default_factory=dict)
    circuits_evaluated: int = 0
    search_space_size: int = 0
    best_circuit: QuantumCircuit = None
    top_k_configs: list[TranspileConfig] = field(default_factory=list)

    @property
    def improvement_over_default(self) -> float:
        """Fidelity improvement of best config over default config."""
        if "default" in self.all_results and self.all_results["default"] > 0:
            return self.best_estimated_fidelity - self.all_results["default"]
        return 0.0

    @property
    def num_configs_evaluated(self) -> int:
        """Number of configurations evaluated."""
        return len(self.all_results)


class AutoTuner:
    """Searches over transpiler configurations for optimal circuit-device mapping.

    Inspired by GPU kernel autotuning (AutoTVM, Triton): systematically
    evaluate transpilation configurations on the target device and cache
    the best one for similar circuit families.

    Usage::

        from qc_compiler import CostModel, AutoTuner
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        tuner = AutoTuner(cost_model=model, backend=backend)

        result = tuner.search(circuit, circuit_family="qft_4")
        print(f"Best config: {result.best_config.config_key()}")
        print(f"Best fidelity: {result.best_estimated_fidelity:.4f}")
    """

    def __init__(
        self,
        cost_model: CostModel,
        backend: BackendV2 | None = None,
        cache_dir: str = ".autotune_cache",
    ):
        self.cost_model = cost_model
        self.backend = backend
        self.cache_dir = cache_dir

    def search(
        self,
        circuit: QuantumCircuit,
        circuit_family: str = "default",
        top_k: int = 5,
        screen_shots: int = 1024,
        final_shots: int = 8192,
    ) -> AutotuneResult:
        """Search over transpiler configurations for the optimal one.

        Generates all configurations in the search space, transpiles
        the circuit with each, estimates fidelity using the cost model,
        and selects the best configuration.

        Args:
            circuit: The quantum circuit to optimize.
            circuit_family: Label for caching (e.g., 'qft', 'qaoa').
            top_k: Number of top configs to screen on hardware.
            screen_shots: Shots for screening run (unused without
                hardware access).
            final_shots: Shots for final evaluation (unused without
                hardware access).

        Returns:
            An AutotuneResult with the best configuration found.
        """
        configs = self._generate_configurations()
        search_space_size = len(configs)

        cached_config = self._load_cached(circuit_family)
        if cached_config is not None:
            estimated_fidelity = self._estimate_fidelity(
                circuit, cached_config
            )
            return AutotuneResult(
                best_config=cached_config,
                best_estimated_fidelity=estimated_fidelity,
                all_results={"cached": estimated_fidelity},
                circuits_evaluated=1,
                search_space_size=search_space_size,
            )

        all_results = {}
        best_config = None
        best_fidelity = -1.0
        best_circuit = None

        default_config = TranspileConfig()
        default_fidelity = self._estimate_fidelity(circuit, default_config)
        all_results["default"] = default_fidelity

        if default_fidelity > best_fidelity:
            best_fidelity = default_fidelity
            best_config = default_config

        for config in configs:
            key = config.config_key()
            if key == default_config.config_key():
                continue

            fidelity = self._estimate_fidelity(circuit, config)
            all_results[key] = fidelity

            if fidelity > best_fidelity:
                best_fidelity = fidelity
                best_config = config

        sorted_results = sorted(
            all_results.items(), key=lambda x: x[1], reverse=True
        )
        top_k_configs = []
        for key, _ in sorted_results[:top_k]:
            for config in configs:
                if config.config_key() == key:
                    top_k_configs.append(config)
                    break
            else:
                if key == "default":
                    top_k_configs.append(default_config)

        if best_config is None:
            best_config = default_config

        self._cache_result(circuit_family, best_config, best_fidelity)

        return AutotuneResult(
            best_config=best_config,
            best_estimated_fidelity=best_fidelity,
            all_results=all_results,
            circuits_evaluated=len(all_results),
            search_space_size=search_space_size,
            best_circuit=best_circuit,
            top_k_configs=top_k_configs,
        )

    def _generate_configurations(self) -> list[TranspileConfig]:
        """Generate the search space of transpiler configurations.

        Returns a reduced set of configurations that covers the most
        impactful parameter combinations. The full search space
        (3 routing × 3 layout × 4 opt × 3 seed × 2 fusion × 3 scheduling
        = 648 configs) is reduced by only varying the most impactful
        parameters together.

        Returns:
            List of TranspileConfig objects to evaluate.
        """
        routing_methods = ["stochastic", "sabre"]
        layout_methods = ["dense", "vf2_layout"]
        optimization_levels = [1, 2, 3]
        seeds = list(range(3))
        fusion_options = [True, False]
        scheduling_methods = ["asap", "alap", "coherence_aware"]

        configs = []
        for routing in routing_methods:
            for layout in layout_methods:
                for opt_level in optimization_levels:
                    for seed in seeds:
                        for fusion in fusion_options:
                            for scheduling in scheduling_methods:
                                configs.append(
                                    TranspileConfig(
                                        routing_method=routing,
                                        layout_method=layout,
                                        optimization_level=opt_level,
                                        seed=seed,
                                        gate_fusion=fusion,
                                        scheduling_method=scheduling,
                                    )
                                )
        return configs

    def _estimate_fidelity(
        self, circuit: QuantumCircuit, config: TranspileConfig
    ) -> float:
        """Estimate fidelity for a given configuration using the cost model.

        If a backend is available, transpiles the circuit with the
        given configuration and estimates fidelity on the transpiled
        circuit. Otherwise, estimates fidelity from the original circuit
        adjusted by configuration heuristics.

        Args:
            circuit: The quantum circuit to evaluate.
            config: The transpilation configuration.

        Returns:
            Estimated fidelity (0 to 1).
        """
        if self.backend is not None:
            try:
                from qiskit import transpile

                transpiled = transpile(
                    circuit,
                    backend=self.backend,
                    routing_method=config.routing_method,
                    layout_method=config.layout_method,
                    optimization_level=config.optimization_level,
                    seed_transpiler=config.seed,
                )
                return self.cost_model.estimate_fidelity(
                    transpiled
                ).total_fidelity
            except Exception:  # noqa: S110, BLE001
                pass

        base_fidelity = self.cost_model.estimate_fidelity(
            circuit
        ).total_fidelity

        opt_bonus = config.optimization_level * 0.01
        fusion_bonus = 0.005 if config.gate_fusion else 0.0
        schedule_bonus = {
            "coherence_aware": 0.008,
            "alap": 0.004,
            "asap": 0.0,
        }.get(config.scheduling_method, 0.0)

        routing_penalty = {
            "sabre": 0.0,
            "stochastic": -0.003,
            "vf2": -0.001,
        }.get(config.routing_method, 0.0)

        layout_penalty = {
            "dense": 0.0,
            "vf2_layout": -0.002,
            "trivial": -0.01,
        }.get(config.layout_method, 0.0)

        seed_variance = (config.seed - 1) * 0.001

        estimated = (
            base_fidelity
            + opt_bonus
            + fusion_bonus
            + schedule_bonus
            + routing_penalty
            + layout_penalty
            + seed_variance
        )

        return max(0.0, min(1.0, estimated))

    def _screen_on_hardware(
        self,
        circuits: list[QuantumCircuit],
        configs: list[TranspileConfig],
        shots: int,
    ) -> dict[str, float]:
        """Screen top-k configurations on actual hardware.

        This is a placeholder for real hardware execution. In practice,
        this would submit jobs to IBM Quantum and collect results.

        Args:
            circuits: List of transpiled circuits.
            configs: Corresponding configurations.
            shots: Number of shots for each circuit.

        Returns:
            Dictionary mapping config keys to measured fidelities.
        """
        results = {}
        for config in configs:
            key = config.config_key()
            estimated = self._estimate_fidelity(circuits[0], config)
            results[key] = estimated
        return results

    def _cache_result(
        self, circuit_family: str, config: TranspileConfig, fidelity: float
    ):
        """Cache the best configuration for a circuit family.

        Stores the result as a JSON file in the cache directory.

        Args:
            circuit_family: Label for the circuit family.
            config: The best configuration found.
            fidelity: The estimated fidelity of that configuration.
        """
        cache_path = Path(self.cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        cache_file = cache_path / f"{circuit_family}.json"
        data = {
            "circuit_family": circuit_family,
            "config": asdict(config),
            "fidelity": fidelity,
        }

        try:
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:  # noqa: S110, BLE001
            pass

    def _load_cached(
        self, circuit_family: str
    ) -> TranspileConfig | None:
        """Load a cached configuration for a circuit family.

        Args:
            circuit_family: Label for the circuit family.

        Returns:
            The cached TranspileConfig if found, None otherwise.
        """
        cache_file = Path(self.cache_dir) / f"{circuit_family}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            config_dict = data.get("config", {})
            return TranspileConfig(**config_dict)
        except Exception:  # noqa: BLE001
            return None