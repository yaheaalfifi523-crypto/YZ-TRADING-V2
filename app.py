import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import requests
import os
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

    
TELEGRAM_BOT_TOKEN = "8853251663:AAHuzszMXg8XAEOUprRtpE78YIaZACd6COw"
TELEGRAM_CHAT_ID = "982998685"


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=data, timeout=10)
    response.raise_for_status()
st.set_page_config(page_title="YZ Trading V2", layout="wide")
refresh_count = st_autorefresh(
    interval=5 * 60 * 1000,
    key="auto_refresh"
)
st.title("YZ Trading V2")


SYMBOLS = [
    "RBLX","CDE","RRC","ENPH","CHWY","HIMS","CELH","FAST","RIVN",
    "LUV","ZETA","INTC","FTI","AA","ADM",
    "EXEL","LEVI","MAS",
    "VAL","TTD",
    "UBER","STM","ON","SWKS","HAL","DVN","KO",
    "BSx","NKE","TOST"
]


st.caption(f"{len(SYMBOLS)} Stocks Scanner • 1D → 4H → 15m → 5m")


@st.cache_data(ttl=60)
def get_data(symbol, period, interval):
    data = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data



    data = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


def trend_check(data):
    if data is None or len(data) < 50:
        return "⚪ لا بيانات"

    close = data["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    price = float(close.iloc[-1])
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])

    if price > e20 > e50:
        return "🟢 صاعد"
    elif price < e20 < e50:
        return "🔴 هابط"
    else:
        return "🟡 محايد"
        
def ema_signal(data):
    if data is None or len(data) < 89:
        return "⚪"

    close = data["Close"]

    ema8 = close.ewm(span=8, adjust=False).mean()
    ema89 = close.ewm(span=89, adjust=False).mean()

    e8_now = float(ema8.iloc[-1])
    e89_now = float(ema89.iloc[-1])

    e8_prev = float(ema8.iloc[-2])
    e89_prev = float(ema89.iloc[-2])
    

    diff_now = ((e8_now - e89_now) / e89_now) * 100
    diff_prev = ((e8_prev - e89_prev) / e89_prev) * 100

    # EMA8 فوق EMA89
    if diff_now > 0.1:
        return "🟢"

    # EMA8 تحت EMA89
    elif diff_now < -0.1:
        return "🔴"

    # تقاطع صاعد الآن
    elif diff_prev < 0 and diff_now >= 0:
        return "🟡"

    # قريب من التقاطع
    elif diff_now < 0 and diff_now >= -0.1:
        return "🔵"

    else:
        return "🔵"
        
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
    
def buy_sell_pressure(data, candles=6):
    data = data.tail(candles)

    green_volume = data[data["Close"] > data["Open"]]["Volume"].sum()
    red_volume = data[data["Close"] < data["Open"]]["Volume"].sum()

    total = green_volume + red_volume

    if total == 0:
        return 0, 0

    buy = round((green_volume / total) * 100, 1)
    sell = round((red_volume / total) * 100, 1)

    return buy, sell
    
def setup_15m(data):
    if data is None or len(data) < 25:
        return "⚪ لا بيانات"

    close = data["Close"]
    rsi = float(calc_rsi(close).iloc[-1])
    ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
    ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
    high = data["High"]
    low = data["Low"]

    price = float(close.iloc[-1])
    resistance = float(high.iloc[-21:-1].max())
    support = float(low.iloc[-21:-1].min())

    distance_up = (resistance - price) / price
    distance_down = (price - support) / price
    
    if rsi >= 75:
        return "🟡 صاعد لكن RSI مرتفع"
    if ema9 <= ema21:
        return "🟡 انتظار EMA 9/21"
    if rsi < 50:
        return "🟡 زخم ضعيف"
    if 0 <= distance_up <= 0.01:
        return "🟢 جاهز صعود"
    elif 0 <= distance_down <= 0.01:
        return "🔴 جاهز هبوط"
    else:
        return "⚪ لا يوجد"
        
        
