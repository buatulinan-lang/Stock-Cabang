# -*- coding: utf-8 -*-
"""
Dashboard Cek Stok vs Budget Purchasing — MFlash
Bandingkan nilai stok aktual (HPP) per cabang & kategori terhadap master budget.
Sumber data: folder `data/` di repo (permanen) dan/atau upload manual (sementara).
"""
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from logic import (
    KATEGORI_BUDGET, KATA_HPP, KATA_JENIS, KATA_KATEGORI, KATA_NILAI, KATA_QTY, LAINNYA,
    baca_tabel, bandingkan, cari_kolom, fmt_rp, hitung_status, ke_angka, load_budget,
    tebak_cabang, tebak_kategori,
)

st.set_page_config(page_title="Cek Stok vs Budget — MFlash", page_icon="📦", layout="wide")
BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
EKSTENSI = (".xlsx", ".xls", ".csv", ".gz")

budget_df = st.cache_data(load_budget)()
daftar_cabang = sorted(budget_df["Cabang"].unique())

st.title("📦 Cek Stok vs Budget Purchasing")
st.caption(f"{len(daftar_cabang)} cabang · 4 kategori berbudget · "
           f"total budget {fmt_rp(budget_df['Budget'].sum())}")

# ---------------------------------------------------------------- sumber data
with st.sidebar:
    st.header("Sumber data")
    file_repo = sorted(p for p in DATA_DIR.glob("*") if p.suffix.lower() in EKSTENSI) \
        if DATA_DIR.exists() else []
    if file_repo:
        st.success(f"{len(file_repo)} file terbaca dari folder `data/` di repo.")
    else:
        st.info("Folder `data/` kosong. Taruh file stok cabang di sana lalu push ke GitHub, "
                "atau upload manual di bawah.")
    unggah = st.file_uploader("Upload tambahan (opsional)", type=["xlsx", "xls", "csv"],
                              accept_multiple_files=True)

    st.header("Pengaturan")
    toleransi = st.slider("Toleransi 'Sesuai' (± % dari budget)", 0, 25, 5)
    hanya_inventory = st.checkbox(
        "Hitung baris Inventory saja", value=True,
        help="Baris Service / Non Inventory bukan persediaan, jadi dikeluarkan dari nilai stok.")
    st.caption("Cabang TELUK JAMBE otomatis dibaca sebagai KARAWANG.")


@st.cache_data(show_spinner=False)
def muat(nama, isi):
    return baca_tabel(isi, nama)


sumber = {}
for p in file_repo:
    sumber[p.name] = ("repo", p.read_bytes())
for f in (unggah or []):
    sumber[f.name] = ("upload", f.getvalue())

if not sumber:
    st.info("Belum ada data stok. Isi folder `data/` atau upload file di panel kiri.")
    with st.expander("Lihat master budget"):
        pv = budget_df.pivot(index="Cabang", columns="Kategori", values="Budget")
        pv["Total"] = pv.sum(axis=1)
        st.dataframe(pv.style.format(fmt_rp), use_container_width=True)
    st.stop()

tabel = {}
for nama, (asal, isi) in sumber.items():
    try:
        tabel[nama] = muat(nama, isi)
    except Exception as e:  # noqa: BLE001
        st.error(f"Gagal membaca {nama}: {e}")
if not tabel:
    st.stop()

# ------------------------------------------------------------ pemetaan kolom
contoh = next(iter(tabel.values()))
kolom = list(contoh.columns)
kol_nilai_auto = cari_kolom(kolom, KATA_NILAI)
kol_satuan_auto = cari_kolom(kolom, KATA_HPP)
kol_qty_auto = cari_kolom(kolom, KATA_QTY)
kol_kat_auto = cari_kolom(kolom, KATA_KATEGORI)
kol_jenis_auto = cari_kolom(kolom, KATA_JENIS)

