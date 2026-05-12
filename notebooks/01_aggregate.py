# /// script
# dependencies = [
#   "marimo",
#   "polars",
# ]
# ///

import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import json
    import re
    from pathlib import Path

    return Path, json, mo, pl, re


@app.cell
def _(mo):
    mo.md("""
    # Gson Energy Dataset — Aggregation
    """)
    return


@app.cell
def _(mo):
    results_input = mo.ui.text(
        value="results",
        label="Path to results directory (results)",
        full_width=True,
    )
    results_input
    return (results_input,)


@app.cell
def _(Path, results_input):
    RESULTS_DIR = Path(results_input.value).expanduser().resolve()
    print(f"Results dir: {RESULTS_DIR}")
    print(f"Exists: {RESULTS_DIR.exists()}")
    if RESULTS_DIR.exists():
        children = sorted(RESULTS_DIR.iterdir())
        print(f"Contents ({len(children)} items): {[c.name for c in children]}")
    return (RESULTS_DIR,)


@app.cell
def _(RESULTS_DIR, json, pl, re):
    def normalize_plugin(raw_name, goal):
        """Normalize plugin names across old/new Maven log formats.
        maven-compiler-plugin -> compiler
        compiler              -> compiler
        """
        norm = raw_name
        if norm.startswith("maven-"):
            norm = norm[len("maven-"):]
        if norm.endswith("-plugin"):
            norm = norm[:-len("-plugin")]
        return norm, f"{norm}:{goal}"

    records = []

    for release_dir in sorted(RESULTS_DIR.iterdir()):
        if not release_dir.is_dir():
            continue
        release = release_dir.name

        for iter_dir in sorted(release_dir.iterdir(), key=lambda p: int(p.name.replace("iter_", "")) if p.name.startswith("iter_") else 0):
            if not iter_dir.is_dir() or not iter_dir.name.startswith("iter_"):
                continue
            iter = int(iter_dir.name.replace("iter_", ""))

            for build_type in ("cold", "warm"):
                json_file = iter_dir / f"{build_type}_build.json"
                if not json_file.exists():
                    continue

                with open(json_file) as f:
                    data = json.load(f)

                if "error" in data:
                    print(f"Skipping error file: {json_file}")
                    continue

                exit_code = data.get("exit_code", -1)

                for phase in data.get("phases", []):
                    phase_index  = phase.get("index", 0)
                    start_token  = phase.get("start_token", "")
                    end_token    = phase.get("end_token", "")
                    duration_ms  = phase.get("duration_ms", None)
                    timestamp_us = phase.get("timestamp", None)

                    m = re.match(r'(?P<plugin>[\w-]+):(?P<version>[\d.]+):(?P<goal>[\w-]+)\s+\((?P<id>[^)]+)\)\s+@\s+(?P<module>[\w-]+)', start_token or "")
                    if m:
                        module = m.group(5)
                        plugin_name, plugin_label = normalize_plugin(m.group(1), m.group(3))
                        plugin_goal = m.group(3)
                    else:
                        continue

                    for metric in phase.get("metrics", []):
                        records.append({
                            "version":      release,
                            "iteration":    iter,
                            "build_type":   build_type,
                            "exit_code":    exit_code,
                            "phase_index":  phase_index,
                            "start_token":  start_token,
                            "end_token":    end_token,
                            "module":       module,
                            "plugin_name":  plugin_name,
                            "plugin_goal":  plugin_goal,
                            "plugin_label": plugin_label,
                            "duration_ms":  duration_ms,
                            "timestamp_us": timestamp_us,
                            "metric_name":  metric.get("name", ""),
                            "value_uj":     metric.get("value", None),
                            "value_j":      metric.get("value", None) / 1_000_000
                                            if metric.get("value") is not None else None,
                            "unit":         metric.get("unit", ""),
                            "source":       metric.get("source", ""),
                        })

    SCHEMA = {
        "version":      pl.String,
        "iteration":    pl.Int64,
        "build_type":   pl.String,
        "exit_code":    pl.Int64,
        "phase_index":  pl.Int64,
        "start_token":  pl.String,
        "end_token":    pl.String,
        "module":       pl.String,
        "plugin_name":  pl.String,
        "plugin_goal":  pl.String,
        "plugin_label": pl.String,
        "duration_ms":  pl.Int64,
        "timestamp_us": pl.Int64,
        "metric_name":  pl.String,
        "value_uj":     pl.Int64,
        "value_j":      pl.Float64,
        "unit":         pl.String,
        "source":       pl.String,
    }

    df_raw = pl.DataFrame(records, schema=SCHEMA) if records else pl.DataFrame(schema=SCHEMA)
    print(f"Loaded {len(df_raw)} rows")
    print(f"Results dir contents: {[str(dir) for dir in RESULTS_DIR.iterdir()] if RESULTS_DIR.exists() else 'DOES NOT EXIST'}")
    # df_raw.head(5)
    df_raw
    return (df_raw,)


