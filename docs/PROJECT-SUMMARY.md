# qc-compiler — Project Summary

**A plain-language record of everything done on this project so far.**

Last updated: October 2026 · Repository: `Manideep3969/quantum-computing` · Version: 0.1.0

---

## 1. What this project is

**qc-compiler** is an open-source Python framework for optimizing quantum circuits before they run on real quantum hardware. It takes a circuit written in Qiskit and applies six hardware-aware optimizations:

| # | Module | What it does | Real-world analogy |
|---|--------|-------------|-------------------|
| 1 | `cost_model.py` | Estimates how much error a circuit will accumulate on a specific device | A performance model for a GPU kernel |
| 2 | `fusion.py` | Merges chains of single-qubit gates into fewer gates | Kernel fusion (e.g. conv+bn+relu) |
| 3 | `cutting.py` | Splits circuits too large for one device into smaller pieces | Model parallelism across GPUs |
| 4 | `mitigation.py` | Plans error-mitigation strategies (ZNE, PEC, CDR) | Mixed-precision training |
| 5 | `scheduling.py` | Reorders gates to reduce time spent idle on fragile qubits | Memory-bandwidth optimization |
| 6 | `batching.py` | Groups independent circuits for shared execution | Batched inference |

Plus a top-level pipeline (`transpiler.py`) that composes all six, and an `autotuning.py` module that searches 216 transpiler configurations to find the best one for a given circuit/device pair.

The framework is the code basis for a planned research paper: *"Hardware-Aware Quantum Circuit Optimization: Bridging Classical Compilation Techniques to NISQ Devices."*

---

## 2. Where it stands now

| Metric | Value |
|---|---|
| Python modules | 10 (`src/qc_compiler/`), ~4,460 lines |
| Public API exports | 34 |
| Tests | **365, all passing** (up from 234 at v0.1.0) |
| Lint | `ruff` — clean |
| CI | GitHub Actions — Python 3.10 / 3.11 / 3.12 / 3.13, all green |
| Open issues | **0** |
| Open pull requests | **0** |
| Merged PRs (all time) | 54 |
| Closed issues (all time) | 45 |

---

## 3. Phase 1 — Open-source readiness

Before the bug campaign, the repository was prepared for public release:

- **Community files:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1), `SECURITY.md`, `NOTICE`
- **GitHub templates:** issue templates (bug/feature), pull-request template, `config.yml`
- **Automation:** GitHub Actions CI (lint + test matrix + coverage), PyPI publish workflow on release
- **Dependabot:** enabled for security alerts only — version-bump PRs disabled (`open-pull-requests-limit: 0`)
- **Quality gates:** `pre-commit` hooks (ruff + standard checks), coverage threshold of 90% in `pyproject.toml`
- **Packaging fixes:** `[project.urls]` added; `classifiers`/`dependencies` moved to correct TOML scope; `.gitignore` fixed
- **README:** CI / license / Python-version badges

---

## 4. Phase 2 — The bug-fix campaign (29 tracked issues, 28 fixes)

### How each fix was done

Every issue followed the same disciplined loop:

```
Read issue → create branch (one per issue) → make the fix
→ add regression tests → run full suite + ruff
→ commit with "fix(#N): ..." → push → open PR
→ wait for 4-version CI to pass → squash/merge → delete branch
```

No fix was merged without a test that would catch the bug coming back.

### P0 — Critical (3 issues)

| # | Bug | What was wrong | The fix | PR |
|---|-----|----------------|---------|----|
| 32 | ALAP schedule was identical to ASAP | The "as late as possible" scheduler did a forward pass only, so it produced the same result as ASAP | Implemented a true reverse pass that computes each gate's latest start, then emits gates sorted by it | #62 |
| 34 | Transpiler discarded all but the first subcircuit after cutting | Cutting produced multiple subcircuits but the pipeline kept only `subcircuits[0]`, losing the rest of the work | The pipeline now keeps every subcircuit, runs scheduling/mitigation on each, and combines fidelities (divided by sampling overhead) | #63 |
| 35 | Decoherence error used the wrong formula | Code used `2^(-t/T₂)` but the physics and the paper require `exp(-t/T₂)`. This inflates every fidelity estimate by a factor of ln 2 ≈ 0.693 | Replaced with `math.exp(-t/T₂)` in three places (`cost_model` twice, `cutting` once); added tests that pin the exponential form | #112 |