st.subheader("Pemetaan kolom")
mode_default = 0 if kol_nilai_auto else 1
mode = st.radio(
    "Dasar nilai stok",
    ["Pakai kolom nilai total (sudah qty × harga)", "Hitung sendiri: Qty × Harga Satuan"],
    index=mode_default, horizontal=True,
    help="Kalau file sudah punya kolom 'Nilai Total', jangan dikali qty lagi — itu bikin "
         "nilai stok menggelembung.",
)


def idx(nama):
    return kolom.index(nama) if nama in kolom else 0


c1, c2, c3 = st.columns(3)
kol_kat = c1.selectbox("Kolom kategori barang", kolom, index=idx(kol_kat_auto))
if mode.startswith("Pakai kolom nilai total"):
    kol_nilai = c2.selectbox("Kolom nilai total stok", kolom, index=idx(kol_nilai_auto))
    kol_qty = c3.selectbox("Kolom qty (untuk info saja)", ["(tidak dipakai)"] + kolom,
                           index=(kolom.index(kol_qty_auto) + 1) if kol_qty_auto else 0)
    kol_satuan = None
else:
    kol_qty = c2.selectbox("Kolom qty/stok", kolom, index=idx(kol_qty_auto))
    kol_satuan = c3.selectbox("Kolom harga satuan (HPP)", kolom, index=idx(kol_satuan_auto))
    kol_nilai = None
    if any(k in str(kol_satuan).lower() for k in ("total", "nilai total", "subtotal")):
        st.error(f"Kolom **{kol_satuan}** kelihatannya sudah berupa nilai total. "
                 "Mengalikannya dengan qty akan menggandakan nilai stok — pilih kolom "
                 "harga satuan, atau ganti ke mode 'Pakai kolom nilai total'.")

kol_jenis = st.selectbox(
    "Kolom jenis barang (filter Inventory)", ["(tidak ada)"] + kolom,
    index=(kolom.index(kol_jenis_auto) + 1) if kol_jenis_auto else 0,
    disabled=not hanya_inventory,
)

# ------------------------------------------------------------ cabang per file
def kolom_cabang(df):
    """File gabungan sudah punya kolom Cabang -> tidak perlu ditebak dari nama file."""
    for c in df.columns:
        if str(c).strip().lower() == "cabang":
            return c
    return None


st.subheader("Cabang")
pilihan = {}
gabungan = {n: kolom_cabang(d) for n, d in tabel.items()}
for nama, df in tabel.items():
    k = st.columns([3, 2, 1])
    k[0].write(f"`{nama}`")
    if gabungan[nama]:
        n_cab = df[gabungan[nama]].nunique()
        k[1].success(f"file gabungan — {n_cab} cabang dari kolom `{gabungan[nama]}`")
        pilihan[nama] = "(dari kolom)"
    else:
        tebakan = tebak_cabang(nama, daftar_cabang)
        pilihan[nama] = k[1].selectbox(
            "cabang", ["(lewati)"] + daftar_cabang,
            index=daftar_cabang.index(tebakan) + 1 if tebakan else 0,
            key=f"cab_{nama}", label_visibility="collapsed")
    k[2].caption(sumber[nama][0])

# ------------------------------------------------------------------ olah data
bagian, catatan = [], []
for nama, df in tabel.items():
    cab = pilihan[nama]
    if cab == "(lewati)":
        continue
    kol_cab = gabungan[nama]
    seri_cab = (df[kol_cab].astype(str).str.strip().str.upper() if kol_cab else cab)
    d = pd.DataFrame({"Cabang": seri_cab, "KategoriAsli": df[kol_kat].astype(str).str.strip()})
    total_baris = len(d)
    if kol_nilai:
        d["NilaiStok"] = ke_angka(df[kol_nilai])
        d["Qty"] = ke_angka(df[kol_qty]) if kol_qty != "(tidak dipakai)" else 0
    else:
        d["Qty"] = ke_angka(df[kol_qty])
        d["NilaiStok"] = d["Qty"] * ke_angka(df[kol_satuan])
    dibuang = 0
    if hanya_inventory and kol_jenis != "(tidak ada)":
        jenis = df[kol_jenis].astype(str).str.strip().str.lower()
        masuk = jenis.eq("inventory")
        dibuang = int((~masuk).sum())
        d = d[masuk.values]
    d["File"] = nama
    bagian.append(d)
    catatan.append({"File": nama,
                    "Cabang": f"{d['Cabang'].nunique()} cabang" if kol_cab else cab,
                    "Baris": total_baris,
                    "Baris non-Inventory dibuang": dibuang,
                    "Nilai stok terbaca": d["NilaiStok"].sum()})

