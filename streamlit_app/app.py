"""Aplikasi Streamlit: klasifikasi penggunaan lahan Jawa Timur (Sentinel-2).
Jalankan: streamlit run app.py   (membaca folder data/ hasil notebook)"""
import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from folium.plugins import Fullscreen
from folium.raster_layers import ImageOverlay

D = Path(__file__).parent / "data"
GOOGLE_SAT = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
GOOGLE_HYB = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
KOLOM_PIKSEL = ["% Training", "% Testing", "Piksel Training (Poligon)",
                "Piksel Testing (Poligon)", "Piksel tersedia di poligon"]

st.set_page_config(page_title="SIG Klasifikasi Lahan Jawa Timur", layout="wide")


@st.cache_data
def muat(nama):
    f = D / nama
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def swatch(nama, warna):
    return (f'<span style="background:{warna};opacity:.85;display:inline-block;width:12px;'
            f'height:12px;border:1px solid #333"></span> {nama}')


def ribuan(v):
    return f"{v:,.0f}".replace(",", ".")


def peta_dasar(pusat, batas=None):
    m = folium.Map(location=pusat, zoom_start=8, tiles=None, control_scale=True)
    folium.TileLayer(GOOGLE_SAT, attr="Google", name="Satelit Google", max_zoom=20).add_to(m)
    folium.TileLayer(GOOGLE_HYB, attr="Google", name="Satelit + label Google", max_zoom=20, show=False).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
    Fullscreen().add_to(m)
    if batas is not None:
        m.fit_bounds(batas)
    return m


def buat_peta_sampel(meta, sampel, tampil, dengan_poligon):
    titik = pd.DataFrame(sampel["titik"])
    batas = [[titik["lat"].min(), titik["lon"].min()], [titik["lat"].max(), titik["lon"].max()]]
    m = peta_dasar(meta["pusat"], batas)
    for nama in meta["kelas"]:
        warna = meta["warna"][nama]
        fg = folium.FeatureGroup(name=swatch(nama, warna), show=True).add_to(m)
        if dengan_poligon:
            fitur = [f for f in sampel["poligon"]["features"]
                     if f["properties"]["kelas"] == nama and tampil in ("Semua", f["properties"]["split"])]
            if fitur:
                folium.GeoJson({"type": "FeatureCollection", "features": fitur},
                               style_function=lambda f, c=warna: {"color": c, "weight": 2, "fillColor": c, "fillOpacity": 0.4},
                               tooltip=folium.GeoJsonTooltip(fields=["kelas", "poligon_id", "split"],
                                                             aliases=["Kelas:", "Poligon:", "Set:"])).add_to(fg)
        sub = titik[(titik["kelas"] == nama) & (titik["split"].isin(["Training", "Testing"] if tampil == "Semua" else [tampil]))]
        for r in sub.itertuples():
            uji = r.split == "Testing"
            folium.CircleMarker([r.lat, r.lon], radius=6 if uji else 5,
                                color="black" if uji else "white", weight=2 if uji else 1,
                                fill=True, fill_color=warna, fill_opacity=1,
                                tooltip=f"{nama} | poligon {r.poligon_id} | {r.split}").add_to(fg)
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    return m


def buat_peta_hasil(meta, opacity):
    m = peta_dasar(meta["pusat"])
    for lap in meta["lapisan"]:   # satu lapisan per kelas -> kotak centang di pojok kanan atas
        fg = folium.FeatureGroup(name=swatch(lap["kelas"], lap["warna"]), show=True).add_to(m)
        ImageOverlay(image=str(D / lap["png"]), bounds=lap["bounds"], opacity=opacity,
                     interactive=False, zindex=5).add_to(fg)
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    return m


meta = muat("meta.json")
if meta is None:
    st.error("Folder data/ belum ada. Jalankan notebook sampai bagian 8.1 lalu salin streamlit_app/ ke sini.")
    st.stop()
sampel = muat("sampel.json")

