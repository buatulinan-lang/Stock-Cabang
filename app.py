# -*- coding: utf-8 -*-
"""
Dashboard Cek Stok vs Budget Purchasing - MFlash
Bandingkan nilai stok aktual (HPP) per cabang & kategori terhadap master budget.
"""
import io

import pandas as pd
import streamlit as st

from logic import (
    KATEGORI_BUDGET, KATA_HPP, KATA_KATEGORI, KATA_NILAI, KATA_QTY,
    baca_tabel, bandingkan, cari_kolom, fmt_rp, hitung_status, ke_angka,
    load_budget, tebak_cabang, tebak_kategori,
)

st.set_page_config(page_title="Cek Stok vs Budget - MFlash", page_icon="📦", layout="wide")

load_budget = st.cache_data(load_budget)

# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
budget_df = load_budget()
daftar_cabang = sorted(budget_df["Cabang"].unique())

st.title("📦 Cek Stok vs Budget Purchasing")
st.caption(f"{len(daftar_cabang)} cabang · 4 kategori · total budget {fmt_rp(budget_df['Budget'].sum())}")

with st.sidebar:
    st.header("1. Upload data stok")
    files = st.file_uploader(
        "File stok per cabang (Excel/CSV, bisa banyak sekaligus)",
        type=["xlsx", "xls", "csv"], accept_multiple_files=True,
    )
    st.header("2. Pengaturan")
    toleransi = st.slider("Toleransi 'Sesuai' (± % dari budget)", 0, 25, 5)
    dasar_nilai = st.radio(
        "Dasar nilai stok",
        ["Qty × Harga Beli", "Kolom nilai stok langsung"],
        help="Budget purchasing berbasis HPP, jadi nilai stok dihitung dari harga beli.",
    )
    st.divider()
    st.caption("Cabang TELUK JAMBE otomatis dibaca sebagai KARAWANG.")

if not files:
    st.info("Upload file stok cabang di panel kiri untuk mulai. Master budget sudah terpasang.")
    with st.expander("Lihat master budget"):
        pivot = budget_df.pivot(index="Cabang", columns="Kategori", values="Budget")
        pivot["Total"] = pivot.sum(axis=1)
        st.dataframe(pivot.style.format(fmt_rp), use_container_width=True)
    st.stop()

# --- Baca semua file ---
tabel = {}
gagal = []
for f in files:
    try:
        tabel[f.name] = baca_tabel(f.getvalue(), f.name)
    except Exception as e:  # noqa: BLE001
        gagal.append((f.name, str(e)))
for nama, err in gagal:
    st.error(f"Gagal membaca {nama}: {err}")
if not tabel:
    st.stop()

contoh = next(iter(tabel.values()))
kolom = list(contoh.columns)

st.subheader("Pemetaan kolom")
st.caption("Terdeteksi otomatis dari file pertama — ubah bila salah. Berlaku untuk semua file.")
c1, c2, c3 = st.columns(3)
with c1:
    kol_kat = st.selectbox("Kolom kategori barang", kolom,
                           index=kolom.index(cari_kolom(kolom, KATA_KATEGORI)) if cari_kolom(kolom, KATA_KATEGORI) else 0)
with c2:
    if dasar_nilai == "Qty × Harga Beli":
        kol_qty = st.selectbox("Kolom qty/stok", kolom,
                               index=kolom.index(cari_kolom(kolom, KATA_QTY)) if cari_kolom(kolom, KATA_QTY) else 0)
    else:
        kol_qty = None
        st.selectbox("Kolom qty/stok (opsional)", ["(tidak dipakai)"] + kolom, disabled=True)
with c3:
    kata = KATA_HPP if dasar_nilai == "Qty × Harga Beli" else KATA_NILAI
    label = "Kolom harga beli (HPP)" if dasar_nilai == "Qty × Harga Beli" else "Kolom nilai stok"
    kol_harga = st.selectbox(label, kolom,
                             index=kolom.index(cari_kolom(kolom, kata)) if cari_kolom(kolom, kata) else 0)

# --- Cabang per file ---
st.subheader("Cabang per file")
pilihan_cabang = {}
for nama in tabel:
    tebakan = tebak_cabang(nama, daftar_cabang)
    kols = st.columns([3, 2])
    kols[0].write(f"`{nama}`")
    idx = daftar_cabang.index(tebakan) + 1 if tebakan else 0
    pilihan_cabang[nama] = kols[1].selectbox(
        "cabang", ["(pilih cabang)"] + daftar_cabang, index=idx,
        key=f"cab_{nama}", label_visibility="collapsed",
    )

# --- Pemetaan kategori ---
gabung = []
for nama, df in tabel.items():
    cab = pilihan_cabang[nama]
    if cab == "(pilih cabang)":
        continue
    d = pd.DataFrame({"Cabang": cab, "KategoriAsli": df[kol_kat].astype(str).str.strip()})
    if dasar_nilai == "Qty × Harga Beli":
        d["Qty"] = ke_angka(df[kol_qty])
        d["Harga"] = ke_angka(df[kol_harga])
        d["NilaiStok"] = d["Qty"] * d["Harga"]
    else:
        d["Qty"] = 0
        d["Harga"] = 0
        d["NilaiStok"] = ke_angka(df[kol_harga])
    d["File"] = nama
    gabung.append(d)

if not gabung:
    st.warning("Pilih cabang untuk minimal satu file.")
    st.stop()

stok = pd.concat(gabung, ignore_index=True)
stok = stok[stok["KategoriAsli"].notna() & (stok["KategoriAsli"].str.lower() != "nan")]

