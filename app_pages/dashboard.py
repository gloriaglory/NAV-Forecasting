import altair as alt
import pandas as pd
import streamlit as st

from nav_core import ASSETS_DIR, FUND_NAMES, MONTH_NAMES, format_compact_tzs, format_tzs, load_nav_history

df = load_nav_history()
latest_date = df["Date Valued"].max()

st.title("Fund dashboard")
st.caption(
    f"{len(df):,} valuations across {df['Scheme Name'].nunique()} schemes · "
    f"data as of {latest_date:%d %B %Y}"
)

unparsed = df["Date Valued"].isna().sum()
if unparsed:
    st.warning(f"{unparsed} rows have dates that could not be read and are excluded.", icon=":material/warning:")

# Latest NAV per scheme, compared with the same point a year earlier.
st.subheader("Net asset value by scheme")
monthly = (
    df.set_index("Date Valued")
    .groupby("Scheme Name")["Net Asset Value"]
    .resample("M")
    .last()
    .reset_index()
)
kpi_cols = st.columns(3)
for i, scheme in enumerate(FUND_NAMES):
    history = monthly[monthly["Scheme Name"] == scheme]
    latest = history["Net Asset Value"].iloc[-1]
    year_ago = history["Net Asset Value"].iloc[-13] if len(history) > 12 else history["Net Asset Value"].iloc[0]
    kpi_cols[i % 3].metric(
        scheme,
        format_compact_tzs(latest),
        delta=f"{(latest / year_ago - 1):+.1%}",
        delta_description="vs last year",
        chart_data=history["Net Asset Value"].tail(24).tolist(),
        chart_type="area",
        border=True,
    )

st.space("medium")
st.subheader("Scheme trends")
with st.container(horizontal=True, vertical_alignment="bottom"):
    selected_scheme = st.selectbox("Scheme", FUND_NAMES, key="scheme_select")
    scheme_df = df[df["Scheme Name"] == selected_scheme]
    years = sorted(scheme_df["Year"].dropna().unique().astype(int), reverse=True)
    selected_year = st.selectbox("Year", years, key="year_select")
    available_months = sorted(scheme_df.loc[scheme_df["Year"] == selected_year, "Month"].unique().astype(int))
    selected_month = st.selectbox(
        "Month",
        available_months,
        index=len(available_months) - 1,
        format_func=lambda m: MONTH_NAMES[m - 1],
        key="month_select",
    )

