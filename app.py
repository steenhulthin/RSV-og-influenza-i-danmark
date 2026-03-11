from __future__ import annotations

from datetime import date
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="RSV og influenza i Danmark",
    page_icon="🦠",
    layout="wide",
)

INFLUENZA_URL = (
    "https://steenhulthin.github.io/infectious-diseases-data/"
    "02_influenza_epikurve_season_region_uge_agegrp.csv"
)
RSV_URL = (
    "https://steenhulthin.github.io/infectious-diseases-data/"
    "02_rsv_epikurve_season_region_uge_agegrp.csv"
)

READ_COLUMNS = {
    "Sygdom",
    "Sæson",
    "Uge",
    "Region",
    "Aldersgruppe",
    "Køn",
    "Antal borgere",
    "Antal Bekræftede tilfælde",
}

COLOR_MAP = {
    "RSV": "#1F7A8C",
    "Influenza A": "#D1495B",
}

WEEK_PATTERN = re.compile(r"(?P<year>\d{4})-U(?P<week>\d{2})")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(31, 122, 140, 0.12), transparent 32%),
                radial-gradient(circle at top left, rgba(209, 73, 91, 0.12), transparent 28%),
                linear-gradient(180deg, #f7fbfc 0%, #eef4f6 100%);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        #MainMenu, footer {
            visibility: hidden;
        }

        .hero {
            padding: 2rem 2.2rem;
            border-radius: 24px;
            background: linear-gradient(135deg, #12343b 0%, #1f4e5f 54%, #f4a261 160%);
            color: #f7fbfc;
            box-shadow: 0 18px 45px rgba(18, 52, 59, 0.18);
            margin-bottom: 1rem;
        }

        .hero-kicker {
            font-size: 0.78rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            opacity: 0.78;
            margin-bottom: 0.45rem;
        }

        .hero h1 {
            font-size: 2.5rem;
            line-height: 1.02;
            margin: 0;
            padding: 0;
        }

        .hero p {
            max-width: 48rem;
            margin: 0.9rem 0 0;
            color: rgba(247, 251, 252, 0.9);
            font-size: 1rem;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(18, 52, 59, 0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 24px rgba(18, 52, 59, 0.06);
        }

        .metric-label {
            color: #45636b;
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            color: #12343b;
            font-size: 2rem;
            font-weight: 700;
            line-height: 1;
        }

        .metric-subtitle {
            color: #607d86;
            font-size: 0.88rem;
            margin-top: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_week_label(week_label: str) -> pd.Timestamp | pd.NaT:
    match = WEEK_PATTERN.fullmatch(str(week_label).strip())
    if not match:
        return pd.NaT

    year = int(match.group("year"))
    week = int(match.group("week"))
    return pd.Timestamp(date.fromisocalendar(year, week, 1))


def format_week(week_start: pd.Timestamp) -> str:
    iso_week = week_start.isocalendar()
    return f"{iso_week.year}-U{iso_week.week:02d}"


@st.cache_data(show_spinner=False, ttl=60 * 60 * 6)
def load_dataset(url: str, disease_key: str) -> pd.DataFrame:
    frame = pd.read_csv(
        url,
        sep=";",
        decimal=",",
        usecols=lambda column: column in READ_COLUMNS,
    )
    frame = frame.rename(columns=str.strip)

    for column in frame.select_dtypes(include="object").columns:
        frame[column] = frame[column].str.strip()

    frame["Antal borgere"] = pd.to_numeric(frame["Antal borgere"], errors="coerce")
    frame["Antal Bekræftede tilfælde"] = pd.to_numeric(
        frame["Antal Bekræftede tilfælde"], errors="coerce"
    )
    frame["week_start"] = frame["Uge"].map(parse_week_label)

    frame = frame[
        (frame["Køn"] == "Alle")
        & (frame["Aldersgruppe"] == "Alle")
    ].copy()

    if disease_key == "influenza":
        frame = frame[frame["Sygdom"] == "INFLA"].copy()
    else:
        frame = frame[frame["Sygdom"] == "RSV"].copy()

    return frame.dropna(
        subset=["week_start", "Region", "Antal borgere", "Antal Bekræftede tilfælde"]
    )


def build_weekly_series(
    frame: pd.DataFrame,
    disease_label: str,
    region: str,
    start_week: pd.Timestamp,
    end_week: pd.Timestamp,
) -> pd.DataFrame:
    filtered = frame[
        (frame["Region"] == region)
        & (frame["week_start"] >= start_week)
        & (frame["week_start"] <= end_week)
    ].copy()

    weekly = (
        filtered.groupby(["week_start", "Uge", "Sæson"], as_index=False)
        .agg(
            cases=("Antal Bekræftede tilfælde", "sum"),
            population=("Antal borgere", "sum"),
        )
        .sort_values("week_start")
    )

    weekly["incidence"] = weekly["cases"].div(weekly["population"]).mul(100_000)
    weekly["disease"] = disease_label
    weekly["week_label"] = weekly["week_start"].map(format_week)
    return weekly


def render_metric_card(label: str, value: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_line_chart(line_frame: pd.DataFrame) -> go.Figure:
    figure = px.line(
        line_frame,
        x="week_start",
        y="incidence",
        color="disease",
        color_discrete_map=COLOR_MAP,
        markers=True,
        custom_data=["week_label", "cases", "population"],
        labels={
            "week_start": "Uge",
            "incidence": "Bekræftede tilfælde pr. 100.000 borgere",
            "disease": "Sygdom",
        },
    )
    figure.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Uge: %{customdata[0]}<br>"
            "Incidens: %{y:.1f}<br>"
            "Bekræftede tilfælde: %{customdata[1]:.0f}<br>"
            "Borgere: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    figure.update_layout(
        template="plotly_white",
        hovermode="x unified",
        legend_title_text="",
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.92)",
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="rgba(18, 52, 59, 0.08)")
    return figure


def build_scatter_chart(comparison_frame: pd.DataFrame) -> go.Figure:
    figure = px.scatter(
        comparison_frame,
        x="Influenza A",
        y="RSV",
        color="Sæson",
        hover_name="week_label",
        hover_data={
            "Sæson": True,
            "Influenza A": ":.1f",
            "RSV": ":.1f",
            "week_label": False,
        },
        labels={
            "Influenza A": "Influenza A incidens pr. 100.000",
            "RSV": "RSV incidens pr. 100.000",
            "Sæson": "Sæson",
        },
    )
    figure.update_traces(marker=dict(size=10, opacity=0.82, line=dict(width=0.6, color="white")))
    figure.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        legend_title_text="Sæson",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.92)",
    )
    figure.update_xaxes(gridcolor="rgba(18, 52, 59, 0.08)")
    figure.update_yaxes(gridcolor="rgba(18, 52, 59, 0.08)")
    return figure


