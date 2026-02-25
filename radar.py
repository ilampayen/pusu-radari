import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import requests
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="S&P 500 Pusu Radarı V8.0", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("S&P 500 Kuantitatif Radar ve Backtest Motoru (V8.0)")

if 'firsatlar_df' not in st.session_state:
    st.session_state.firsatlar_df = None

@st.cache_data(ttl=3600)
def sp500_listesini_getir():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    html_verisi = requests.get(url, headers=headers).text
    tablo = pd.read_html(html_verisi)[0]
    return [t.replace('.', '-') for t in tablo['Symbol'].tolist()]

def backtest_hesapla(data, limit=35, bekleme_suresi=10):
    try:
        sinyaller = data[data['RSI'] < limit]
        if len(sinyaller) == 0: return 0.0, 0.0
        kazanc_sayisi, toplam_getiri, gecerli_islem = 0, 0.0, 0
        
        for idx, row in sinyaller.iterrows():
            sinyal_index = data.index.get_loc(idx)
            if sinyal_index + bekleme_suresi < len(data):
                alis = row['Close']
                satis = data.iloc[sinyal_index + bekleme_suresi]['Close']
                getiri = (satis - alis) / alis
                toplam_getiri += getiri
                if getiri > 0: kazanc_sayisi += 1
                gecerli_islem += 1
                
        if gecerli_islem == 0: return 0.0, 0.0
        return round((kazanc_sayisi / gecerli_islem) * 100, 1), round((toplam_getiri / gecerli_islem) * 100, 2)
    except:
        return 0.0, 0.0

def radar_taramasi():
    tickers = sp500_listesini_getir()
    macro_limit, micro_limit = 35, 30
    ilerleme_cubugu = st.progress(0)
    durum_metni = st.empty()
    liste = []

    for i, ticker in enumerate(tickers):
        ilerleme_cubugu.progress((i + 1) / len(tickers))
        durum_metni.text(f"🔍 Taranıyor ve Test Ediliyor: {ticker} ({i+1}/{len(tickers)})")
        
        try:
            hisse = yf.Ticker(ticker)
            d_gunluk = hisse.history(period="1y") # Backtest için 1 yıllık veri çekilir
            if len(d_gunluk) < 50: continue
            d_gunluk['RSI'] = ta.momentum.RSIIndicator(d_gunluk['Close']).rsi()
            rsi_g = d_gunluk['RSI'].iloc[-1]
            
            if rsi_g < macro_limit:
                kazanma_orani, ortalama_getiri = backtest_hesapla(d_gunluk, macro_limit, 10)
                
                d_15m = hisse.history(period="5d", interval="15m")
                if d_15m.empty: continue
                d_15m['RSI'] = ta.momentum.RSIIndicator(d_15m['Close']).rsi()
                rsi_m = d_15m['RSI'].iloc[-1]
                
                fiyat = d_15m['Close'].iloc[-1]
                liste.append({
                    "Durum": "🟢 PUSU" if rsi_m < micro_limit else "🟡 İZLE",
                    "Hisse": ticker,
                    "Makro RSI": round(rsi_g, 1),
                    "Mikro RSI": round(rsi_m, 1),
                    "Tarihsel Kazanma (%)": kazanma_orani,
                    "Ortalama Getiri (%)": ortalama_getiri,
                    "Fiyat ($)": round(fiyat, 2),
                    "Pusu Limiti ($)": round(fiyat * 0.995, 2),
                    "Kâr Al ($)": round(fiyat * 1.07, 2)
                })
        except: pass
    
    durum_metni.empty()
    ilerleme_cubugu.empty()
    return pd.DataFrame(liste)

if st.button("🚀 S&P 500 RADARINI VE BACKTESTİ ATEŞLE"):
    with st.spinner("Amerikan Borsası taranıyor ve stratejiler test ediliyor... (2-4 dk)"):
        st.session_state.firsatlar_df = radar_taramasi()

if st.session_state.firsatlar_df is not None:
    df = st.session_state.firsatlar_df
    if len(df) > 0:
        st.success(f"Analiz Tamamlandı: {len(df)} aday listede.")
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 CSV İndir", df.to_csv(index=False).encode('utf-8'), "sp500_backtest.csv", "text/csv")
    else:
        st.warning("Kriterlere uyan hisse bulunamadı.")