if not bagian:
    st.warning("Belum ada file yang dipetakan ke cabang.")
    st.stop()

stok = pd.concat(bagian, ignore_index=True)
stok = stok[stok["KategoriAsli"].str.lower().ne("nan")]

# --------------------------------------------------------- pemetaan kategori
kat_unik = sorted(stok["KategoriAsli"].unique())
with st.expander(f"Pemetaan kategori ({len(kat_unik)} kategori sistem)", expanded=False):
    st.caption("Kategori di luar 4 kategori berbudget masuk **Lainnya** — tetap dihitung "
               "di total nilai stok, hanya tidak punya budget pembanding.")
    peta, ui = {}, st.columns(3)
    for i, k in enumerate(kat_unik):
        opsi = KATEGORI_BUDGET + [LAINNYA, "(abaikan)"]
        peta[k] = ui[i % 3].selectbox(k, opsi, index=opsi.index(tebak_kategori(k)),
                                      key=f"map_{k}")

stok["Kategori"] = stok["KategoriAsli"].map(peta)
stok = stok[stok["Kategori"] != "(abaikan)"]

cabang_aktif = sorted(set(stok["Cabang"]) & set(daftar_cabang))
tak_dikenal = sorted(set(stok["Cabang"]) - set(daftar_cabang))
if tak_dikenal:
    st.warning(f"Nama cabang tidak ada di master budget, diabaikan: {', '.join(tak_dikenal)}")
    stok = stok[stok["Cabang"].isin(cabang_aktif)]
hasil = bandingkan(stok, budget_df, cabang_aktif, toleransi)

# --------------------------------------------------------------- validasi
nilai_terbaca = pd.DataFrame(catatan)["Nilai stok terbaca"].sum()
selisih_baca = hasil["NilaiStok"].sum() - nilai_terbaca
with st.expander("🔍 Validasi pembacaan file (cocokkan dengan total di file asli)", expanded=False):
    st.dataframe(
        pd.DataFrame(catatan).style.format({"Nilai stok terbaca": fmt_rp}),
        use_container_width=True, hide_index=True)
    st.caption(f"Total nilai stok terbaca dari file: **{fmt_rp(nilai_terbaca)}**. "
               f"Yang masuk dashboard: **{fmt_rp(hasil['NilaiStok'].sum())}** "
               f"(selisih {fmt_rp(selisih_baca)} — dari kategori yang di-abaikan).")

# --------------------------------------------------------------- ringkasan
berbudget = hasil[hasil["Kategori"].isin(KATEGORI_BUDGET)]
lainnya = hasil[hasil["Kategori"] == LAINNYA]
tb, ts = berbudget["Budget"].sum(), berbudget["NilaiStok"].sum()

st.subheader("Ringkasan")
m = st.columns(5)
m[0].metric("Total Budget (4 kategori)", fmt_rp(tb))
m[1].metric("Nilai Stok (4 kategori)", fmt_rp(ts),
            f"{(ts / tb * 100 - 100):+.1f}%" if tb else None)
m[2].metric("Nilai Stok Lainnya", fmt_rp(lainnya["NilaiStok"].sum()))
m[3].metric("Total Nilai Stok", fmt_rp(hasil["NilaiStok"].sum()))
m[4].metric("Selisih vs Budget", fmt_rp(ts - tb))

