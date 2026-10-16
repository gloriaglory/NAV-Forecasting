import datetime

import streamlit as st

from nav_core import (
    FUND_NAMES,
    UNIT_FEATURES,
    forecast_chart,
    format_tzs,
    load_fund_data,
    predict,
    show_accuracy,
    show_model_metrics,
    train_model,
)

st.title("NAV per unit forecast")
st.caption("Forecast a fund's NAV per unit on a future date and see your expected profit or loss per unit.")

fund = st.segmented_control("Fund", FUND_NAMES, default=FUND_NAMES[0], required=True, key="unit_fund")
history = load_fund_data(fund)
latest = history.iloc[-1]

inputs_col, results_col = st.columns([1, 2], gap="large")
with inputs_col:
    with st.form("unit_forecast_form"):
        st.markdown(f"**{fund} inputs**")
        current_nav = st.number_input(
            "Current NAV per unit (TZS)",
            min_value=0.0,
            value=float(latest["Nav Per Unit"]),
            format="%.4f",
            help="The NAV per unit you bought at or hold today. Used to compute profit or loss.",
            key=f"unit_current_{fund}",
        )
        target_date = st.date_input(
            "Forecast date",
            value=datetime.date.today(),
            min_value=datetime.date(2017, 1, 1),
            format="DD/MM/YYYY",
            key=f"unit_date_{fund}",
        )
        submitted = st.form_submit_button("Forecast", type="primary", icon=":material/auto_graph:", width="stretch")
    st.caption(f"Latest recorded NAV per unit: {format_tzs(latest['Nav Per Unit'], 4)} on {latest['Date']:%d %b %Y}")

with results_col:
    if not submitted:
        with st.container(border=True, height="stretch", horizontal_alignment="center", vertical_alignment="center"):
            st.markdown(":material/insights: Choose a forecast date and select **Forecast** to see the prediction.",
                        text_alignment="center")
    else:
        model, metrics = train_model(fund, tuple(UNIT_FEATURES), "Nav Per Unit")
        predicted = predict(model, UNIT_FEATURES, [target_date.year, target_date.month, target_date.day])
        profit_loss = predicted - current_nav

        with st.container(horizontal=True):
            st.metric("Predicted NAV per unit", format_tzs(predicted, 4), border=True)
            st.metric(
                "Profit / loss per unit",
                format_tzs(profit_loss, 4),
                delta=f"{profit_loss / current_nav:+.2%}" if current_nav else None,
                border=True,
            )
        show_accuracy(metrics["R-squared"])
        forecast_chart(history, "Nav Per Unit", "NAV per unit (TZS)", target_date, predicted)
        show_model_metrics(metrics)
