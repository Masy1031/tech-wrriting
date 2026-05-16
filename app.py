import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Stock Price Dashboard", layout="wide")

# Automatically refresh every 5 minutes (300000 milliseconds)
st_autorefresh(interval=300000, limit=1000, key="data_refresh")

st.title("株価ダッシュボード (S&P 500 & All Country)")
st.markdown("Yahooファイナンスから取得した株価データを表示します。自動で更新されます。")

# Tickers
TICKERS = {
    "S&P 500": "^GSPC",
    "All Country (ACWI)": "ACWI" # iShares MSCI ACWI ETF as proxy
}

@st.cache_data(ttl=300) # Cache for 5 mins
def get_data(ticker, period="5y"):
    df = yf.Ticker(ticker).history(period=period)
    df.reset_index(inplace=True)
    # yfinance Date is timezone-aware, convert to timezone-naive
    if df['Date'].dt.tz is not None:
         df['Date'] = df['Date'].dt.tz_localize(None)
    return df

@st.cache_data(ttl=300)
def get_current_price(ticker):
    data = yf.Ticker(ticker).history(period="1d")
    if not data.empty:
        return data['Close'].iloc[-1]
    return None

# Top section: Current Prices
st.header("現在の株価")
cols = st.columns(len(TICKERS))

for idx, (name, symbol) in enumerate(TICKERS.items()):
    price = get_current_price(symbol)
    with cols[idx]:
        if price:
            st.metric(label=name, value=f"${price:,.2f}")
        else:
            st.metric(label=name, value="N/A")

st.divider()

# Bottom section: Historical Data
st.header("株価推移")

granularity = st.radio(
    "表示単位を選択してください:",
    ("日次 (Daily)", "月次 (Monthly)", "年次 (Yearly)"),
    horizontal=True
)

for name, symbol in TICKERS.items():
    st.subheader(name)
    df = get_data(symbol, period="5y" if granularity != "年次 (Yearly)" else "max")

    if df.empty:
        st.warning(f"{name} のデータが取得できませんでした。")
        continue

    # Process data based on granularity
    if granularity == "日次 (Daily)":
        plot_df = df
        x_label = "Date"
    elif granularity == "月次 (Monthly)":
        # Resample to monthly end
        df.set_index('Date', inplace=True)
        plot_df = df.resample('ME').last().reset_index()
        x_label = "Date"
    else: # Yearly
        # Resample to yearly end
        df.set_index('Date', inplace=True)
        plot_df = df.resample('YE').last().reset_index()
        plot_df['Year'] = plot_df['Date'].dt.year
        x_label = "Year"

    fig = px.line(plot_df, x=x_label, y="Close", title=f"{name} 推移 ({granularity})")
    fig.update_xaxes(title_text="日付" if x_label == "Date" else "年")
    fig.update_yaxes(title_text="終値 (USD)")

    st.plotly_chart(fig, use_container_width=True)