inject_styles()

st.markdown(
    """
    <section class="hero">
        <div class="hero-kicker">National overvågning</div>
        <h1>RSV og influenza i Danmark</h1>
        <p>
            Interaktivt dashboard for ugentlig incidens af RSV og influenza A med filtre for periode
            og region. Dashboardet viser kun aldersgruppen Alle.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

try:
    influenza = load_dataset(INFLUENZA_URL, "influenza")
    rsv = load_dataset(RSV_URL, "rsv")
except Exception as exc:  # pragma: no cover - Streamlit UI fallback
    st.error(f"Data kunne ikke hentes: {exc}")
    st.stop()

all_weeks = (
    pd.concat([influenza["week_start"], rsv["week_start"]])
    .drop_duplicates()
    .sort_values()
    .tolist()
)

common_regions = sorted(set(influenza["Region"]).intersection(rsv["Region"]))
region_options = ["Alle"] + [region for region in common_regions if region != "Alle"]

filter_col, region_col = st.columns([2.3, 1])

with filter_col:
    start_week, end_week = st.select_slider(
        "Periode",
        options=all_weeks,
        value=(all_weeks[0], all_weeks[-1]),
        format_func=format_week,
    )

with region_col:
    selected_region = st.selectbox("Region", region_options)

st.caption("Influenza-serien viser kun INFLA. Dashboardet bruger kun aldersgruppen Alle.")

influenza_series = build_weekly_series(
    influenza,
    disease_label="Influenza A",
    region=selected_region,
    start_week=start_week,
    end_week=end_week,
)
rsv_series = build_weekly_series(
    rsv,
    disease_label="RSV",
    region=selected_region,
    start_week=start_week,
    end_week=end_week,
)

line_frame = pd.concat([rsv_series, influenza_series], ignore_index=True)

comparison = pd.merge(
    influenza_series[["week_start", "week_label", "Sæson", "incidence"]].rename(
        columns={"incidence": "Influenza A"}
    ),
    rsv_series[["week_start", "week_label", "Sæson", "incidence"]].rename(
        columns={"incidence": "RSV"}
    ),
    on=["week_start", "week_label", "Sæson"],
    how="inner",
).sort_values("week_start")

if line_frame.empty:
    st.warning("Ingen data matcher de valgte filtre.")
    st.stop()

latest_week = line_frame["week_start"].max()
latest_rsv = rsv_series.loc[rsv_series["week_start"] == latest_week, "incidence"]
latest_influenza = influenza_series.loc[
    influenza_series["week_start"] == latest_week, "incidence"
]
correlation = comparison[["Influenza A", "RSV"]].corr().iloc[0, 1] if len(comparison) > 1 else None

metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)

with metric_col_1:
    render_metric_card(
        "Seneste uge",
        format_week(latest_week),
        f"{selected_region} · Alle",
    )

with metric_col_2:
    render_metric_card(
        "Influenza A",
        f"{latest_influenza.iloc[0]:.1f}" if not latest_influenza.empty else "Ingen data",
        "Bekræftede tilfælde pr. 100.000 borgere",
    )

with metric_col_3:
    render_metric_card(
        "RSV",
        f"{latest_rsv.iloc[0]:.1f}" if not latest_rsv.empty else "Ingen data",
        "Bekræftede tilfælde pr. 100.000 borgere",
    )

with metric_col_4:
    correlation_text = f"{correlation:.2f}" if pd.notna(correlation) else "For få punkter"
    render_metric_card(
        "Sammenhæng",
        correlation_text,
        "Korrelationskoefficient mellem RSV og influenza A i perioden",
    )

st.subheader("Graf 1: Incidens over tid")
st.plotly_chart(build_line_chart(line_frame), width="stretch")

st.subheader("Graf 2: RSV mod influenza")
if comparison.empty:
    st.info("Scatterplottet kræver uger, hvor begge serier har data for de valgte filtre.")
else:
    st.plotly_chart(build_scatter_chart(comparison), width="stretch")

st.markdown(
    "Kilder: "
    "[ssi.dk](https://ssi.dk) via "
    f"[influenza epikurve]({INFLUENZA_URL})"
    " og "
    f"[RSV epikurve]({RSV_URL})."
)
