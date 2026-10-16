import datetime

import numpy as np
import streamlit as st

from nav_core import (
    FUND_NAMES,
    forecast_chart,
    format_compact_tzs,
    format_tzs,
    load_fund_data,
    nav_features,
    predict,
    show_accuracy,
    show_model_metrics,
    train_model,
)

st.title("Total NAV forecast")
st.caption("Forecast a fund's total net asset value from its outstanding units and pricing on a given date.")

fund = st.segmented_control("Fund", FUND_NAMES, default=FUND_NAMES[0], required=True, key="nav_fund")
features = nav_features(fund)
history = load_fund_data(fund).assign(NAV=lambda d: d["Sqrt_NAV"] ** 2)
latest = history.iloc[-1]

inputs_col, results_col = st.columns([1, 2], gap="large")
with inputs_col:
    with st.form("nav_forecast_form"):
        st.markdown(f"**{fund} inputs**")
        onu = st.number_input(
            "Outstanding number of units",
            min_value=0.0,
            value=float(np.exp(latest["Log_ONU"])),
            format="%.2f",
            key=f"nav_onu_{fund}",
        )
        if "Nav Per Unit" in features:
            nav_per_unit = st.number_input(
                "NAV per unit (TZS)", min_value=0.0, value=float(latest["Nav Per Unit"]), format="%.4f", key=f"nav_npu_{fund}"
            )
            repurchase_price = st.number_input(
                "Repurchase price per unit (TZS)",
                min_value=0.0,
                value=float(latest["Repurchase Price/Unit"]),
                format="%.4f",
                key=f"nav_rp_{fund}",
            )
        target_date = st.date_input(
            "Forecast date",
            value=datetime.date.today(),
            min_value=datetime.date(2017, 1, 1),
            format="DD/MM/YYYY",
            key=f"nav_date_{fund}",
        )
        submitted = st.form_submit_button("Forecast", type="primary", icon=":material/auto_graph:", width="stretch")
    st.caption(f"Inputs are prefilled with the latest record from {latest['Date']:%d %b %Y}.")

with results_col:
    if not submitted:
        with st.container(border=True, height="stretch", horizontal_alignment="center", vertical_alignment="center"):
            st.markdown(":material/insights: Adjust the inputs and select **Forecast** to see the prediction.",
                        text_alignment="center")
    else:
        values = {
            "Log_ONU": np.log(onu) if onu > 0 else 0.0,
            "Year": target_date.year,
            "Month": target_date.month,
            "Day": target_date.day,
        }
        if "Nav Per Unit" in features:
            values["Nav Per Unit"] = nav_per_unit
            values["Repurchase Price/Unit"] = repurchase_price

        model, metrics = train_model(fund, tuple(features), "Sqrt_NAV")
        # The model predicts the square root of NAV; square it to get TZS.
        predicted_nav = predict(model, features, [values[f] for f in features]) ** 2
        change = predicted_nav / latest["NAV"] - 1

        with st.container(horizontal=True):
            st.metric("Predicted NAV", format_compact_tzs(predicted_nav), border=True,
                      help=format_tzs(predicted_nav))
            st.metric("Change vs latest NAV", f"{change:+.2%}", delta=format_compact_tzs(predicted_nav - latest["NAV"]),
                      border=True)
        show_accuracy(metrics["R-squared"])
        forecast_chart(history, "NAV", "NAV (TZS)", target_date, predicted_nav)
        show_model_metrics(metrics)
