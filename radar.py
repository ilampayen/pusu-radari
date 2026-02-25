import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Pusu Radarı V8.6 - Zaman Motoru", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("VIP Portföy & Pusu Radarı (V8.6) - Zaman Maliyeti Analizi")

if 'etf_df' not in st.session_state: st.session_state.etf_df = None
if 'market_df' not in st.session_state: st.session_state.market_df = None

huzur_listesi = ["VEA", "SPYM", "SCHD"]

@st.cache_data(ttl=3600)
def sp500_listesini_getir():
    # Performans için buraya BIST listesini de koyabilirsiniz, ABD için S&P 500
    import requests
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    html_verisi = requests.get(url, headers=headers).text
    tablo = pd.read_html(html_verisi)[0]
    return [t.replace('.', '-') for t in tablo['Symbol'].tolist()]

def backtest_hesapla(data, limit=35, hedef_yuzde=1.07, max_bekleme=30):
    """
    Sadece getiri oranını değil, %7'lik (hedef_yuzde) hedefe ortalama kaç günde ulaşıldığını hesaplar.
    """
    try:
        sinyaller = data[data['RSI'] < limit]
        if len(sinyaller) == 0: return 0.0, 0.0, 0
        
        kazanc, toplam, adet = 0, 0.0, 0
        toplam_hedef_gun, hedefe_ulasan_adet = 0, 0
        
        for idx, row in sinyaller.iterrows():
            loc = data.index.get_loc(idx)
            alis_fiyati = row['Close']
            hedef_fiyat = alis_fiyati * hedef_yuzde
            
            # Tahmini Gün Hesaplama (Hedefe değdiği ilk gün)
            if loc + 1 < len(data):
                end_loc = min(loc + max_bekleme, len(data) - 1)
                gelecek_veri = data.iloc[loc+1 : end_loc+1]
                
                # Hedefe dokunduğu (High >= Hedef) günleri bul
                hedefi_vuranlar = gelecek_veri[gelecek_veri['High'] >= hedef_fiyat]
                
                if not hedefi_vuranlar.empty:
                    ilk_vurus_idx = hedefi_vuranlar.index[0]
                    gecen_gun = data.index.get_loc(ilk_vurus_idx) - loc
                    toplam_hedef_gun += gecen_gun
                    hedefe_ulasan_adet += 1

            # Klasik 10 Günlük Ortalama Getiri Testi
            bekleme = 10
            if loc + bekleme < len(data):
                ret = (data.iloc[loc + bekleme]['Close'] - alis_fiyati) / alis_fiyati
                toplam += ret
                if ret > 0: kazanc += 1
                adet += 1
                
        tarihsel_k = round((kazanc/adet)*100, 1) if adet > 0 else 0.0
        ort_getiri = round((toplam/adet)*100, 2) if adet > 0 else 0.0
        ort_hedef_gun = round(toplam_hedef_gun / hedefe_ulasan_adet, 1) if hedefe_ulasan_adet > 0 else 0
        
        return tarihsel_k, ort_getiri, ort_hedef_gun
    except: return 0.0, 0.0, 0

def analiz_et(ticker, is_etf=False):
    try:
        hisse = yf.Ticker(ticker)
        d_gunluk = hisse.history(period="1y")
        if len(d_gunluk) < 50: return None
        
        d_gunluk['RSI'] = ta.momentum.RSIIndicator(d_gunluk['Close']).rsi()
        rsi_g = d_gunluk['RSI'].iloc[-1]
        fiyat = d_gunluk['Close'].iloc[-1]
        
        if is_etf or rsi_g < 35:
            res = {"Enstrüman": ticker, "Makro RSI": round(rsi_g, 1), "Fiyat": round(fiyat, 2)}
            
            d_15m = hisse.history(period="5d", interval="15m")
            if not d_15m.empty:
                d_15m['RSI'] = ta.momentum.RSIIndicator(d_15m['Close']).rsi()
                res["Mikro RSI"] = round(d_15m['RSI'].iloc[-1], 1)
                res["Durum"] = "🟢 PUSU" if res["Mikro RSI"] < 30 else ("🟡 İZLE" if res["Mikro RSI"] < 40 else "⚪ NÖTR")
            
            # Backtest (Artık 3 parametre dönüyor)
            k, o, gun = backtest_hesapla(d_gunluk)
            res["Tarihsel Başarı (%)"] = k
            res["Ort. 10G Getiri (%)"] = o
            res["Tahmini Kâr Al (Gün)"] = f"{gun} Gün" if gun > 0 else "Ulaşamadı"
            
            res["Pusu Limiti"] = round(fiyat * 0.995, 2)
            res["Kâr Al Hedefi"] = round(fiyat * 1.07, 2)
            
            if is_etf:
                res["Zirveden Düşüş (%)"] = round(((fiyat - d_gunluk['High'].max()) / d_gunluk['High'].max()) * 100, 2)
                sma200 = d_gunluk['Close'].rolling(window=200).mean().iloc[-1] if len(d_gunluk) >= 200 else d_gunluk['Close'].mean()
                res["200G Ort. Mesafe (%)"] = round(((fiyat - sma200) / sma200) * 100, 2)
                
                son_yil = hisse.dividends[hisse.dividends.index > (pd.Timestamp.now(tz='UTC') - pd.DateOffset(years=1))]
                res["Temettü Verimi (%)"] = round((son_yil.sum() / fiyat) * 100, 2)
            
            return res
    except: return None

col1, col2 = st.columns(2)

with col1:
    if st.button("🛡️ HUZUR PORTFÖYÜNÜ DENETLE (VIP)"):
        with st.spinner("VIP Listesi denetleniyor..."):
            etf_res = [analiz_et(t, is_etf=True) for t in huzur_listesi]
            st.session_state.etf_df = pd.DataFrame([x for x in etf_res if x])
        st.success("Huzur Portföyü Güncellendi.")

with col2:
    if st.button("🚀 PUSU RADARINI ATEŞLE (Piyasa)"):
        with st.spinner("Piyasa taranıyor..."):
            market_res = []
            tickers = sp500_listesini_getir() # BIST için bist_listesini_getir() fonksiyonunu kullanın
            prog = st.progress(0)
            for i, t in enumerate(tickers):
                prog.progress((i+1)/len(tickers))
                r = analiz_et(t)
                if r: market_res.append(r)
            st.session_state.market_df = pd.DataFrame(market_res)
        st.success("Taraması Tamamlandı.")

st.markdown("---")
if st.session_state.etf_df is not None and not st.session_state.etf_df.empty:
    st.markdown("### 🏛️ HUZUR PORTFÖYÜ DURUM RAPORU")
    st.table(st.session_state.etf_df)

if st.session_state.market_df is not None and not st.session_state.market_df.empty:
    st.markdown("### 🔍 PUSU ADAYLARI")
    # Tahmini güne göre veya getiriye göre sıralayabilirsiniz
    st.dataframe(st.session_state.market_df.sort_values(by="Tarihsel Başarı (%)", ascending=False), use_container_width=True)
