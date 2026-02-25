import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import warnings

warnings.filterwarnings('ignore')

# 1. SAYFA YAPISI
st.set_page_config(page_title="Çift Motorlu Pusu Radarı V8.5", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("Huzur Portföyü & S&P 500 Bağımsız Denetim Sistemi (V8.5)")

# BELLEK YÖNETİMİ
if 'etf_df' not in st.session_state: st.session_state.etf_df = None
if 'market_df' not in st.session_state: st.session_state.market_df = None

huzur_listesi = ["VEA", "SPYM", "SCHD"]

# 2. YARDIMCI FONKSİYONLAR
@st.cache_data(ttl=3600)
def sp500_listesini_getir():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    html_verisi = requests.get(url, headers=headers).text
    tablo = pd.read_html(html_verisi)[0]
    return [t.replace('.', '-') for t in tablo['Symbol'].tolist()]

def backtest_hesapla(data, limit=35):
    try:
        bekleme = 10
        sinyaller = data[data['RSI'] < limit]
        if len(sinyaller) == 0: return 0.0, 0.0
        kazanc, toplam, adet = 0, 0.0, 0
        for idx, row in sinyaller.iterrows():
            loc = data.index.get_loc(idx)
            if loc + bekleme < len(data):
                ret = (data.iloc[loc + bekleme]['Close'] - row['Close']) / row['Close']
                toplam += ret
                if ret > 0: kazanc += 1
                adet += 1
        return (round((kazanc/adet)*100, 1), round((toplam/adet)*100, 2)) if adet > 0 else (0.0, 0.0)
    except: return (0.0, 0.0)

def analiz_et(ticker, is_etf=False):
    try:
        hisse = yf.Ticker(ticker)
        d_gunluk = hisse.history(period="1y")
        if len(d_gunluk) < 50: return None
        
        d_gunluk['RSI'] = ta.momentum.RSIIndicator(d_gunluk['Close']).rsi()
        rsi_g = d_gunluk['RSI'].iloc[-1]
        fiyat = d_gunluk['Close'].iloc[-1]
        
        if is_etf or rsi_g < 35:
            res = {"Enstrüman": ticker, "Makro RSI": round(rsi_g, 1), "Fiyat ($)": round(fiyat, 2)}
            
            # 15 Dakikalık Mikro Analiz
            d_15m = hisse.history(period="5d", interval="15m")
            if not d_15m.empty:
                d_15m['RSI'] = ta.momentum.RSIIndicator(d_15m['Close']).rsi()
                res["Mikro RSI"] = round(d_15m['RSI'].iloc[-1], 1)
                res["Durum"] = "🟢 PUSU" if res["Mikro RSI"] < 30 else ("🟡 İZLE" if res["Mikro RSI"] < 40 else "⚪ NÖTR")
            
            # Backtest
            k, o = backtest_hesapla(d_gunluk)
            res["Tarihsel Başarı (%)"] = k
            res["Ort. 10G Getiri (%)"] = o
            
            if is_etf:
                res["Zirveden Düşüş (%)"] = round(((fiyat - d_gunluk['High'].max()) / d_gunluk['High'].max()) * 100, 2)
                sma200 = d_gunluk['Close'].rolling(window=200).mean().iloc[-1] if len(d_gunluk) >= 200 else d_gunluk['Close'].mean()
                res["200G Ort. Mesafe (%)"] = round(((fiyat - sma200) / sma200) * 100, 2)
                
                # Gerçek Temettü Hesabı (V8.4 Fix)
                son_yil = hisse.dividends[hisse.dividends.index > (pd.Timestamp.now(tz='UTC') - pd.DateOffset(years=1))]
                res["Temettü Verimi (%)"] = round((son_yil.sum() / fiyat) * 100, 2)
            
            return res
    except: return None

# 3. KONTROL PANELİ (AYRIK BUTONLAR)
col1, col2 = st.columns(2)

with col1:
    if st.button("🛡️ HUZUR PORTFÖYÜNÜ DENETLE (Hızlı)"):
        with st.spinner("VIP Listesi denetleniyor..."):
            etf_res = [analiz_et(t, is_etf=True) for t in huzur_listesi]
            st.session_state.etf_df = pd.DataFrame([x for x in etf_res if x])
        st.success("Huzur Portföyü Güncellendi.")

with col2:
    if st.button("🚀 S&P 500 RADARINI ATEŞLE (Derin)"):
        with st.spinner("Tüm S&P 500 taranıyor..."):
            market_res = []
            tickers = sp500_listesini_getir()
            prog = st.progress(0)
            for i, t in enumerate(tickers):
                prog.progress((i+1)/len(tickers))
                r = analiz_et(t)
                if r: market_res.append(r)
            st.session_state.market_df = pd.DataFrame(market_res)
        st.success("Piyasa Taraması Tamamlandı.")

# 4. GÖRSELLEŞTİRME
st.markdown("---")
if st.session_state.etf_df is not None:
    st.markdown("### 🏛️ HUZUR PORTFÖYÜ DURUM RAPORU")
    st.table(st.session_state.etf_df)

if st.session_state.market_df is not None:
    st.markdown("### 🔍 S&P 500 GÜNCEL PUSU ADAYLARI")
    if not st.session_state.market_df.empty:
        st.dataframe(st.session_state.market_df.sort_values(by="Tarihsel Başarı (%)", ascending=False), use_container_width=True)
    else:
        st.info("Kriterlere uyan agresif bir fırsat bulunamadı.")
