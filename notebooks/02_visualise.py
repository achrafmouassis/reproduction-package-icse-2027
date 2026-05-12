# /// script
# dependencies = [
#   "marimo",
#   "polars",
#   "altair",
#   "matplotlib",
#   "mplcursors",
# ]
# ///

import marimo

__generated_with = "0.23.4"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import altair as alt
    from pathlib import Path

    return Path, alt, mo, pl


@app.cell
def _(mo):
    mo.md("""
    # Gson Energy Profiling — Visualisation
    """)
    return


@app.cell
def _(mo):
    dataset_input = mo.ui.text(
        value="data",
        label="Path to dataset directory (output of 01_aggregate.py)",
        full_width=True,
    )
    dataset_input
    return (dataset_input,)


@app.cell
def _(Path, dataset_input, pl):
    ds = Path(dataset_input.value).expanduser().resolve()

    df_phases = pl.read_csv(ds / "phases.csv")
    df_totals = pl.read_csv(ds / "totals.csv")

    VERSION_ORDER = (
        df_totals
        .select("version")
        .unique()
        .sort("version")
        ["version"]
        .to_list()
    )
    print("Versions:", VERSION_ORDER)
    print(f"Phases:   {df_phases.shape}")
    print(f"Totals:   {df_totals.shape}")
    return VERSION_ORDER, df_phases


@app.cell
def _(mo):
    mo.md("""
    ## Per-phase PACKAGE energy heatmap

    Rows = phases identified by **index — plugin:goal**.
    Columns = releases.
    """)
    return


@app.cell
def _(df_phases, mo, pl):
    bt4 = mo.ui.dropdown(
        options=["warm", "cold"], value="warm", label="Build type",
    )

    _modules = (
        df_phases
        .select(pl.col("module"))
        .unique()
        .sort("module")
        ["module"]
        .to_list()
    )

    bt4
    return (bt4,)


@app.cell(hide_code=True)
def _(VERSION_ORDER, alt, bt4, df_phases, mo, pl):
    all_phases_df = (
        df_phases
        .select(["phase_index", "plugin_label"])
        .unique()
        .sort(["phase_index", "plugin_label"])
        .with_columns(
            (pl.col("phase_index").cast(pl.Utf8) + " — " + pl.col("plugin_label"))
            .alias("phase_label")
        )
    )

    _phase_order4 = (
        all_phases_df
        .group_by("plugin_label")
        .agg(pl.col("phase_index").min())
        .sort("phase_index")
        .select("plugin_label")
        .to_series()
        .to_list()
    )

    charts = []
    for module in df_phases["module"].unique().sort().to_list():
        _df = (
            df_phases
            .filter(
                # pl.col("version").is_in(['2.13.2', '2.14.0']),
                pl.col("build_type") == bt4.value,
                pl.col("module") == module
            )
            .with_columns(
                (pl.col("package_j") + pl.col("dram_j")).alias("total_j"),
                pl.col("duration_ms").alias("duration_ms")
            )
            .group_by(["version", "phase_index", "plugin_label"])
            .agg(
                pl.col("total_j").mean().alias("mean_total_j"),
                (pl.col("duration_ms").mean() / 1000).round(2).alias("duration")
            )
            .with_columns(
                (pl.col("phase_index").cast(pl.Utf8) + " — " + pl.col("plugin_label"))
                .alias("phase_label")
            )
            .sort(["phase_index", "plugin_label", "version"])
            .to_pandas()
        )

        _phase_order = (
            _df[["phase_index", "phase_label"]]
            .drop_duplicates()
            .sort_values("phase_index")["phase_label"]
            .tolist()
        )

        chart = alt.Chart(_df).mark_rect().encode(
            x=alt.X("version:O", sort=VERSION_ORDER, title="Gson release"),
            y=alt.Y(
                "phase_label:N",
                sort=_phase_order,
                title="Phase (index — plugin:goal)",
                axis=alt.Axis(labelFontSize=8),
            ),
            color=alt.Color(
                "mean_total_j:Q",
                title="Mean total (J)",
                scale=alt.Scale(scheme="orangered", type="sqrt"),
                legend=alt.Legend(labelFontSize=10, orient="right"),
            ),
            tooltip=[
                alt.Tooltip("version:N",      title="Release"),
                alt.Tooltip("phase_index:Q",  title="Phase index"),
                alt.Tooltip("plugin_label:N", title="Plugin"),
                alt.Tooltip("duration:N", title="Duration (s)"),
                alt.Tooltip("mean_total_j:Q", title="Total energy (J)", format=".3f"),
            ],
        ).properties(
            title=f"{module} — {bt4.value}",
            width=400,
            height=max(300, len(_phase_order) * 16),
        )
        charts.append(chart)

    mo.hstack(charts, wrap=True)
    return