> **Note on #35:** an earlier session had reported this fixed, but the code was never actually changed. A final audit caught it — see Section 5.

### P1 — High (11 tracked, 10 fixed — #40 was a duplicate)

| # | Bug | What was wrong | The fix | PR |
|---|-----|----------------|---------|----|
| 36 | `TWO_QUBIT_GATES` defined inconsistently in 5 modules | Each module had its own copy, with different gate lists — some modules missed gates like `rxx`, `crz` | One canonical set in `utils.py`, imported everywhere; tests assert its contents | #84 |
| 37 | Multi-qubit gate fusion corrupted circuits | Chains were replaced sequentially; once one replacement shifted instruction indices, later replacements hit the wrong gates | Single-pass `_replace_all_chains` builds the output from the original index space | #85 |
| 38 | `compute_idle_fraction` undercounted | Counted gates with `count_ops()`, treating a 2-qubit gate as one busy slot instead of two | Counts `len(instr.qubits)` per instruction | #86 |
| 39 | `AutotuneResult.best_circuit` was always `None` | First-order cause found later (see Section 5); the immediate fix populated the field on the main search path | Populated `best_circuit` from the best config's transpiled circuit | #87, #113 |
| 40 | `optimize_batch` used original circuits | Duplicate of #34 — already fixed | Closed as duplicate | — |
| 41 | Cost model ignored the layout | Used one average error rate for all qubits, ignoring that physical qubits differ | Added per-qubit and per-pair fidelity lookup keyed by layout; `estimate_gate_error` now walks instructions | #92 |
| 42 | PEC/CDR returned wrong results silently | Placeholder implementations returned numbers that looked real | Added a `placeholder=True` flag, `UserWarning`s explaining the results are not reliable, and docs | #93 |
| 43 | README Quick Start had wrong parameter names | Example used `gate_fusion=`, `scheduling_method=` etc. — would raise `TypeError` | Corrected all examples to `fusion=`, `scheduling=`, `mitigation=`, `cutting=`; fixed `CostModel` and result-field examples too | #94 |
| 44 | `reconstruct()` was mathematically incorrect | Simple averaging loses the sign/coefficient information required by quasi-probability decomposition | Added `UserWarning` + docstring marking it as a placeholder and pointing to `circuit_knitting` for real QPD | #95 |
| 54 | Paper claimed benchmarks that don't exist | The outline presented projected numbers ("1.3–2.8× depth reduction") as measured results and described unimplemented features (crosstalk, 2-qubit absorption fusion, ILP scheduling) | Added a PROPOSAL status banner, reframed all numbers as targets, marked unimplemented features as future work throughout | #114 |
| 55 | No unitary-equivalence tests | Nothing verified that optimized circuits compute the same unitary as the input | Added `Operator`-based equivalence tests for all scheduling methods, fusion, and cutting partition correctness | #96 |

### P2 — Medium (10 issues)

