"""Tests for qc_compiler.scheduling module."""

import pytest
from qiskit import QuantumCircuit

from qc_compiler.cost_model import CostModel
from qc_compiler.scheduling import CoherenceAwareScheduler, ScheduleResult


class TestCoherenceAwareScheduler:
    def test_schedule_not_implemented(self):
        scheduler = CoherenceAwareScheduler(cost_model=CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            scheduler.schedule(qc)

    def test_schedule_methods(self):
        scheduler = CoherenceAwareScheduler(cost_model=CostModel())
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        with pytest.raises(NotImplementedError):
            scheduler._asap_schedule(qc)
        with pytest.raises(NotImplementedError):
            scheduler._alap_schedule(qc)
        with pytest.raises(NotImplementedError):
            scheduler._coherence_aware_schedule(qc)


class TestScheduleResult:
    def test_default_values(self):
        result = ScheduleResult()
        assert result.circuit is None
        assert result.idle_times == {}