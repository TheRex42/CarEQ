"""careq command line: gen | measure | identify | fit | simulate | targets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from .signals import SweepSpec, generate
from .measure import (LOG_GRID, MeasureOptions, Measurement, Response, measure_files, apply_mic_cal)
from .identify import identify, EqModel, DEFAULT_LABELS_HZ, N_BANDS_DEFAULT
from .fit import fit_eq, load_target, list_targets, plot_fit, default_weights, DEFAULT_GAIN_SCALE


def _load_spec(args, manifest: dict | None = None, base: Path | None = None) -> SweepSpec:
    if args.stimulus:
        return SweepSpec.load(args.stimulus)
    if manifest and "stimulus" in manifest:
        return SweepSpec.load((base or Path(".")) / manifest["stimulus"])
    return SweepSpec.load("stimulus.json")


def _measure_opts(args) -> MeasureOptions:
    drift = "auto"
    if getattr(args, "no_drift", False):
        drift = "off"
    elif getattr(args, "drift_ppm", None) is not None:
        drift = float(args.drift_ppm)
    return MeasureOptions(pre_ms=args.pre_ms, post_ms=args.window_ms, drift=drift)


def _add_measure_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stimulus", default=None,
                   help="stimulus.json written by 'careq gen' (default: from the manifest, else ./stimulus.json)")
    p.add_argument("--window-ms", type=float, default=500.0, help="IR window after the peak (ms)")
    p.add_argument("--pre-ms", type=float, default=20.0, help="IR window before the peak (ms)")
    p.add_argument("--smooth", type=float, default=3.0, help="fractional-octave smoothing, 1/N")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--no-drift", action="store_true", help="skip clock drift estimation")
    g.add_argument("--drift-ppm", type=float, help="use a fixed recorder clock offset (ppm)")


def _print_sweep_diag(m: Measurement, frac: float) -> None:
    for i, s in enumerate(m.sweeps):
        snr = s.snr_db(frac)
        def at(f):
            return snr[int(np.argmin(np.abs(LOG_GRID - f)))]
        flag = "  CLIPPING!" if s.clip_fraction > 1e-4 else ""
        print(f"  sweep {i + 1}: onset {s.onset / m.fs:8.3f} s  drift {s.drift_ppm:+7.1f} ppm  "
              f"corr-quality {s.corr_quality:7.0f}  SNR@100/1k/10k: {at(100):.0f}/{at(1000):.0f}/{at(10000):.0f} dB{flag}")


def cmd_gen(args) -> int:
    spec = SweepSpec(fs=args.fs, f1=args.f1, f2=args.f2, duration=args.duration, level_dbfs=args.level,
                     pre_silence=args.pre, post_silence=args.post, repeats=args.repeats)
    paths = generate(args.out, spec, pink_seconds=args.pink)
    for k, v in paths.items():
        print(f"{k:9s} {v}")
    print(f"Copy the sweep WAV to the USB stick; keep {paths['stimulus']} for processing.")
    return 0


def cmd_measure(args) -> int:
    spec = _load_spec(args)
    m = measure_files(args.recording, spec, _measure_opts(args))
    print(f"{m.source}: {len(m.sweeps)} sweep(s)")
    _print_sweep_diag(m, args.smooth)
    resp = m.response(args.smooth)
    if args.mic_cal:
        resp = apply_mic_cal(resp, Response.from_csv(args.mic_cal))
    out = Path(args.out)
    resp.to_csv(out)
    print(f"wrote {out}")
    if args.save_npz:
        m.save(args.save_npz)
        print(f"wrote {args.save_npz}")
    if args.save_ir:
        import soundfile as sf
        ir = m.ir()
        sf.write(args.save_ir, ir / (np.max(np.abs(ir)) + 1e-12) * 0.9, m.fs, subtype="FLOAT")
        print(f"wrote {args.save_ir} (import in REW: File > Import > Import impulse response)")
    if args.plot:
        _plot_response([resp], args.plot, "Measured response (1/%g oct)" % args.smooth)
        print(f"wrote {args.plot}")
    return 0


def _plot_response(responses: list[Response], path: str, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import ticker
    colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, r in enumerate(responses):
        ax.semilogx(r.freq, r.db, color=colors[i % len(colors)], linewidth=1.8, label=r.name or f"#{i + 1}")
    ax.set_xlim(20, 20000)
    ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.grid(True, which="both", color="#e6e5e1", linewidth=0.6)
    ax.set_ylabel("dB")
    ax.set_title(title, loc="left")
    if len(responses) > 1:
        ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _parse_band_arg(tokens: list[str]) -> tuple[int, int, list[str]]:
    if len(tokens) < 3:
        raise SystemExit("--band needs: BAND STEPS FILE [FILE ...]")
    band = int(tokens[0]) - 1
    steps = int(tokens[1])
    return band, steps, tokens[2:]


def cmd_identify(args) -> int:
    opts = _measure_opts(args)
    baseline_files: list[str] = list(args.baseline or [])
    runs_spec: list[tuple[int, int, list[str]]] = [_parse_band_arg(t) for t in (args.band or [])]
    labels = None
    man, base = None, None
    if args.manifest:
        man = json.loads(Path(args.manifest).read_text())
        base = Path(args.manifest).parent
        baseline_files += [str(base / f) for f in man.get("baseline", [])]
        for r in man.get("bands", []):
            runs_spec.append((int(r["band"]) - 1, int(r["steps"]), [str(base / f) for f in r["files"]]))
        labels = man.get("labels_hz")
    spec = _load_spec(args, man, base)
    if not baseline_files:
        raise SystemExit("no baseline recordings given (use --baseline or a manifest)")
    if not runs_spec:
        raise SystemExit("no band recordings given (use --band or a manifest)")

    print(f"baseline: {len(baseline_files)} file(s)")
    baseline = measure_files(baseline_files, spec, opts)
    _print_sweep_diag(baseline, args.smooth)
    runs = []
    for band, steps, files in runs_spec:
        print(f"band {band + 1:2d} at {steps:+d}: {len(files)} file(s)")
        m = measure_files(files, spec, opts)
        _print_sweep_diag(m, args.smooth)
        runs.append((band, steps, m))
    model = identify(baseline, runs, n_bands=args.n_bands, labels_hz=labels, frac=args.smooth,
                     level_correct=not args.no_level_correct)
    model.save(args.out)
    print()
    print(model.describe())
    print(f"wrote {args.out}")
    if args.baseline_csv:
        baseline.response(args.smooth).to_csv(args.baseline_csv)
        print(f"wrote {args.baseline_csv}")
    if args.plot:
        _plot_bases(model, args.plot)
        print(f"wrote {args.plot}")
    return 0


def _plot_bases(model: EqModel, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import ticker
    fig, ax = plt.subplots(figsize=(10, 5))
    for b in model.bands:
        ax.semilogx(model.freq, b.basis_db, color="#2a78d6", linewidth=1.4, alpha=0.9)
        i = int(np.argmax(np.abs(b.basis_db)))
        ax.text(model.freq[i], b.basis_db[i] + 0.3, str(b.index + 1), ha="center", fontsize=8)
    ax.set_xlim(20, 20000)
    ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.grid(True, which="both", color="#e6e5e1", linewidth=0.6)
    ax.set_ylabel("dB at identification setting")
    ax.set_title("Measured EQ band shapes", loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def cmd_fit(args) -> int:
    model = EqModel.load(args.model)
    if args.measurement.endswith(".csv"):
        baseline = Response.from_csv(args.measurement, "measured")
    else:
        spec = _load_spec(args)
        m = measure_files([args.measurement] + list(args.more or []), spec, _measure_opts(args))
        _print_sweep_diag(m, args.smooth)
        baseline = m.response(args.smooth)
    if args.mic_cal:
        baseline = apply_mic_cal(baseline, Response.from_csv(args.mic_cal))
    target = load_target(args.target)
    w = default_weights(model.freq, f_lo=args.w_lo, f_hi=args.w_hi, f_min=args.fmin, f_max=args.fmax)
    current = _parse_current(args.current, model.n_bands)
    if current is not None:
        print("current settings: " + " ".join(f"{g:+d}" for g in current))
    result = fit_eq(baseline, model, target, weights=w, max_step=args.max_step, max_boost=args.max_boost,
                    current=current, gain_scale=args.gain_scale, cut_factor=args.cut_factor)
    print(result.summary())
    if args.out:
        Path(args.out).write_text(json.dumps(result.to_dict(), indent=1))
        print(f"wrote {args.out}")
    if args.plot:
        plot_fit(result, args.plot, f"target: {Path(args.target).stem}")
        print(f"wrote {args.plot}")
    return 0


def _parse_current(text: str | None, n: int) -> np.ndarray | None:
    """--current: 13 integers (comma/space separated) or a fit.json from a previous run."""
    if not text:
        return None
    p = Path(text)
    if p.exists():
        d = json.loads(p.read_text())
        vals = d["steps"] if isinstance(d, dict) else d
    else:
        vals = [int(v) for v in text.replace(",", " ").split()]
    vals = [int(v) for v in vals]
    if len(vals) != n:
        raise SystemExit(f"--current needs {n} integers, got {len(vals)}")
    return np.asarray(vals, dtype=int)


def cmd_simulate(args) -> int:
    from .simulate import Scenario
    from .signals import write_wav
    spec = SweepSpec(duration=args.duration, repeats=args.repeats)
    sc = Scenario.default(spec, seed=args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    spec.save(out / "stimulus.json")
    rng = np.random.default_rng(args.seed)
    n = sc.eq.n_bands
    manifest = {"stimulus": "stimulus.json", "baseline": [], "bands": [], "labels_hz": list(sc.eq.fc)}
    for i in range(args.baseline_files):
        name = f"baseline_{i + 1}.wav"
        write_wav(out / name, sc.record(np.zeros(n), onset_s=float(rng.uniform(0.3, 2.0)), drift_ppm=args.drift_ppm,
                                        snr_db=args.snr, seed=100 + i), spec.fs)
        manifest["baseline"].append(name)
    for k in range(n):
        steps = np.zeros(n)
        steps[k] = 9
        name = f"band{k + 1:02d}_p9.wav"
        write_wav(out / name, sc.record(steps, onset_s=float(rng.uniform(0.3, 2.0)), drift_ppm=args.drift_ppm,
                                        snr_db=args.snr, seed=200 + k), spec.fs)
        manifest["bands"].append({"band": k + 1, "steps": 9, "files": [name]})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    truth = {"fc": list(sc.eq.fc), "q": list(sc.eq.q), "db_per_step": list(sc.eq.db_per_step),
             "cut_factor": sc.eq.cut_factor, "limiter_knee_db": sc.eq.knee_db, "limiter_cap_db": sc.eq.cap_db,
             "drift_ppm": args.drift_ppm}
    (out / "truth.json").write_text(json.dumps(truth, indent=1))
    print(f"wrote {1 + args.baseline_files + n} WAVs, manifest.json, stimulus.json and truth.json to {out}")
    print(f"next: careq identify --manifest {out / 'manifest.json'} --out {out / 'eq_model.json'} "
          f"--baseline-csv {out / 'baseline.csv'}")
    return 0


def cmd_targets(args) -> int:
    for t in list_targets():
        print(t)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="careq", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="generate the sweep WAV for the USB stick and stimulus.json")
    g.add_argument("--out", default="stimulus")
    g.add_argument("--fs", type=int, default=48000)
    g.add_argument("--f1", type=float, default=20.0)
    g.add_argument("--f2", type=float, default=20000.0)
    g.add_argument("--duration", type=float, default=10.0)
    g.add_argument("--level", type=float, default=-12.0, help="sweep level dBFS")
    g.add_argument("--pre", type=float, default=1.0, help="silence before the first sweep (s)")
    g.add_argument("--post", type=float, default=2.0, help="silence after each sweep (s)")
    g.add_argument("--repeats", type=int, default=3,
                   help="sweeps per file; >=2 lets clock drift be measured exactly, and they are averaged")
    g.add_argument("--pink", type=float, default=0.0, help="also write N seconds of pink noise (phase 3)")
    g.set_defaults(func=cmd_gen)

    m = sub.add_parser("measure", help="process recording(s) into a smoothed response CSV")
    m.add_argument("recording", nargs="+", help="phone recording WAV(s) or saved .npz; several = pooled")
    _add_measure_args(m)
    m.add_argument("--mic-cal", help="mic calibration text file (UMIK-1 / REW format)")
    m.add_argument("--out", default="measurement.csv")
    m.add_argument("--save-npz", help="save the full measurement (spectra + IRs) for reuse")
    m.add_argument("--save-ir", help="save the averaged impulse response as WAV (for REW)")
    m.add_argument("--plot")
    m.set_defaults(func=cmd_measure)

    i = sub.add_parser("identify", help="baseline + per-band recordings -> eq_model.json")
    _add_measure_args(i)
    i.add_argument("--manifest", help="JSON: {stimulus, baseline:[...], bands:[{band, steps, files:[...]}]}")
    i.add_argument("--baseline", nargs="+", help="baseline recording(s), all bands at 0")
    i.add_argument("--band", nargs="+", action="append", metavar="X",
                   help="BAND STEPS FILE [FILE...]  e.g. --band 4 +9 rec.wav (repeatable)")
    i.add_argument("--n-bands", type=int, default=N_BANDS_DEFAULT)
    i.add_argument("--no-level-correct", action="store_true",
                   help="keep each run's broadband level difference to the baseline in its basis")
    i.add_argument("--out", default="eq_model.json")
    i.add_argument("--baseline-csv", help="also write the baseline response CSV (input for 'fit')")
    i.add_argument("--plot")
    i.set_defaults(func=cmd_identify)

    f = sub.add_parser("fit", help="fit integer band settings to a target")
    f.add_argument("--measurement", required=True, help="baseline response CSV, or a recording WAV/npz")
    f.add_argument("--more", nargs="*", help="additional recordings pooled with --measurement")
    f.add_argument("--model", default="eq_model.json")
    f.add_argument("--target", default="harman_car", help="bundled target name or a file (see 'careq targets')")
    f.add_argument("--mic-cal")
    f.add_argument("--max-step", type=int, default=9)
    f.add_argument("--max-boost", type=int, default=None,
                   help="cap positive steps lower than --max-step (boosts cost head-unit headroom)")
    f.add_argument("--current", help="settings the measurement was made with: 13 integers, or a previous "
                                     "fit.json; the fit then returns the corrected absolute settings")
    f.add_argument("--gain-scale", type=float, default=DEFAULT_GAIN_SCALE,
                   help="fraction of the single-band gain delivered when several bands are set (0.95 with ALC off)")
    f.add_argument("--cut-factor", type=float, default=None,
                   help="depth of a cut relative to the same boost (default: from the model, else 0.93)")
    f.add_argument("--w-lo", type=float, default=60.0, help="full weight above this frequency")
    f.add_argument("--w-hi", type=float, default=12000.0, help="full weight below this frequency")
    f.add_argument("--fmin", type=float, default=30.0, help="weight reaches its floor (5%%) below this")
    f.add_argument("--fmax", type=float, default=16000.0, help="weight reaches its floor (5%%) above this")
    f.add_argument("--out", default="fit.json")
    f.add_argument("--plot", default="fit.png")
    _add_measure_args(f)
    f.set_defaults(func=cmd_fit)

    s = sub.add_parser("simulate", help="write synthetic recordings of a known car for a dry run")
    s.add_argument("--out", default="sim")
    s.add_argument("--duration", type=float, default=10.0)
    s.add_argument("--repeats", type=int, default=3)
    s.add_argument("--baseline-files", type=int, default=2)
    s.add_argument("--drift-ppm", type=float, default=-63.0)
    s.add_argument("--snr", type=float, default=35.0)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(func=cmd_simulate)

    t = sub.add_parser("targets", help="list bundled target curves")
    t.set_defaults(func=cmd_targets)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
