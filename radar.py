import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import requests
import warnings

warnings.filterwarnings('ignore')

# 1. ARAYÜZ (GUI) TASARIMI
st.set_page_config(page_title="S&P 500 Pusu Radarı", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("S&P 500 Kuantitatif Pusu Radarı (V6.0)")
st.markdown("---")

# 2. ALGORİTMA MOTORU
@st.cache_data(ttl=3600) # Listeyi 1 saat hafızada tutar, hızı artırır
def sp500_listesini_getir():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    html_verisi = requests.get(url, headers=headers).text
    tablo = pd.read_html(html_verisi)[0]
    tickers = [t.replace('.', '-') for t in tablo['Symbol'].tolist()]
    return tickers

def radar_taramasi():
    tickers = sp500_listesini_getir()
    macro_limit = 35
    micro_limit = 30
    
    # Ekranda şık bir ilerleme çubuğu (Progress Bar) oluşturur
    ilerleme_cubugu = st.progress(0)
    durum_metni = st.empty()
    
    bulunan_firsatlar = []

    for i, ticker in enumerate(tickers):
        # İlerleme çubuğunu günceller
        ilerleme_cubugu.progress((i + 1) / len(tickers))
        durum_metni.text(f"Taraniyor: {ticker} ({i+1}/{len(tickers)})")
        
        try:
            hisse = yf.Ticker(ticker)
            data_gunluk = hisse.history(period="60d", interval="1d")
            if data_gunluk.empty: continue
            data_gunluk['RSI'] = ta.momentum.RSIIndicator(data_gunluk['Close'], window=14).rsi()
            rsi_gunluk = data_gunluk['RSI'].iloc[-1]
            
            if rsi_gunluk < macro_limit:
                data_15m = hisse.history(period="5d", interval="15m")
                if data_15m.empty: continue
                data_15m['RSI'] = ta.momentum.RSIIndicator(data_15m['Close'], window=14).rsi()
                rsi_15m = data_15m['RSI'].iloc[-1]

                guncel_fiyat = data_15m['Close'].iloc[-1]
                limit_fiyati = guncel_fiyat * 0.995
                kar_al_hedefi = guncel_fiyat * 1.07
                
                durum = "🟢 KUSURSUZ PUSU" if rsi_15m < micro_limit else "🟡 İZLEMEDE"
                
                # Çıktıları bir sözlük (satır) olarak listeye ekler
                bulunan_firsatlar.append({
                    "Durum": durum,
                    "Hisse": ticker,
                    "Makro RSI (1D)": round(rsi_gunluk, 1),
                    "Mikro RSI (15m)": round(rsi_15m, 1),
                    "Güncel Fiyat ($)": round(guncel_fiyat, 2),
                    "Pusu Limiti ($)": round(limit_fiyati, 2),
                    "Kâr Al Hedefi ($)": round(kar_al_hedefi, 2)
                })
        except Exception:
            pass
            
    durum_metni.text("Tarama Tamamlandı!")
    return bulunan_firsatlar

# 3. KONTROL PANELİ
if st.button("🚀 RADARI ATEŞLE (S&P 500 Tarama)"):
    with st.spinner("Okyanus taranıyor, lütfen bekleyin... (2-4 dakika)"):
        firsatlar = radar_taramasi()
        
        if firsatlar:
            st.success(f"Toplam {len(firsatlar)} adet 'Aşırı Cezalandırılmış' aday bulundu.")
            # Listeyi şık bir