def room_to_move_15m(data, price):
    if data is None or len(data) < 25:
        return False

    high = data["High"]

    resistance = float(high.iloc[-21:-1].max())

    room = resistance - price

    # الهدف المطلوب بين 10 و30 سنت حسب سعر السهم
    needed_room = min(max(price * 0.001, 0.10), 0.30)

    return room >= needed_room
    

        
def trigger_5m(data):
    if data is None or len(data) < 25:
        return "⚪ لا بيانات"

    close = data["Close"]
    rsi = float(calc_rsi(close).iloc[-2])
    
    ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-2])
    ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-2])
    high = data["High"]
    low = data["Low"]
    volume = data["Volume"]

    price = float(close.iloc[-2])
    resistance = float(high.iloc[-6:-2].max())
    support = float(low.iloc[-6:-2].min())

    avg_volume = float(volume.iloc[-22:-2].mean())
    current_volume = float(volume.iloc[-2])

    volume_ratio = (
        current_volume / avg_volume
        if avg_volume > 0 else 0
    )

    if price <= resistance :
        return f"⚪ رفض: لا اختراق ({round(price,2)} / {round(resistance,2)})"

    elif volume_ratio < 1.1:
        return f"⚪ رفض: حجم ضعيف {round(volume_ratio,2)}"

    elif rsi < 50:
        return f"⚪ رفض: RSI منخفض {round(rsi,1)}"

    elif rsi >= 70:
        return f"⚪ رفض: RSI مرتفع {round(rsi,1)}"

    elif ema9 <= ema21:
        return "⚪ رفض: EMA ضعيف"

    else:
        return "🚀 اختراق صاعد"
    
def final_decision(d1, h4, m15, m5, room_ok, rsi_5m):
    if (
        "جاهز صعود" in m15
        and "اختراق صاعد" in m5
        and room_ok
        and rsi_5m < 70
    ):
        return "🚀 دخول قوي"

    if "جاهز هبوط" in m15 or "كسر هابط" in m5:
        return "🔴 تجاهل"

    if "جاهز صعود" in m15 and rsi_5m >= 70:
        return "🟡 انتظار تهدئة RSI"

    if "جاهز صعود" in m15:
        return "🟢 مراقبة دخول"

    return "⚪ انتظار"
    
if "last_refresh_count" not in st.session_state:
    st.session_state.last_refresh_count = -1

auto_scan = refresh_count != st.session_state.last_refresh_count
st.session_state.last_refresh_count = refresh_count

