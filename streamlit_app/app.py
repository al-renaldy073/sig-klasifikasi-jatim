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

st.set_page_config(page_title="SIG Klasifikasi Lahan Jawa Timur", layout="wide")


@st.cache_data
def muat():
    return json.loads((D / "meta.json").read_text(encoding="utf-8"))


def swatch(nama, warna):
    return (f'<span style="background:{warna};opacity:.85;display:inline-block;width:12px;'
            f'height:12px;border:1px solid #333"></span> {nama}')


def buat_peta(meta, opacity):
    m = folium.Map(location=meta["pusat"], zoom_start=8, tiles=None, control_scale=True)
    folium.TileLayer(GOOGLE_SAT, attr="Google", name="Satelit Google", max_zoom=20).add_to(m)
    folium.TileLayer(GOOGLE_HYB, attr="Google", name="Satelit + label Google", max_zoom=20, show=False).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
    Fullscreen().add_to(m)
    for lap in meta["lapisan"]:   # satu lapisan per kelas -> kotak centang di pojok kanan atas
        fg = folium.FeatureGroup(name=swatch(lap["kelas"], lap["warna"]), show=True).add_to(m)
        ImageOverlay(image=str(D / lap["png"]), bounds=lap["bounds"], opacity=opacity,
                     interactive=False, zindex=5).add_to(fg)
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    return m


if not (D / "meta.json").exists():
    st.error("Folder data/ belum ada. Jalankan notebook sampai bagian 8.1 lalu salin streamlit_app/ ke sini.")
    st.stop()

meta = muat()
st.title(meta["judul"])
st.caption(f"UTS Sistem Informasi Geografis | citra {meta['periode'][0]} s/d {meta['periode'][1]} | "
           f"resolusi peta {meta['skala_peta_m']} m")

tab_data, tab_model, tab_peta = st.tabs(["Data dan jumlah piksel", "Model dan akurasi", "Peta hasil"])

with tab_data:
    st.subheader("Jumlah piksel training dan testing per kelas")
    st.dataframe(pd.DataFrame(meta["jumlah_piksel"]).set_index("kelas"), use_container_width=True)
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
    components.html(buat_peta(meta, opacity)._repr_html_(), height=700)
    st.subheader("Luas hasil klasifikasi")
    st.dataframe(pd.DataFrame(meta["luas"]), hide_index=True, use_container_width=True)