st.title(meta["judul"])
st.caption(f"UTS Proyek Sains Data | citra {meta['periode'][0]} s/d {meta['periode'][1]} | "
           f"resolusi peta {meta['skala_peta_m']} m")

tab_data, tab_model, tab_peta = st.tabs(["Sampel dan jumlah piksel", "Model dan akurasi", "Peta hasil"])

with tab_data:
    st.subheader("Peta Sebaran Sampel")
    if sampel is None:
        st.info("Data sampel (data/sampel.json) belum ada. Jalankan ulang sel bagian 8.1 di notebook, "
                "lalu salin folder data/ ke sini.")
    else:
        k1, k2 = st.columns([2, 1])
        tampil = k1.radio("Tampilkan sampel", ["Semua", "Training", "Testing"], horizontal=True)
        dengan_poligon = k2.checkbox("Tampilkan poligon sumber", value=True)
        st.caption("Titik Training bergaris tepi putih, titik Testing bergaris tepi hitam. "
                   "Centang atau hilangkan centang kelas di pojok kanan atas peta.")
        components.html(buat_peta_sampel(meta, sampel, tampil, dengan_poligon)._repr_html_(), height=650)

    st.subheader("Jumlah Piksel Training dan Testing")
    tabel = pd.DataFrame(meta["jumlah_piksel"]).set_index("kelas")[KOLOM_PIKSEL]
    tabel.index.name = "Kelas"
    st.dataframe(tabel.style.format({"% Training": "{:.1f}", "% Testing": "{:.1f}",
                                     "Piksel Training (Poligon)": ribuan, "Piksel Testing (Poligon)": ribuan,
                                     "Piksel tersedia di poligon": ribuan}),
                 use_container_width=True)
    st.caption("Satu sampel adalah satu titik (satu piksel). Piksel tersedia di poligon dihitung dari luas poligon "
               "dibagi 100 m2 (piksel 10 m), lalu dibagi sesuai rasio Training dan Testing.")
    st.bar_chart(tabel.drop(index="TOTAL")[["Piksel Training (Poligon)", "Piksel Testing (Poligon)"]])

    st.subheader("Jumlah piksel per sampel")
    f_csv = D / "jumlah_piksel_per_sampel.csv"
    if f_csv.exists():
        per_sampel = pd.read_csv(f_csv)
        pilih = st.multiselect("Filter kelas", meta["kelas"], default=meta["kelas"])
        st.dataframe(per_sampel[per_sampel["kelas"].isin(pilih)], use_container_width=True, hide_index=True)
        st.download_button("Unduh CSV", f_csv.read_bytes(), "jumlah_piksel_per_sampel.csv")
    st.subheader("Fitur yang dipakai model")
    st.write(", ".join(meta["fitur"]))

with tab_model:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Model terbaik", meta["model_terbaik"])
    c2.metric("Akurasi testing", f"{meta['akurasi']:.2%}")
    c3.metric("Kappa", f"{meta['kappa']:.3f}")
    c4.metric("F1 macro", f"{meta['f1_macro']:.3f}")
    st.subheader("Perbandingan model")
    st.dataframe(pd.DataFrame(meta["perbandingan_model"]), hide_index=True, use_container_width=True)
    st.subheader("Metrik per kelas (data testing)")
    st.dataframe(pd.DataFrame(meta["laporan_kelas"]).T.round(3), use_container_width=True)
    st.subheader("Confusion matrix")
    st.dataframe(pd.DataFrame(meta["confusion_matrix"], index=meta["kelas"], columns=meta["kelas"]),
                 use_container_width=True)

with tab_peta:
    opacity = st.slider("Transparansi lapisan klasifikasi", 0.2, 1.0, 0.7, 0.05)
    st.caption("Centang atau hilangkan centang kelas di pojok kanan atas peta.")
    components.html(buat_peta_hasil(meta, opacity)._repr_html_(), height=700)
    st.subheader("Luas hasil klasifikasi")
    st.dataframe(pd.DataFrame(meta["luas"]), hide_index=True, use_container_width=True)