if st.button("🔄 فحص الأسهم") or auto_scan:
    results = []

    progress = st.progress(0)
    status = st.empty()

    for i, symbol in enumerate(SYMBOLS):
        status.write(f"جاري تحليل {symbol} ...")

        try:
            daily = get_data(symbol, "6mo", "1d")
            h4 = get_data(symbol, "60d", "1h")
            m15 = get_data(symbol, "10d", "15m")
            m5 = get_data(symbol, "5d", "5m")
            
            
                
            if daily is None:
                continue

            # تحويل بيانات الساعة إلى 4 ساعات
            if h4 is not None:
                h4 = h4.resample("4h").agg({
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum"
                }).dropna()

            price = float(daily["Close"].iloc[-1])
            
            
            daily_close = daily["Close"].dropna()

            daily_changes = daily_close.diff().dropna()

            completed_changes = daily_changes.iloc[:-1] if len(daily_changes) > 1 else daily_changes

            d1 = completed_changes.iloc[-1] if len(completed_changes) >= 1 else 0
            d2 = completed_changes.iloc[-2] if len(completed_changes) >= 2 else 0
            d3 = completed_changes.iloc[-3] if len(completed_changes) >= 3 else 0
            d4 = completed_changes.iloc[-4] if len(completed_changes) >= 4 else 0
            d5 = completed_changes.iloc[-5] if len(completed_changes) >= 5 else 0
            d6 = completed_changes.iloc[-6] if len(completed_changes) >= 6 else 0
            d7 = completed_changes.iloc[-7] if len(completed_changes) >= 7 else 0
            d8 = completed_changes.iloc[-8] if len(completed_changes) >= 8 else 0
            d9 = completed_changes.iloc[-9] if len(completed_changes) >= 9 else 0
            d10 = completed_changes.iloc[-10] if len(completed_changes) >= 10 else 0
            
            red_sessions = sum(
                1 for x in completed_changes.iloc[-10:]
                if x < 0
            )
            sessions_display = (
                f"{'🟢' if d1 >= 0 else '🔴'}{d1:+.2f} "
                f"{'🟢' if d2 >= 0 else '🔴'}{d2:+.2f} "
                f"{'🟢' if d3 >= 0 else '🔴'}{d3:+.2f} "
                f"{'🟢' if d4 >= 0 else '🔴'}{d4:+.2f} "
                f"{'🟢' if d5 >= 0 else '🔴'}{d5:+.2f}"
                f"{'🟢' if d6 >= 0 else '🔴'}{d6:+.2f} "
                f"{'🟢' if d7 >= 0 else '🔴'}{d7:+.2f} "
                f"{'🟢' if d8 >= 0 else '🔴'}{d8:+.2f} "
                f"{'🟢' if d9 >= 0 else '🔴'}{d9:+.2f} "
                f"{'🟢' if d10 >= 0 else '🔴'}{d10:+.2f}"
            )
            
            d1_result = trend_check(daily)
            h4_result = trend_check(h4)
            m15_result = setup_15m(m15)
            m5_result = trigger_5m(m5)
            rsi_value = round(float(calc_rsi(m5["Close"]).iloc[-2]), 1)
            rsi_15m_value = round(float(calc_rsi(m15["Close"]).iloc[-2]), 1)
            buy_pressure, sell_pressure = buy_sell_pressure(m5, 6)
            
            if m5 is not None and "Volume" in m5.columns and m5["Volume"].sum() > 0:
                vwap = (m5["Close"] * m5["Volume"]).sum() / m5["Volume"].sum()

                if price > vwap:
                    vwap_display = "🟢 فوق VWAP"
                else:
                    vwap_display = "🔴 تحت VWAP"
            else:
                vwap_display = "⚪ لا يوجد"
            
            if rsi_15m_value >= 70:
                rsi_15m_display = f"🔴 {rsi_15m_value} تشبع"
            elif rsi_15m_value >= 65:
                rsi_15m_display = f"🟡 {rsi_15m_value} مرتفع"
            elif rsi_15m_value >= 50:
                rsi_15m_display = f"🟢 {rsi_15m_value} مناسب"
            else:
                rsi_15m_display = f"🟡 {rsi_15m_value} ضعيف"
            if rsi_value >= 70:
                rsi_display = f"🔴 {rsi_value} تشبع"
            elif rsi_value >= 65:
                rsi_display = f"🟡 {rsi_value} مرتفع"
            elif rsi_value >= 50:
                rsi_display = f"🟢 {rsi_value} مناسب"
            else:
                rsi_display = f"🟡 {rsi_value} منخفض"
                
                
            # حساب المقاومة (أعلى سعر قريب في آخر 15 شمعة)
            resistance = round(m15["High"].tail(15).max(), 2)
                
            room_ok = room_to_move_15m(m15, price)

            decision = final_decision(
                 d1_result,
                 h4_result,
                 m15_result,
                 m5_result,
                 room_ok,
                 rsi_value
            )
            
            current_price = round(price, 2)

            prev_close = yf.Ticker(symbol).history(period="5d")["Close"].iloc[-2]
            change = round(current_price - prev_close, 2)

            if change > 0:
                change_display = f"+{change:.2f}"
            elif change < 0:
                change_display = f"{change:.2f}"
            else:
                change_display = "0.00"
            
            if "telegram_sent" not in st.session_state:
                st.session_state.telegram_sent = {}

            telegram_key = f"{symbol}_{decision}"

            if (
            ("دخول قوي" in decision )
                and telegram_key not in st.session_state.telegram_sent
            ):
                message = (
                    f"📊 {symbol}\n"
                    f"السعر: {round(price, 2)}\n"
                    f"RSI 5m: {rsi_value}\n"
                    f"RSI 15m: {rsi_15m_value}\n"
                    f"15m: {m15_result}\n"
                    f"5m: {m5_result}\n"
                    f"القرار: {decision}"
                )

                send_telegram_message(message)
                st.session_state.telegram_sent[telegram_key] = True
                
                
                    
            
                   
                            

                
           
            
           
            
            if 'change_display' not in locals():
                change_display = "0.00"
                
            
           
            
            results.append({

                "السهم": symbol,
                "السعر": round(price, 2),
                "+/-": change_display,

                # النظام الأساسي
                "RSI 5m": rsi_display,
                "15m Setup": m15_result,
                "المقاومة": resistance,
                "5m Trigger": m5_result,
                "🎯 القرار النهائي": decision,
               
              
                "EMA": ema_signal(m5),
                
                "🔴 red": red_sessions,
                # آخر عمود
                "آخر 10 جلسات": sessions_display,
                })
              
        except Exception as e:
        
            results.append({
                "السهم": symbol,
                "السعر": "-",
               "RSI 5m": f"⚠️ {e}",
                
                "15m Setup": "-",
                "المقاومة": resistance,
                "5m Trigger": "-",
                "🎯 القرار النهائي": "⚠️ تعذر التحليل"
            })

        progress.progress((i + 1) / len(SYMBOLS))

    status.empty()
    progress.empty()

    if results:
        df = pd.DataFrame(results)

        priority = {
            "🚀 دخول قوي": 1,
            "🟢 مراقبة دخول": 2,
            "⚪ انتظار": 3,
            "🔴 تجاهل": 4,
            "⚠️ تعذر التحليل": 5
        }

        df["_ترتيب"] = df["🎯 القرار النهائي"].map(priority).fillna(99)
        df = df.sort_values("_ترتيب").drop(columns="_ترتيب")

        st.subheader("📊 نتائج فحص الأسهم")

        st.markdown("""
        <style>
        [data-testid="stDataFrame"] thead tr th {
            position: sticky;
            top: 0;
            z-index: 999;
            background-color: white;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <style>
        [data-testid="stDataFrame"] {
            overflow: visible !important;
        }

        [data-testid="stDataFrame"] [role="columnheader"] {
            position: sticky !important;
            top: 0 !important;
            z-index: 999 !important;
            background-color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if "+/-" in df.columns:
          df["+/-"] = df["+/-"].apply(lambda x: f"🟢 {x}" if "+" in str(x) else f"🔴 {x}")

        
        if "QML" in df.columns:
            df["QML"] = df["QML"].astype(str)
        
        st.markdown("""
        <style>
        div[data-testid="stDataFrame"] div[role="row"]:hover {
            background-color: #ffd6d6 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=2000
        )
        strong = len(df[df["🎯 القرار النهائي"] == "🚀 دخول قوي"])
        watch = len(df[df["🎯 القرار النهائي"] == "🟢 مراقبة دخول"])

        c1, c2, c3 = st.columns(3)
        c1.metric("🚀 دخول قوي", strong)
        c2.metric("🟢 مراقبة", watch)
        c3.metric("إجمالي الأسهم", len(df))

        st.caption(
            "القرار آلي مبني على الاتجاه والإعداد والاختراق، وليس توصية مالية."
        )
else:
    st.info("اضغط 🔄 فحص الأسهم لبدء تحليل القائمة.")
