"""Shared data loading, forecasting models, and UI helpers for the NAV app."""

import datetime
import pathlib

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import VotingRegressor
from sklearn.linear_model import Lasso, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

BASE_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Data"
ASSETS_DIR = BASE_DIR / "assets"

FUNDS = {
    "Umoja Fund": {
        "logo": "umoja-fund-logo.gif",
        "data": "NAV Umoja Fund.csv",
        "risk": "Medium risk",
        "description": "An open-ended balanced fund investing in a diversified portfolio, "
        "best suited for a medium risk profile.",
    },
    "Wekeza Maisha Fund": {
        "logo": "wekeza maisha.jpeg",
        "data": "NAV Wekeza Maisha Fund.csv",
        "risk": "Investment + insurance",
        "description": "The Wekeza Maisha / Invest Life Unit Trust is the first investment "
        "cum insurance scheme established by UTT AMIS in the country.",
    },
    "Watoto Fund": {
        "logo": "watoto1.jpeg",
        "data": "NAV Watoto Fund.csv",
        "risk": "Long term",
        "description": "A child benefit open-ended balanced fund that seeks to generate "
        "long-term capital appreciation.",
    },
    "Jikimu Fund": {
        "logo": "jikimu logo.jpeg",
        "data": "NAV Jikimu Fund.csv",
        "risk": "Medium risk",
        "description": "An open-ended balanced fund investing in a diversified portfolio, "
        "providing regular income to its unit holders.",
    },
    "Liquid Fund": {
        "logo": "liquid_logo.jpeg",
        "data": "NAV Liquid Fund.csv",
        "risk": "Low risk",
        "description": "An open-ended money market fund investing in short-term, "
        "highly liquid instruments.",
    },
    "Bond Fund": {
        "logo": "bondfund.jpeg",
        "data": "NAV Bond Fund.csv",
        "risk": "Fixed income",
        "description": "An open-ended fund investing mainly in government and corporate "
        "bonds for steady fixed income returns.",
    },
}
FUND_NAMES = list(FUNDS)

MONTH_NAMES = [datetime.date(2000, m, 1).strftime("%B") for m in range(1, 13)]

# Features used by the total NAV model. Bond Fund was trained on fewer inputs.
DEFAULT_NAV_FEATURES = ["Log_ONU", "Nav Per Unit", "Repurchase Price/Unit", "Year", "Month", "Day"]
NAV_FEATURES = {"Bond Fund": ["Log_ONU", "Year", "Month", "Day"]}
UNIT_FEATURES = ["Year", "Month", "Day"]


def nav_features(fund):
    return NAV_FEATURES.get(fund, DEFAULT_NAV_FEATURES)


@st.cache_data(ttl="1d", show_spinner="Loading NAV history...")
def load_nav_history():
    """Load the combined NAV history for all schemes, with numeric and date columns cleaned."""
    df = pd.read_csv(DATA_DIR / "net_asset_value.csv")

    for col in ["Net Asset Value", "Outstanding Number of Units"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce"
        )

    # Dates mix "30-12-2022" and "2/1/2017"; both are day-first.
    df["Date Valued"] = pd.to_datetime(
        df["Date Valued"], format="mixed", dayfirst=True, errors="coerce"
    )
    df["Year"] = df["Date Valued"].dt.year
    df["Month"] = df["Date Valued"].dt.month
    df["Day"] = df["Date Valued"].dt.day
    return df.sort_values("Date Valued").reset_index(drop=True)


@st.cache_data(ttl="1d")
def load_fund_data(fund):
    """Load the per-fund training data with a reconstructed valuation date."""
    df = pd.read_csv(DATA_DIR / FUNDS[fund]["data"])
    df["Date"] = pd.to_datetime(df[["Year", "Month", "Day"]].rename(columns=str.lower))
    return df.sort_values("Date").reset_index(drop=True)


@st.cache_resource(max_entries=24, show_spinner="Training forecasting model...")
def train_model(fund, features, target):
    """Fit the Lasso + Ridge voting ensemble for one fund and score it on a held-out split."""
    data = load_fund_data(fund)
    X = data[list(features)]
    y = data[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = VotingRegressor([("Lasso", Lasso(alpha=0.01)), ("Ridge", Ridge(alpha=0.1))])
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)
    daily_returns = y_test.pct_change().dropna()
    metrics = {
        "MAE": mean_absolute_error(y_test, predictions),
        "MSE": mse,
        "RMSE": np.sqrt(mse),
        "R-squared": r2_score(y_test, predictions),
        "MAPE (%)": np.mean(np.abs((y_test - predictions) / y_test)) * 100,
        "Annualized returns": (daily_returns.mean() + 1) ** 252 - 1,
        "Sharpe ratio": (daily_returns.mean() * 252) / (daily_returns.std() * np.sqrt(252)),
    }
    return model, metrics


def predict(model, features, values):
    return model.predict(pd.DataFrame([values], columns=list(features)))[0]


def format_tzs(value, decimals=2):
    return f"TZS {value:,.{decimals}f}"


def format_compact_tzs(value):
    for threshold, suffix in [(1e12, "T"), (1e9, "B"), (1e6, "M")]:
        if abs(value) >= threshold:
            return f"TZS {value / threshold:,.1f}{suffix}"
    return format_tzs(value)


def show_accuracy(r2):
    """Show how much to trust a forecast, colored by the model's R-squared."""
    message = f"Predicted with an accuracy (R²) of {r2:.2%}"
    if r2 > 0.8:
        st.success(message, icon=":material/verified:")
    elif r2 >= 0.5:
        st.warning(message, icon=":material/warning:")
    else:
        st.error(message, icon=":material/error:")


def show_model_metrics(metrics):
    with st.expander("Model accuracy metrics", icon=":material/analytics:"):
        table = pd.DataFrame({"Metric": list(metrics), "Value": list(metrics.values())})
        st.dataframe(
            table,
            hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format="%.4f")},
            alt="Model accuracy metrics on the held-out test set",
        )


def forecast_chart(history, value_col, value_title, forecast_date, forecast_value):
    """Line chart of a fund's history with the forecast point highlighted."""
    base = alt.Chart(history).encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y(f"{value_col}:Q", title=value_title, scale=alt.Scale(zero=False)),
    )
    line = base.mark_line(strokeWidth=1.5).encode(
        tooltip=[
            alt.Tooltip("Date:T", format="%d %b %Y"),
            alt.Tooltip(f"{value_col}:Q", title=value_title, format=",.2f"),
        ]
    )
    point_df = pd.DataFrame(
        {"Date": [pd.Timestamp(forecast_date)], value_col: [forecast_value], "Label": ["Forecast"]}
    )
    point = (
        alt.Chart(point_df)
        .mark_point(size=140, filled=True, color="#d97706")
        .encode(
            x="Date:T",
            y=f"{value_col}:Q",
            tooltip=[
                alt.Tooltip("Label:N", title=" "),
                alt.Tooltip("Date:T", format="%d %b %Y"),
                alt.Tooltip(f"{value_col}:Q", title=value_title, format=",.2f"),
            ],
        )
    )
    st.altair_chart(
        (line + point).properties(height=340),
        alt=f"{value_title} history with the forecast point highlighted",
    )
