"""hprc/pin_tuning/sitecustomize.py -- the same kernel choices in every parser server.

WHY
---
Several kernels tune themselves the first time they run in a server: they run
each of their options, time them, and keep the fastest. Two options give the
same result to many decimal places but not to the last bit, because they add
numbers in a different order. Timing on a shared machine is noisy, so two
servers started separately can keep different options, and the parser, which
samples its words, then writes a different reply to the same prompt from the
first near-tie on. Measured on FASTER, 12 October 2026: a server asked twice
gave the same reply 3 of 3 times; two servers started separately gave different
replies in 10 of 11 DEV plans (hprc/compare_plans.py) and 0 of 3 in the probe
(hprc/repeat_probe.py), with or without --enforce-eager.

The tuning steps (read in the code of these versions):
  * Triton 3.7.1, triton/runtime/autotuner.py: Autotuner.run benchmarks every
    pruned config with Autotuner._bench and keeps builtins.min(timings).
    vLLM's bundled FLA kernels (the GDN layers that read the prompt) use it.
  * torch 2.13 Inductor, torch/_inductor/runtime/triton_heuristics.py:
    CachingAutotuner.autotune_to_one_config keeps builtins.min of
    CachingAutotuner.bench over its launchers; the combo-kernel tuning keeps a
    trial only if its bench time is lower.

WHAT THIS DOES
--------------
Each option is still run once as before, so an option that fails (out of
resources, too many spilled registers) still counts as failed. But every option
that runs is given the same time, 1.0. Both tuners then keep the FIRST working
option in their own list, whose order is fixed in the code. So every server
makes the same choices, however the timings came out.

It is loaded only by the parser servers: hprc/vine_hprc.py puts this folder on
PYTHONPATH (and sets VINE_PIN_TUNING=1) in their environment alone. Nothing
else, and no installed package, is changed. Each Python process that loads
one of the two modules says so on stderr, which goes to the server's log:
"[vine-pin pid N] Triton tuning pinned" / "... torch.compile tuning pinned".
"""
import importlib.abc
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_INF = float("inf")


def _say(msg):
    try:
        sys.stderr.write(f"[vine-pin pid {os.getpid()}] {msg}\n")
        sys.stderr.flush()
    except Exception:  # noqa: BLE001
        pass


def _pin_triton(module):
    Autotuner = getattr(module, "Autotuner", None)
    orig = getattr(Autotuner, "_bench", None)
    if orig is None:
        _say("NOT PINNED: triton.runtime.autotuner.Autotuner._bench is not there in this Triton")
        return
    if getattr(orig, "_vine_pinned", False):
        return

    def _bench(self, *args, config, **meta):
        t = orig(self, *args, config=config, **meta)
        values = list(t) if isinstance(t, (list, tuple)) else [t]
        if any(v == _INF for v in values):
            return t                                   # a failed option stays failed
        return [1.0] * len(values) if isinstance(t, (list, tuple)) else 1.0

    _bench._vine_pinned = True
    Autotuner._bench = _bench
    _say("Triton tuning pinned (the first working option of each kernel is kept)")


def _pin_inductor(module):
    CachingAutotuner = getattr(module, "CachingAutotuner", None)
    orig = getattr(CachingAutotuner, "bench", None)
    if orig is None:
        _say("NOT PINNED: CachingAutotuner.bench is not there in this torch")
        return
    if getattr(orig, "_vine_pinned", False):
        return

    def bench(self, launcher, *args, **kwargs):
        t = orig(self, launcher, *args, **kwargs)
        return t if t == _INF else 1.0

    bench._vine_pinned = True
    CachingAutotuner.bench = bench
    _say("torch.compile tuning pinned (the first working option of each kernel is kept)")


_TARGETS = {"triton.runtime.autotuner": _pin_triton,
            "torch._inductor.runtime.triton_heuristics": _pin_inductor}


class _PinWhenImported(importlib.abc.MetaPathFinder):
    """Patch each target module right after it is first imported, in whatever
    process imports it (so nothing heavy is imported here)."""

    def find_spec(self, name, path=None, target=None):
        if name not in _TARGETS:
            return None
        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            spec = finder.find_spec(name, path, target)
            if spec is not None:
                break
        else:
            return None
        loader = spec.loader
        if loader is None or not hasattr(loader, "exec_module"):
            return spec
        run_module = loader.exec_module

        def exec_module(module, _run=run_module, _name=name):
            _run(module)
            try:
                _TARGETS[_name](module)
            except Exception as e:  # noqa: BLE001
                _say(f"NOT PINNED: {_name}: {e!r}")

        loader.exec_module = exec_module
        return spec


def _install():
    if os.environ.get("VINE_PIN_TUNING") != "1":
        return
    for name, pin in _TARGETS.items():
        if name in sys.modules:               # imported already: patch now
            pin(sys.modules[name])
    if not any(isinstance(f, _PinWhenImported) for f in sys.meta_path):
        sys.meta_path.insert(0, _PinWhenImported())


def _chain_other_sitecustomize():
    """A sitecustomize further down the path would be hidden by this one: run it too."""
    for p in sys.path:
        if not p or os.path.abspath(p) == _HERE:
            continue
        f = os.path.join(p, "sitecustomize.py")
        if os.path.isfile(f):
            try:
                spec = importlib.util.spec_from_file_location("_vine_chained_sitecustomize", f)
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
            except Exception as e:  # noqa: BLE001
                _say(f"the other sitecustomize at {f} failed: {e!r}")
            return


_install()
_chain_other_sitecustomize()