nav_col, unit_col = st.columns(2)
with nav_col.container(border=True):
    st.markdown("**Net asset value over time**")
    chart = (
        alt.Chart(scheme_df)
        .mark_area(line=True, opacity=0.25)
        .encode(
            x=alt.X("Date Valued:T", title=None),
            y=alt.Y("Net Asset Value:Q", title="NAV (TZS)", axis=alt.Axis(format="~s")),
            tooltip=[alt.Tooltip("Date Valued:T", format="%d %b %Y"), alt.Tooltip("Net Asset Value:Q", format=",.0f")],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, alt=f"Net asset value of {selected_scheme} over time")
with unit_col.container(border=True):
    st.markdown("**NAV per unit over time**")
    chart = (
        alt.Chart(scheme_df)
        .mark_line()
        .encode(
            x=alt.X("Date Valued:T", title=None),
            y=alt.Y("Nav Per Unit:Q", title="NAV per unit (TZS)", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("Date Valued:T", format="%d %b %Y"), alt.Tooltip("Nav Per Unit:Q", format=",.4f")],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, alt=f"NAV per unit of {selected_scheme} over time")

month_df = scheme_df[(scheme_df["Year"] == selected_year) & (scheme_df["Month"] == selected_month)]
period = f"{MONTH_NAMES[selected_month - 1]} {selected_year}"

month_col, month_unit_col = st.columns(2)
with month_col.container(border=True):
    st.markdown(f"**NAV and outstanding units · {period}**")
    base = alt.Chart(month_df).encode(x=alt.X("Day:O", title="Day"))
    bars = base.mark_bar(opacity=0.35, color="#8a9a90").encode(
        y=alt.Y("Outstanding Number of Units:Q", title="Outstanding units", axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip("Date Valued:T", format="%d %b %Y"), alt.Tooltip("Outstanding Number of Units:Q", format=",.0f")],
    )
    line = base.mark_line(point=True, strokeWidth=2).encode(
        y=alt.Y("Net Asset Value:Q", title="NAV (TZS)", axis=alt.Axis(format="~s"), scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("Date Valued:T", format="%d %b %Y"), alt.Tooltip("Net Asset Value:Q", format=",.0f")],
    )
    st.altair_chart(
        alt.layer(bars, line).resolve_scale(y="independent").properties(height=280),
        alt=f"Daily NAV and outstanding units for {selected_scheme} in {period}",
    )
with month_unit_col.container(border=True):
    st.markdown(f"**NAV per unit · {period}**")
    chart = (
        alt.Chart(month_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Day:O", title="Day"),
            y=alt.Y("Nav Per Unit:Q", title="NAV per unit (TZS)", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("Date Valued:T", format="%d %b %Y"), alt.Tooltip("Nav Per Unit:Q", format=",.4f")],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, alt=f"Daily NAV per unit for {selected_scheme} in {period}")

if not month_df.empty:
    first, last = month_df.iloc[0], month_df.iloc[-1]
    with st.container(horizontal=True):
        st.metric("Closing NAV", format_compact_tzs(last["Net Asset Value"]),
                  delta=f"{last['Net Asset Value'] / first['Net Asset Value'] - 1:+.2%}", border=True)
        st.metric("Closing NAV per unit", format_tzs(last["Nav Per Unit"], 4),
                  delta=f"{last['Nav Per Unit'] / first['Nav Per Unit'] - 1:+.2%}", border=True)
        st.metric("Outstanding units", f"{last['Outstanding Number of Units']:,.0f}",
                  delta=f"{last['Outstanding Number of Units'] / first['Outstanding Number of Units'] - 1:+.2%}", border=True)
        st.metric("Valuations this month", len(month_df), border=True)

st.space("medium")
st.subheader("Compare schemes")
averages = (
    df.groupby("Scheme Name")
    .agg(**{"Average NAV": ("Net Asset Value", "mean"), "Average outstanding units": ("Outstanding Number of Units", "mean")})
    .reset_index()
)
avg_nav_col, avg_units_col = st.columns(2)
for col, measure in [(avg_nav_col, "Average NAV"), (avg_units_col, "Average outstanding units")]:
    with col.container(border=True):
        st.markdown(f"**{measure} by scheme**")
        chart = (
            alt.Chart(averages)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X(f"{measure}:Q", title=None, axis=alt.Axis(format="~s")),
                y=alt.Y("Scheme Name:N", title=None, sort="-x"),
                color=alt.Color("Scheme Name:N", legend=None),
                tooltip=["Scheme Name:N", alt.Tooltip(f"{measure}:Q", format=",.0f")],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, alt=f"{measure} for each scheme")

by_year = df.groupby(["Year", "Scheme Name"])["Net Asset Value"].mean().reset_index()
by_month = df.groupby(["Month", "Scheme Name"])["Net Asset Value"].mean().reset_index()
by_month["Month name"] = by_month["Month"].map(lambda m: MONTH_NAMES[m - 1][:3])

view = st.segmented_control(
    "Average NAV breakdown", ["By year", "By month"], default="By year", required=True, key="breakdown"
)
with st.container(border=True):
    if view == "By year":
        data, x = by_year, alt.X("Year:O", title=None)
    else:
        data, x = by_month, alt.X("Month name:N", title=None, sort=[m[:3] for m in MONTH_NAMES])
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=x,
            xOffset="Scheme Name:N",
            y=alt.Y("Net Asset Value:Q", title="Average NAV (TZS)", axis=alt.Axis(format="~s")),
            color=alt.Color("Scheme Name:N", title=None, legend=alt.Legend(orient="top")),
            tooltip=["Scheme Name:N", alt.Tooltip("Net Asset Value:Q", title="Average NAV", format=",.0f")],
        )
        .properties(height=340)
    )
    st.altair_chart(chart, alt=f"Average NAV of each scheme {view.lower()}")

st.space("medium")
with st.expander("Time series decomposition", icon=":material/stacked_line_chart:"):
    st.image(str(ASSETS_DIR / "time.PNG"), caption="Trend, seasonal and residual components of NAV", alt="Time series decomposition of NAV")

with st.expander("Raw data", icon=":material/table_chart:"):
    st.dataframe(
        df.drop(columns=["Year", "Month", "Day"]).sort_values("Date Valued", ascending=False),
        hide_index=True,
        column_config={
            "Date Valued": st.column_config.DateColumn(format="DD MMM YYYY"),
            "Net Asset Value": st.column_config.NumberColumn(format="localized"),
            "Outstanding Number of Units": st.column_config.NumberColumn(format="localized"),
        },
        alt="Full NAV history for all schemes",
    )
    st.markdown("**Statistical summary**")
    st.dataframe(df[["Net Asset Value", "Outstanding Number of Units", "Nav Per Unit", "Sale Price per Unit", "Repurchase Price/Unit"]].describe().T,
                 alt="Statistical summary of numeric columns")