warna = {"Over": "#c0392b", "Kurang": "#e67e22", "Sesuai": "#27ae60", "Tanpa budget": "#7f8c8d"}
fmt_tabel = {"Budget": fmt_rp, "NilaiStok": fmt_rp, "Selisih": fmt_rp,
             "Serapan %": "{:.1f}%", "Qty": "{:,.0f}", "Item": "{:,.0f}"}


def warnai(s):
    return [f"color: {warna.get(v, '')}; font-weight: 600" for v in s]


def gaya(df):
    kols = {k: v for k, v in fmt_tabel.items() if k in df.columns}
    return df.style.format(kols, na_rep="—").apply(warnai, subset=["Status"])


t1, t2, t3 = st.tabs(["Per Cabang", "Per Kategori", "Detail Cabang × Kategori"])

with t1:
    per_cab = berbudget.groupby("Cabang", as_index=False).agg(
        Budget=("Budget", "sum"), NilaiStok=("NilaiStok", "sum"))
    lain_cab = lainnya.groupby("Cabang")["NilaiStok"].sum()
    per_cab["Stok Lainnya"] = per_cab["Cabang"].map(lain_cab).fillna(0)
    per_cab["Selisih"] = per_cab["NilaiStok"] - per_cab["Budget"]
    per_cab["Serapan %"] = (per_cab["NilaiStok"] / per_cab["Budget"] * 100).round(1)
    per_cab["Status"] = per_cab.apply(lambda r: hitung_status(r, toleransi), axis=1)
    per_cab = per_cab.sort_values("Selisih")
    st.dataframe(gaya(per_cab).format({"Stok Lainnya": fmt_rp}),
                 use_container_width=True, hide_index=True)
    st.bar_chart(per_cab.set_index("Cabang")[["Budget", "NilaiStok"]])
    st.caption("Budget & selisih hanya menghitung 4 kategori berbudget; "
               "kolom Stok Lainnya ditampilkan terpisah.")

with t2:
    per_kat = hasil.groupby("Kategori", as_index=False).agg(
        Budget=("Budget", "sum"), NilaiStok=("NilaiStok", "sum"))
    per_kat["Selisih"] = per_kat["NilaiStok"] - per_kat["Budget"]
    per_kat["Serapan %"] = (per_kat["NilaiStok"] /
                            per_kat["Budget"].where(per_kat["Budget"] != 0) * 100).round(1)
    per_kat["Status"] = per_kat.apply(lambda r: hitung_status(r, toleransi), axis=1)
    st.dataframe(gaya(per_kat), use_container_width=True, hide_index=True)
    st.bar_chart(per_kat.set_index("Kategori")[["Budget", "NilaiStok"]])

with t3:
    f1, f2 = st.columns(2)
    fc = f1.multiselect("Filter cabang", sorted(hasil["Cabang"].unique()))
    fs = f2.multiselect("Filter status", ["Over", "Kurang", "Sesuai", "Tanpa budget"])
    tampil = hasil
    if fc:
        tampil = tampil[tampil["Cabang"].isin(fc)]
    if fs:
        tampil = tampil[tampil["Status"].isin(fs)]
    st.dataframe(gaya(tampil), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------- export
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    hasil.to_excel(w, sheet_name="Rekap", index=False)
    per_cab.to_excel(w, sheet_name="Per Cabang", index=False)
    per_kat.to_excel(w, sheet_name="Per Kategori", index=False)
    pd.DataFrame(catatan).to_excel(w, sheet_name="Validasi", index=False)
    for cab in sorted(hasil["Cabang"].unique()):
        hasil[hasil["Cabang"] == cab].to_excel(w, sheet_name=cab[:31], index=False)
st.download_button("⬇️ Download hasil (Excel multi-sheet)", buf.getvalue(),
                   "cek_stok_vs_budget.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
