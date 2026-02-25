import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import requests
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="S&P 500 Pusu Radarı", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("S&P 500 Kuantitatif Pusu Radarı (V6.1)")

# BELLEK YÖNETİMİ: Verileri hafızada tutmak için
if 'firsatlar_df' not in st.session_state:
    st.session_state.firsatlar_df = None

@st.cache_data(ttl=3600)
def sp500_listesini_getir():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    html_verisi = requests.get(url, headers=headers).text
    tablo = pd.read_html(html_verisi)[0]
    return [t.replace('.', '-') for t in tablo['Symbol'].tolist()]

def radar_taramasi():
    tickers = sp500_listesini_getir()
    macro_limit, micro_limit = 35, 30
    ilerleme_cubugu = st.progress(0)
    durum_metni = st.empty()
    liste = []

    for i, ticker in enumerate(tickers):
        ilerleme_cubugu.progress((i + 1) / len(tickers))
        durum_metni.text(f"🔍 Denetleniyor: {ticker} ({i+1}/{len(tickers)})")
        try:
            hisse = yf.Ticker(ticker)
            d_gunluk = hisse.history(period="60d")
            if d_gunluk.empty: continue
            d_gunluk['RSI'] = ta.momentum.RSIIndicator(d_gunluk['Close']).rsi()
            rsi_g = d_gunluk['RSI'].iloc[-1]
            
            if rsi_g < macro_limit:
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
                    "Fiyat ($)": round(fiyat, 2),
                    "Pusu Limiti ($)": round(fiyat * 0.995, 2),
                    "Kâr Al ($)": round(fiyat * 1.07, 2)
                })
        except: pass
    
    durum_metni.empty()
    ilerleme_cubugu.empty()
    return pd.DataFrame(liste)

# BUTON VE GÖSTERİM
if st.button("🚀 RADARI ATEŞLE"):
    with st.spinner("Piyasa taranıyor..."):
        res = radar_taramasi()
        st.session_state.firsatlar_df = res

# EĞER VERİ VARSA GÖSTER
if st.session_state.firsatlar_df is not None:
    df = st.session_state.firsatlar_df
    st.success(f"Analiz Tamamlandı: {len(df)} aday listede.")
    
    # Tabloyu Göster
    st.dataframe(df, use_container_width=True)
    
    # CSV İndirme Butonu
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Sonuçları CSV Olarak İndir", csv, "pusu_adaylari.csv", "text/csv")
