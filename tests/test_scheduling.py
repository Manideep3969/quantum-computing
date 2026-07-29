"""Tests for qc_compiler.scheduling module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.scheduling import CoherenceAwareScheduler, ScheduleResult


class TestScheduleResult:
    def test_default_values(self):
        result = ScheduleResult()
        assert result.circuit is None
        assert result.idle_times == {}
        assert result.estimated_fidelity_asap == 0.0
        assert result.estimated_fidelity_alap == 0.0
        assert result.estimated_fidelity_optimized == 0.0
        assert result.method == "coherence_aware"
        assert result.depth_asap == 0
        assert result.depth_alap == 0
        assert result.depth_optimized == 0

    def test_idle_time_total(self):
        result = ScheduleResult(idle_times={0: 1e-6, 1: 2e-6, 2: 3e-6})
        assert abs(result.idle_time_total - 6e-6) < 1e-15

    def test_idle_time_avg(self):
        result = ScheduleResult(idle_times={0: 1e-6, 1: 2e-6, 2: 3e-6})
        assert abs(result.idle_time_avg - 2e-6) < 1e-15

    def test_idle_time_avg_empty(self):
        result = ScheduleResult(idle_times={})
        assert result.idle_time_avg == 0.0

    def test_depth_reduction_pct(self):
        result = ScheduleResult(depth_asap=10, depth_optimized=7)
        assert abs(result.depth_reduction_pct - 30.0) < 1e-10

    def test_depth_reduction_pct_zero(self):
        result = ScheduleResult(depth_asap=0, depth_optimized=0)
        assert result.depth_reduction_pct == 0.0

    def test_fidelity_improvement(self):
        result = ScheduleResult(
            estimated_fidelity_asap=0.85,
            estimated_fidelity_optimized=0.90,
        )
        assert abs(result.fidelity_improvement - 0.05) < 1e-10


class TestCoherenceAwareSchedulerNoBackend:
    """Tests without a backend (default model)."""

    @pytest.fixture
    def scheduler(self):
        return CoherenceAwareScheduler(cost_model=CostModel())

    def test_schedule_asap(self, scheduler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = scheduler.schedule(qc, method="asap")
        assert isinstance(result, ScheduleResult)
        assert result.method == "asap"
        assert result.circuit is not None
        assert result.depth_asap > 0

    def test_schedule_alap(self, scheduler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = scheduler.schedule(qc, method="alap")
        assert result.method == "alap"
        assert result.circuit is not None

    def test_schedule_coherence_aware(self, scheduler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = scheduler.schedule(qc, method="coherence_aware")
        assert result.method == "coherence_aware"
        assert result.circuit is not None

    def test_schedule_invalid_method(self, scheduler):
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError, match="Unknown scheduling method"):
            scheduler.schedule(qc, method="invalid")

    def test_schedule_empty_circuit(self, scheduler):
        qc = QuantumCircuit(4)
        result = scheduler.schedule(qc)
        assert result.depth_asap == 0
        assert result.depth_optimized == 0

    def test_schedule_preserves_gates(self, scheduler):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.h(1)
        qc.h(2)
        qc.cx(0, 1)
        qc.cx(1, 2)
        result = scheduler.schedule(qc)
        original_ops = qc.count_ops()
        scheduled_ops = result.circuit.count_ops()
        for gate, count in original_ops.items():
            assert scheduled_ops.get(gate, 0) == count

    def test_schedule_ghz(self, scheduler, ghz_circuit):
        result = scheduler.schedule(ghz_circuit)
        assert result.estimated_fidelity_asap > 0
        assert result.estimated_fidelity_optimized > 0

    def test_schedule_qaoa(self, scheduler, qaoa_circuit):
        result = scheduler.schedule(qaoa_circuit)
        assert result.estimated_fidelity_asap > 0
        assert result.idle_time_total >= 0

    def test_idle_times_computed(self, scheduler):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        result = scheduler.schedule(qc)
        assert len(result.idle_times) == 3
        for q, t in result.idle_times.items():
            assert t >= 0

    def test_asap_fidelity_matches(self, scheduler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = scheduler.schedule(qc, method="asap")
        assert abs(result.estimated_fidelity_asap - result.estimated_fidelity_optimized) < 1e-10

    def test_alap_fidelity_matches(self, scheduler):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        result = scheduler.schedule(qc, method="alap")
        assert abs(result.estimated_fidelity_alap - result.estimated_fidelity_optimized) < 1e-10

    def test_all_methods_same_gate_count(self, scheduler):
        qc = QuantumCircuit(3)
        qc.h(0)
        for i in range(1, 3):
            qc.cx(0, i)
        qc.rz(0.5, 0)
        qc.rz(0.3, 1)

        total_orig = sum(qc.count_ops().values())
        for method in ("asap", "alap", "coherence_aware"):
            result = scheduler.schedule(qc, method=method)
            total_sched = sum(result.circuit.count_ops().values())
            assert total_sched == total_orig


class TestCoherenceAwareSchedulerWithBackend:
    """Tests with FakeBrisbane backend."""

    @pytest.fixture
    def scheduler_with_backend(self):
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        backend = FakeBrisbane()
        model = CostModel(backend=backend)
        return CoherenceAwareScheduler(cost_model=model)

    def test_schedule_with_real_backend(self, scheduler_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = scheduler_with_backend.schedule(qc)
        assert result.estimated_fidelity_asap > 0
        assert result.estimated_fidelity_optimized > 0

    def test_idle_times_with_real_device(self, scheduler_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = scheduler_with_backend.schedule(qc)
        assert len(result.idle_times) == 4
        for t in result.idle_times.values():
            assert t >= 0

    def test_t2_priority_affects_scheduling(self, scheduler_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        qc.h(1)
        qc.cx(0, 1)
        qc.cx(1, 2)
        qc.h(3)
        result = scheduler_with_backend.schedule(qc)
        assert result.method == "coherence_aware"
        assert result.circuit is not None

    def test_ghz_with_backend(self, scheduler_with_backend):
        qc = QuantumCircuit(4)
        qc.h(0)
        for i in range(1, 4):
            qc.cx(0, i)
        result = scheduler_with_backend.schedule(qc)
        assert result.estimated_fidelity_optimized > 0


class TestComputeIdleTimes:
    """Tests for idle time computation."""

    @pytest.fixture
    def scheduler(self):
        return CoherenceAwareScheduler(cost_model=CostModel())

    def test_empty_circuit_idle_times(self, scheduler):
        qc = QuantumCircuit(3)
        idle = scheduler._compute_idle_times(qc)
        assert len(idle) == 3
        assert all(v == 0.0 for v in idle.values())

    def test_single_gate_idle_times(self, scheduler):
        qc = QuantumCircuit(2)
        qc.h(0)
        idle = scheduler._compute_idle_times(qc)
        assert idle[0] >= 0
        assert idle[1] >= 0

    def test_bell_circuit_idle_times(self, scheduler, bell_circuit):
        idle = scheduler._compute_idle_times(bell_circuit)
        assert len(idle) == 2
        assert all(v >= 0 for v in idle.values())


class TestGateDuration:
    """Tests for gate duration model."""

    @pytest.fixture
    def scheduler(self):
        return CoherenceAwareScheduler(cost_model=CostModel())

    def test_single_qubit_gate_duration(self, scheduler):
        assert scheduler._get_gate_duration("h", [0]) == 1
        assert scheduler._get_gate_duration("sx", [0]) == 1
        assert scheduler._get_gate_duration("rz", [0]) == 1

    def test_two_qubit_gate_duration(self, scheduler):
        assert scheduler._get_gate_duration("cx", [0, 1]) == 3
        assert scheduler._get_gate_duration("ecr", [0, 1]) == 3

    def test_measurement_duration(self, scheduler):
        assert scheduler._get_gate_duration("measure", [0]) == 1