| # | Bug | What was wrong | The fix | PR |
|---|-----|----------------|---------|----|
| 45 | Structural batching treated same-size circuits as overlapping | It compared virtual qubit sets (`{0,1,2}` vs `{0,1,2}` always overlap), so two 3-qubit circuits could never be batched on a 127-qubit device | Tracks cumulative qubit count against `max_qubits` instead | #97 |
| 46 | Autotuning docs said 648 configs, code made 216 | Docstring/paper described a 3×3×4×3×2×3 space; code implements 2×2×3×3×2×3 | Corrected docstring and paper outline; added tests asserting the dimension sizes | #98 |
| 47 | `mitigation='adaptive'` silently became `'zne'` | The config default was converted before reaching the mitigation module, making 'adaptive' unreachable | `AdaptiveErrorMitigation` now accepts `'adaptive'` as a first-class method (resolves to ZNE internally); original string preserved in results | #99 |
| 48 | `_simulate_values` used hardcoded fidelity 0.85 | Synthetic values ignored the device; no warning | Uses the cost model's fidelity for the actual circuit; emits `UserWarning` | #100 |
| 49 | Silent exception swallowing in backend extraction | `except: pass` made empty device data impossible to debug | Logs a warning per failed property (`T1`, `T2`, readout error) | #101 |
| 50 | Default constants duplicated across modules | `0.0005`, `0.01`, `0.015`, `150e-6`, `50e-9`, `300e-9` hardcoded in up to 4 files | Centralized as named constants in `utils.py`, imported elsewhere | #102 |
| 51 | `_compute_core_hash` used non-deterministic `hash()` | Python salts `hash()` per process — same circuit hashed differently across sessions, breaking caching | Replaced with `hashlib.sha256` | #103 |
| 52 | Gate-error averages recomputed per gate | O(N) dict scans for every gate in the circuit during fidelity estimation | Cached on first call in `CostModel` | #104 |
| 56 | Measurement error assumed all qubits measured | When a circuit had no measurements, it assumed all qubits were measured, inflating error | Returns an empty list; measurement error is correctly 0 | #105 |
| 57 | `_get_gate_duration` ignored calibration | Fixed 1/3 model even though `gate_lengths` data was available | Looks up actual durations and normalizes to abstract units by average single-qubit time | #106 |

### P3 — Low (5 issues)

| # | Bug | What was wrong | The fix | PR |
|---|-----|----------------|---------|----|
| 53 | Unused core dependencies | `cirq`, `pennylane`, `qiskit-aer` were required to install but never imported | Moved to optional extras: `frameworks` and `simulator` | #107 |
| 58 | Type annotations missing `\| None` | 10 dataclass fields defaulted to `None` but were typed non-nullable | Added `\| None` across 4 files | #108 |
| 59 | No input validation | `optimization_level=5`, invalid methods, `None` circuits, and empty circuits failed deep inside pipelines | `__post_init__` validation in `TranspileConfig` and `OptimizerConfig`; early checks in `optimize()` | #109 |
| 60 | O(n²) batching lookup | `circuits.index(c)` inside a loop | `{id(circuit): index}` dict for O(1) lookups | #110 |
| 61 | `find_bit` compatibility risk | `circuit.find_bit(q).index` used in 24 places, at risk of Qiskit deprecation | Added `qubit_index()` / `clbit_index()` wrappers in `utils.py`; single migration point if the API changes | #111 |

---

## 5. The three surprises (why the final audit mattered)

At the end of the campaign, all fixes appeared merged — but the GitHub issues were all still open, because PR bodies didn't use the `Fixes #N` keyword. Instead of bulk-closing them, every claimed fix was audited against the actual code. That found three genuine problems:

### Surprise 1 — Issue #35 was never actually fixed

The prior session's record said "P0 bugs #32–#35 all fixed and merged." The audit found the code still contained `2.0 ** (-total_time / t2)` — the exact bug. It was re-fixed properly in PR #112, with tests that would fail if the formula ever regresses.

**Lesson:** "merged" does not mean "fixed." Verify against the code, not the changelog.

### Surprise 2 — Issue #39's real root cause was elsewhere

The first fix populated `best_circuit` on the main search path, but the field was *still* `None` whenever a cached config hit, and the search behaved strangely. Digging in revealed the deeper cause:

- The autotuner's search space used transpiler plugin names that **don't exist in Qiskit 2.x**: `'stochastic'` routing and `'vf2_layout'` layout.
- Every transpile call raised `TranspilerError`, which was caught by `except: pass` — silently swallowed.
- So *no* config ever produced a transpiled circuit, and `best_circuit` was always `None`.