@app.cell
def _(df_raw, mo, pl):
    if df_raw.is_empty():
        mo.stop(
            True,
            mo.callout(mo.md(f"""
    **No data loaded.** `df_raw` is empty.

    Check that:
    - The results directory path is correct
    - JSON files exist under `<results_dir>/<release>/rep_<n>/cold_build.json`
    - The JSON files contain a `phases` key with a non-empty list

    **Columns found:** `{df_raw.columns}`
            """), kind="danger")
        )

    df_pivot = (
        df_raw
        .with_columns(
            pl.when(pl.col("metric_name").str.starts_with("DRAM"))
              .then(pl.lit("DRAM"))
              .when(pl.col("metric_name").str.starts_with("PACKAGE"))
              .then(pl.lit("PACKAGE"))
              .when(pl.col("metric_name").str.starts_with("GPU"))
              .then(pl.lit("GPU"))
              .otherwise(pl.col("metric_name"))
              .alias("metric_group")
        )
        .group_by([
            "version", "iteration", "build_type", "exit_code",
            "phase_index", "start_token", "end_token", "module",
            "plugin_name", "plugin_goal", "plugin_label",
            "duration_ms", "timestamp_us", "metric_group"
        ])
        .agg(
            pl.col("value_j").sum().alias("energy_j"),
            pl.col("value_uj").sum().alias("energy_uj"),
        )
        .pivot(
            on="metric_group",
            index=[
                "version", "iteration", "build_type", "exit_code",
                "phase_index", "start_token", "end_token", "module",
                "plugin_name", "plugin_goal", "plugin_label",
                "duration_ms", "timestamp_us",
            ],
            values="energy_j",
            aggregate_function="sum",
        )
        .rename({"DRAM": "dram_j", "PACKAGE": "package_j"})
        .sort(["version", "iteration", "build_type", "phase_index"])
    )

    # Ensure columns exist even if no GPU present
    for _col in ("dram_j", "package_j"):
        if _col not in df_pivot.columns:
            df_pivot = df_pivot.with_columns(pl.lit(None).cast(pl.Float64).alias(_col))

    print(f"Phases dataset: {df_pivot.shape}")
    df_pivot[:20]
    return (df_pivot,)


@app.cell
def _(df_pivot, pl):
    df_totals = (
        df_pivot
        .group_by(["version", "iteration", "build_type", "exit_code"])
        .agg(
            pl.col("dram_j").sum().alias("total_dram_j"),
            pl.col("package_j").sum().alias("total_package_j"),
            pl.col("duration_ms").sum().alias("total_duration_ms"),
            pl.col("phase_index").count().alias("n_phases"),
        )
        .sort(["version", "iteration", "build_type"])
    )
    print(f"Totals dataset: {df_totals.shape}")
    df_totals.head(10)
    return (df_totals,)


@app.cell
def _(mo):
    mo.md("""
    ## Export
    """)
    return


@app.cell
def _(mo):
    output_input = mo.ui.text(
        value="data",
        label="Output directory for CSV files",
        full_width=True,
    )
    output_input
    return (output_input,)


@app.cell
def _(Path, df_pivot, df_raw, df_totals, mo, output_input):
    out_dir = Path(output_input.value).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    path_raw    = out_dir / "raw.csv"
    path_phases = out_dir / "phases.csv"
    path_totals = out_dir / "totals.csv"

    df_raw.write_csv(path_raw)
    df_pivot.write_csv(path_phases)
    df_totals.write_csv(path_totals)

    mo.callout(
        mo.md(f"""
    **Exported:**
    - `{path_raw}` — raw metrics ({len(df_raw)} rows)
    - `{path_phases}` — phases wide ({len(df_pivot)} rows)
    - `{path_totals}` — totals per build ({len(df_totals)} rows)
        """),
        kind="success",
    )
    return


if __name__ == "__main__":
    app.run()
