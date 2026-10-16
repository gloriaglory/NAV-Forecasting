import json

import streamlit as st
from streamlit_lottie import st_lottie

from nav_core import ASSETS_DIR, FUNDS


@st.cache_data
def load_lottie(path):
    with open(path) as f:
        return json.load(f)


hero_text, hero_art = st.columns([3, 2], gap="large", vertical_alignment="center")
with hero_text:
    st.badge("UTT AMIS · Your obvious investment partner", icon=":material/account_balance:", color="green")
    st.title("Forecast the future of your investments")
    st.markdown(
        "Explore six years of net asset value (NAV) history for UTT AMIS unit trust schemes "
        "and forecast where each fund is heading, whether you're a seasoned investor "
        "or just starting your journey."
    )
    with st.container(horizontal=True):
        if st.button("Explore the dashboard", type="primary", icon=":material/monitoring:"):
            st.switch_page("app_pages/dashboard.py")
        if st.button("Make a forecast", icon=":material/trending_up:"):
            st.switch_page("app_pages/unit_forecast.py")
        st.link_button("Visit UTT AMIS", "https://www.uttamis.co.tz/", type="tertiary", icon=":material/open_in_new:")
with hero_art:
    st_lottie(load_lottie(ASSETS_DIR / "investor.json"), height=320, quality="medium", key="hero_lottie")

st.space("medium")
st.header("Why use NAV forecasting?")
features = [
    (":material/target:", "Accurate predictions", "Ensemble models forecast NAV and NAV per unit for each scheme."),
    (":material/account_tree:", "Six schemes", "Balanced, money market, bond, child-benefit and insurance-linked funds."),
    (":material/insights:", "In-depth analysis", "Dig into historical trends, monthly activity and scheme comparisons."),
    (":material/savings:", "Plan your future", "See your expected profit or loss per unit before you invest."),
]
for col, (icon, title, body) in zip(st.columns(4), features):
    with col.container(border=True, height="stretch"):
        st.markdown(f"### {icon}")
        st.markdown(f"**{title}**")
        st.caption(body)

st.space("medium")
st.header("Our funds")
fund_items = list(FUNDS.items())
for row in (fund_items[:3], fund_items[3:]):
    for col, (name, fund) in zip(st.columns(3), row):
        with col.container(border=True, height="stretch"):
            st.image(str(ASSETS_DIR / fund["logo"]), alt=f"{name} logo")
            st.subheader(name)
            st.badge(fund["risk"], color="gray")
            st.markdown(fund["description"])

st.space("medium")
st.header("Get started")
steps = [
    ("1", "Pick a scheme", "Choose the fund you're interested in."),
    ("2", "Explore its history", "Review trends and monthly activity on the dashboard."),
    ("3", "Forecast", "Enter a date and get a NAV forecast with its accuracy."),
]
for col, (number, title, body) in zip(st.columns(3), steps):
    with col.container(border=True, height="stretch"):
        st.markdown(f":green-badge[Step {number}] **{title}**")
        st.caption(body)