The fix (PR #113): valid plugin names (`sabre`/`basic` routing, `dense`/`trivial` layout), a warning log on failure, cache-path population, and removal of a stale checked-in cache file that pinned the invalid config. Two candidate replacements were tested and rejected with data: `lookahead` routing is ~190× slower on 127-qubit devices (188 s vs 1.7 s for the full search), and `vf2` is no longer a routing plugin.

**Lesson:** A silent `except: pass` can disguise a total feature failure as a minor one.

### Surprise 3 — The paper was overclaiming

The paper outline read like a finished results paper: "Our results demonstrate 1.3–2.8× reduction... benchmarks on IBM Quantum hardware." None of it had been run — `results/` and `benchmarks/` contained only `.gitkeep` placeholders. PR #114 added a proposal-status banner, converted all numbers to explicit targets, and marked unimplemented features (crosstalk modeling, two-qubit absorption fusion, true QPD reconstruction, real PEC/CDR, ILP scheduling) as future work in both the outline and Section 12.4.

**Lesson:** A proposal that reads like a results paper is a credibility risk.

---

## 6. Quality gates

Every change passed through all of these before merging:

1. **Regression test** written first (or with the fix) — the bug can't silently return
2. **Full test suite** — 365 tests, ~11 s locally
3. **`ruff` lint** — zero warnings, enforced in CI and pre-commit
4. **Four-version CI matrix** — Python 3.10, 3.11, 3.12, 3.13
5. **PR review body** documenting the fix and referencing the issue

Test count grew from 234 (v0.1.0) to **365** during this work.

---

## 7. How to verify any of this

```bash
# Clone and install
git clone https://github.com/Manideep3969/quantum-computing
cd quantum-computing
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# Run everything
pytest tests/ -v          # 365 passed
ruff check src/ tests/    # All checks passed!

# Try the framework
python -c "
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qc_compiler import QCompiler, OptimizerConfig

qc = QuantumCircuit(3)
for _ in range(4):
    qc.h(0); qc.rz(0.3, 0); qc.sx(0)   # fusible chain on qubit 0
qc.cx(0, 1); qc.cx(1, 2)

compiler = QCompiler(backend=FakeBrisbane())
config = OptimizerConfig(fusion=True, scheduling='none',
                         mitigation='none', cutting=False)
result = compiler.optimize(qc, config=config)

print('passes applied:', result.passes_applied)
print('depth:', result.original_circuit.depth(), '->',
      result.optimized_circuit.depth())
print('unitary preserved:',
      Operator(qc).equiv(Operator(result.optimized_circuit)))
"
```

Each fix can be traced: `git log --oneline --grep="#35"` etc. Each issue on GitHub has a closing comment pointing at its PR.

---

## 8. What's next

The framework is complete and correct per its tests. The remaining work is **research validation**, not bug-fixing:

- **Run the planned experiments** in `docs/notes/06-paper-outline.md` Section 11 (gate fusion, cutting, mitigation, scheduling, batching, autotuning) on IBM Quantum hardware or noisy simulators
- **Populate `results/`** with real measurements (currently placeholders)
- **Implement the marked future work** if the paper needs it: crosstalk modeling, two-qubit fusion, full QPD reconstruction, real PEC/CDR, exact scheduling solver
- **Write the paper** using only measured results — the outline now makes the target/actual boundary explicit

---

## 9. One-paragraph summary you can repeat

> Over the past sessions, we took `qc-compiler` — a six-module quantum circuit optimization framework — from a private alpha to an open-source-ready project. We added all community files, CI for four Python versions, and security-only Dependabot. We then worked through 29 tracked issues, fixing 28 of them (one was a duplicate), each on its own branch/PR with a regression test: three critical (a wrong decoherence formula, a scheduler that wasn't actually late-as-possible, and a pipeline that dropped subcircuits after cutting), ten high, ten medium, and five low severity. Every fix was verified against the code, which caught that one "already fixed" bug had never actually been changed, that the autotuner's search space used plugin names that don't exist in modern Qiskit (silently failing every transpile), and that the paper outline was presenting projected targets as measured results. The repository now has 365 passing tests, clean lint, zero open issues, and a paper outline that honestly separates what is implemented from what is planned.
