import streamlit as st

from nav_core import ASSETS_DIR

st.set_page_config(
    page_title="UTT AMIS NAV forecasting",
    page_icon=str(ASSETS_DIR / "favicon.ico"),
    layout="wide",
)
st.logo(str(ASSETS_DIR / "uttamislogof.png"), size="large", link="https://www.uttamis.co.tz/")

page = st.navigation(
    [
        st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/monitoring:"),
        st.Page("app_pages/unit_forecast.py", title="NAV per unit forecast", icon=":material/trending_up:"),
        st.Page("app_pages/nav_forecast.py", title="Total NAV forecast", icon=":material/query_stats:"),
    ],
    position="top",
)
page.run()