kat_unik = sorted(stok["KategoriAsli"].unique())
with st.expander(f"Pemetaan kategori barang ({len(kat_unik)} nilai unik) — cek sebelum baca hasil", expanded=False):
    st.caption("Kategori di file dipetakan ke 4 kategori budget. Yang salah bisa diubah di sini.")
    peta = {}
    kolom_ui = st.columns(3)
    for i, k in enumerate(kat_unik):
        default = tebak_kategori(k)
        opsi = KATEGORI_BUDGET + ["(belum dipetakan)", "(abaikan)"]
        peta[k] = kolom_ui[i % 3].selectbox(
            k, opsi, index=opsi.index(default), key=f"map_{k}",
        )

stok["Kategori"] = stok["KategoriAsli"].map(peta)
belum = stok[stok["Kategori"] == "(belum dipetakan)"]
if len(belum):
    st.warning(
        f"{belum['KategoriAsli'].nunique()} kategori belum dipetakan "
        f"(nilai {fmt_rp(belum['NilaiStok'].sum())}). Buka panel pemetaan kategori di atas."
    )
stok_valid = stok[stok["Kategori"].isin(KATEGORI_BUDGET)]

# --- Perbandingan ---
cabang_aktif = [c for c in pilihan_cabang.values() if c != "(pilih cabang)"]
hasil = bandingkan(stok_valid, budget_df, cabang_aktif, toleransi)


def status(row):
    return hitung_status(row, toleransi)


# --- Ringkasan ---
st.subheader("Ringkasan")
tb, ts = hasil["Budget"].sum(), hasil["NilaiStok"].sum()
m = st.columns(5)
m[0].metric("Total Budget", fmt_rp(tb))
m[1].metric("Total Nilai Stok", fmt_rp(ts))
m[2].metric("Selisih", fmt_rp(ts - tb), f"{(ts / tb * 100 - 100):+.1f}%" if tb else None)
m[3].metric("Baris Over", int((hasil["Status"] == "Over").sum()))
m[4].metric("Baris Kurang", int((hasil["Status"] == "Kurang").sum()))

warna = {"Over": "#c0392b", "Kurang": "#e67e22", "Sesuai": "#27ae60", "Tanpa budget": "#7f8c8d"}


def warnai(s):
    return [f"color: {warna.get(v, '')}; font-weight: 600" for v in s]


tab1, tab2, tab3 = st.tabs(["Per Cabang", "Per Kategori", "Detail Cabang × Kategori"])

with tab1:
    per_cab = hasil.groupby("Cabang", as_index=False).agg(
        Budget=("Budget", "sum"), NilaiStok=("NilaiStok", "sum"))
    per_cab["Selisih"] = per_cab["NilaiStok"] - per_cab["Budget"]
    per_cab["Serapan %"] = (per_cab["NilaiStok"] / per_cab["Budget"] * 100).round(1)
    per_cab["Status"] = per_cab.apply(status, axis=1)
    per_cab = per_cab.sort_values("Selisih")
    st.dataframe(
        per_cab.style.format({"Budget": fmt_rp, "NilaiStok": fmt_rp, "Selisih": fmt_rp,
                              "Serapan %": "{:.1f}%"}).apply(warnai, subset=["Status"]),
        use_container_width=True, hide_index=True,
    )
    st.bar_chart(per_cab.set_index("Cabang")[["Budget", "NilaiStok"]])

with tab2:
    per_kat = hasil.groupby("Kategori", as_index=False).agg(
        Budget=("Budget", "sum"), NilaiStok=("NilaiStok", "sum"))
    per_kat["Selisih"] = per_kat["NilaiStok"] - per_kat["Budget"]
    per_kat["Serapan %"] = (per_kat["NilaiStok"] / per_kat["Budget"] * 100).round(1)
    per_kat["Status"] = per_kat.apply(status, axis=1)
    st.dataframe(
        per_kat.style.format({"Budget": fmt_rp, "NilaiStok": fmt_rp, "Selisih": fmt_rp,
                              "Serapan %": "{:.1f}%"}).apply(warnai, subset=["Status"]),
        use_container_width=True, hide_index=True,
    )
    st.bar_chart(per_kat.set_index("Kategori")[["Budget", "NilaiStok"]])

with tab3:
    f1, f2 = st.columns(2)
    filter_cab = f1.multiselect("Filter cabang", sorted(hasil["Cabang"].unique()))
    filter_st = f2.multiselect("Filter status", ["Over", "Kurang", "Sesuai"])
    tampil = hasil.copy()
    if filter_cab:
        tampil = tampil[tampil["Cabang"].isin(filter_cab)]
    if filter_st:
        tampil = tampil[tampil["Status"].isin(filter_st)]
    st.dataframe(
        tampil.sort_values(["Cabang", "Kategori"]).style.format(
            {"Budget": fmt_rp, "NilaiStok": fmt_rp, "Selisih": fmt_rp,
             "Serapan %": "{:.1f}%", "Qty": "{:,.0f}", "Item": "{:,.0f}"}
        ).apply(warnai, subset=["Status"]),
        use_container_width=True, hide_index=True,
    )

# --- Export ---
st.subheader("Export")
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    hasil.sort_values(["Cabang", "Kategori"]).to_excel(w, sheet_name="Rekap", index=False)
    per_cab.to_excel(w, sheet_name="Per Cabang", index=False)
    per_kat.to_excel(w, sheet_name="Per Kategori", index=False)
    for cab in sorted(hasil["Cabang"].unique()):
        hasil[hasil["Cabang"] == cab].to_excel(w, sheet_name=cab[:31], index=False)
st.download_button("⬇️ Download hasil (Excel multi-sheet)", buf.getvalue(),
                   "cek_stok_vs_budget.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