@app.cell
def _(VERSION_ORDER, alt, bt4, df_phases, pl):
    _df_all = (
        df_phases
        .filter(pl.col("build_type") == bt4.value)
        .with_columns(
            (pl.col("package_j") + pl.col("dram_j")).alias("total_j"),
        )
        .group_by(["module", "version", "plugin_label"])
        .agg(
            pl.col("total_j").mean().alias("mean_total_j"),
            (pl.col("duration_ms").mean() / 1000).round(2).alias("duration")
        )
        .group_by(["version", "plugin_label"])
        .agg(
            pl.col("mean_total_j").sum().alias("mean_total_j"),
            pl.col("duration").sum().alias("duration")
        )
        .sort(["plugin_label", "version"])
    )

    _plugin_order = (
        _df_all
        .group_by("plugin_label")
        .agg(pl.col("mean_total_j").mean())
        .sort("mean_total_j", descending=True)
        .get_column("plugin_label")
        .to_list()
    )

    chart_all = alt.Chart(_df_all.to_pandas()).mark_rect().encode(
        x=alt.X("version:O", sort=VERSION_ORDER, title="Gson release"),
        y=alt.Y(
            "plugin_label:N",
            sort=_plugin_order,
            title="Plugin:goal",
            axis=alt.Axis(labelFontSize=8),
        ),
        color=alt.Color(
            "mean_total_j:Q",
            title="Total energy (J)",
            scale=alt.Scale(scheme="orangered", type="sqrt"),
            legend=alt.Legend(labelFontSize=10, orient="right"),
        ),
        tooltip=[
            alt.Tooltip("version:N",      title="Release"),
            alt.Tooltip("plugin_label:N", title="Plugin"),
            alt.Tooltip("duration:Q",     title="Duration (s)"),
            alt.Tooltip("mean_total_j:Q", title="Total energy (J)", format=".3f"),
        ],
    ).properties(
        title=f"All modules — {bt4.value}",
        width=500,
        height=max(300, len(_plugin_order) * 24),
    )

    chart_all
    return


@app.cell
def _(mo):
    mo.md("""
    ## Energy regression per phase across releases

    Select phases by their **index — plugin:goal** label.
    Same plugin invoked for different submodules = different lines.
    """)
    return


@app.cell(hide_code=True)
def _(VERSION_ORDER, alt, df_phases, pl):
    _df_bar = (
        df_phases
        .group_by(["version", "module", "build_type", "iteration"])
        .agg((pl.col("package_j").sum() + pl.col("dram_j").sum()).alias("total_j"))
        .group_by(["version", "module", "build_type"])
        .agg(pl.col("total_j").mean())
        .sort(["module", "version"])
    )

    chart_bar4 = alt.Chart(_df_bar).mark_bar().encode(
        x=alt.X("version:O", sort=VERSION_ORDER, title="Version"),
        y=alt.Y("total_j:Q", title="Total energy (J)", stack="zero"),
        color=alt.Color(
            "module:N",
            title="Module",
            legend=alt.Legend(
                labelFontSize=10,
                orient="top",
            ),
        ),
        column=alt.Column(
            "build_type:N",
            title="Build type",
            header=alt.Header(labelFontSize=11, titleFontSize=12),
        ),
        tooltip=[
            alt.Tooltip("version:N",    title="Version"),
            alt.Tooltip("module:N",     title="Module"),
            alt.Tooltip("build_type:N", title="Build type"),
            alt.Tooltip("total_j:Q",    title="Total energy (J)", format=".2f"),
        ],
    ).properties(
        width=350,
        height=400,
        # title="Total energy (PACKAGE + DRAM) by module and version",
    ).interactive()

    chart_bar4
    return


@app.cell
def _(df_phases, pl):
    _df_ratios = (
        df_phases
        .group_by(["version", "module", "build_type", "iteration"])
        .agg((pl.col("package_j").sum() + pl.col("dram_j").sum()).alias("total_j"))
        .group_by(["version", "module", "build_type"])
        .agg(pl.col("total_j").mean())
        .sort(["module", "version"])
        .pivot(on="build_type", index=["version", "module"], values="total_j")
        .with_columns(
            (pl.col("cold") / pl.col("warm")).round(3).alias("ratio")
        )
        .select(["version", "module", "cold", "warm", "ratio"])
    )

    _df_totals = (
        _df_ratios
        .group_by("version")
        .agg(
            pl.col("cold").sum().alias("total_cold"),
            pl.col("warm").sum().alias("total_warm"),
        )
    )

    _df_ratios = (
        _df_ratios
        .join(_df_totals, on="version")
        .with_columns(
            (pl.col("cold") / pl.col("total_cold")).round(3).alias("cold_pct"),
            (pl.col("warm") / pl.col("total_warm")).round(3).alias("warm_pct"),
        )
        .select(["version", "module", "cold", "cold_pct", "warm", "warm_pct", "ratio"])
    )

    _df_total = (
        _df_ratios
        .group_by("version")
        .agg(
            pl.col("cold").sum(),
            pl.col("warm").sum(),
        )
        .with_columns(
            (pl.col("cold") / pl.col("warm")).round(3).alias("ratio"),
            pl.lit("total").alias("module"),
            pl.lit(1.0).alias("cold_pct"),
            pl.lit(1.0).alias("warm_pct"),
        )
        .select(["version", "module", "cold", "cold_pct", "warm", "warm_pct", "ratio"])
    )

    pl.concat([_df_ratios, _df_total]).sort(["version", "module"])
    return


@app.cell
def _(df_phases, pl):
    _df_ratios = (
        df_phases
        .group_by(["version", "module", "build_type", "iteration"])
        .agg((pl.col("package_j").sum() + pl.col("dram_j").sum()).alias("total_j"))
        .group_by(["version", "module"])
        .agg(pl.col("total_j").mean())
        .sort(["module", "version"])
        .filter(pl.col("version").is_in(["2.13.2", "2.14.0"]))
        .pivot(on="version", index="module", values="total_j")
        .with_columns(
            (pl.col("2.13.2") / pl.col("2.14.0")).round(3).alias("ratio")
        )
    )
    _df_ratios
    return


if __name__ == "__main__":
    app.run()
