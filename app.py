import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- ページ設定 ---
st.set_page_config(
    page_title="Stock Price Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- 自動更新設定 (5分ごと) ---
st_autorefresh(interval=300000, limit=1000, key="data_refresh")

# --- 定数 ---
TICKERS = {
    "S&P 500": "^GSPC",
    "All Country (ACWI)": "ACWI" # 代替として iShares MSCI ACWI ETF
}

# --- データ取得関数 ---
@st.cache_data(ttl=300)
def get_data(ticker, period="5y"):
    df = yf.Ticker(ticker).history(period=period)
    df.reset_index(inplace=True)
    if df['Date'].dt.tz is not None:
         df['Date'] = df['Date'].dt.tz_localize(None)
    return df

@st.cache_data(ttl=300)
def get_recent_prices(ticker):
    # 前日比を出すために直近数日分のデータを取得
    data = yf.Ticker(ticker).history(period="5d")
    if len(data) >= 2:
        return data['Close'].iloc[-1], data['Close'].iloc[-2]
    elif len(data) == 1:
        return data['Close'].iloc[-1], None
    return None, None

# --- サイドバー ---
with st.sidebar:
    st.header("⚙️ 設定")
    granularity = st.radio(
        "グラフの表示単位を選択:",
        ("日次 (Daily)", "月次 (Monthly)", "年次 (Yearly)")
    )
    st.markdown("---")
    st.info("**💡 Tips**\n\nこのダッシュボードは5分ごとに自動更新されます。データはYahooファイナンスから取得しています。")

# --- メインコンテンツ ---
st.title("📈 株価ダッシュボード (S&P 500 & All Country)")
st.markdown("世界の主要な株価指数の現在の価格と推移を一覧できるダッシュボードです。")

st.divider()

# --- 現在の株価 (Metrics) ---
st.header("💵 現在の株価")
metric_cols = st.columns(len(TICKERS))

for idx, (name, symbol) in enumerate(TICKERS.items()):
    current_price, prev_price = get_recent_prices(symbol)
    with metric_cols[idx]:
        if current_price:
            if prev_price:
                delta = current_price - prev_price
                delta_percent = (delta / prev_price) * 100
                # 矢印と色付けをよしなにやってくれる Streamlit の metric を活用
                st.metric(
                    label=f"**{name}**",
                    value=f"${current_price:,.2f}",
                    delta=f"{delta:+,.2f} ({delta_percent:+.2f}%)"
                )
            else:
                st.metric(label=f"**{name}**", value=f"${current_price:,.2f}")
        else:
            st.metric(label=f"**{name}**", value="データ取得エラー")

st.markdown("<br>", unsafe_allow_html=True) # 少し余白を空ける

# --- 株価推移 (Charts) ---
st.header("📊 株価推移")

chart_cols = st.columns(2) # グラフを左右に並べる

for idx, (name, symbol) in enumerate(TICKERS.items()):
    # 年次の場合は全期間、それ以外は直近5年を取得
    df = get_data(symbol, period="5y" if granularity != "年次 (Yearly)" else "max")

    with chart_cols[idx]:
        if df.empty:
            st.warning(f"{name} のデータが取得できませんでした。")
            continue

        # 単位に応じたデータの加工
        if granularity == "日次 (Daily)":
            plot_df = df
            x_label = "Date"
        elif granularity == "月次 (Monthly)":
            # 月末のデータでリサンプリング
            df.set_index('Date', inplace=True)
            plot_df = df.resample('ME').last().reset_index()
            x_label = "Date"
        else: # Yearly
            # 年末のデータでリサンプリング
            df.set_index('Date', inplace=True)
            plot_df = df.resample('YE').last().reset_index()
            plot_df['Year'] = plot_df['Date'].dt.year
            x_label = "Year"

        # 見やすいエリアチャート (塗りつぶしグラフ) を作成
        fig = px.area(
            plot_df,
            x=x_label,
            y="Close",
            title=f"<b>{name}</b>",
            color_discrete_sequence=["#1f77b4"] if idx == 0 else ["#2ca02c"] # S&Pは青、ACWIは緑
        )

        # グラフのデザインを調整
        fig.update_layout(
            xaxis_title=None,
            yaxis_title="終値 (USD)",
            hovermode="x unified", # マウスオーバー時に縦線と値を表示
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="rgba(0,0,0,0)", # 背景を透明に
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_xaxes(showgrid=False) # X軸のグリッド線を非表示
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e0e0e0') # Y軸のグリッド線を薄く表示

        st.plotly_chart(fig, use_container_width=True)
