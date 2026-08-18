# -*- coding: utf-8 -*-
"""Logika inti dashboard cek stok vs budget (tanpa dependensi Streamlit)."""
import io
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
KATEGORI_BUDGET = ["Aksesoris", "Handphone", "Laptop", "Sparepart"]


# ----------------------------------------------------------------------------
# Master budget
# ----------------------------------------------------------------------------
def load_budget():
    with open(BASE / "budget_master.json", encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for cabang, kats in data.items():
        for kat, val in kats.items():
            rows.append({"Cabang": cabang, "Kategori": kat, "Budget": float(val)})
    return pd.DataFrame(rows)


# Alias nama cabang -> nama resmi di master budget.
# Kunci ditulis tanpa spasi/underscore, huruf kecil.
ALIAS_CABANG = {
    "telukjambe": "KARAWANG",
    "tlkjambe": "KARAWANG",
    "karawang": "KARAWANG",
    "klender": "KLENDER",
    "klende": "KLENDER",
    "radjiman": "RADJIMAN",
    "rajiman": "RADJIMAN",
    "condet": "CONDET",
    "warbong": "WARBONG",
    "waringinbongsang": "WARBONG",
    "cilangkap": "CILANGKAP",
    "ceger": "CEGER",
    "jatimulya": "JATIMULYA",
    "jatibening": "JATIBENING",
    "cinere": "CINERE",
    "jatiwaringin": "JATIWARINGIN",
    "pejaten": "PEJATEN",
    "bintara": "BINTARA",
    "dramaga": "DRAMAGA",
    "sawangan": "SAWANGAN",
    "cibinong": "CIBINONG",
    "cikampek": "CIKAMPEK",
    "cibubur": "CIBUBUR",
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tebak_cabang(nama_file, daftar_cabang):
    n = norm(nama_file)
    kandidat = []
    for alias, resmi in ALIAS_CABANG.items():
        if resmi in daftar_cabang and alias in n:
            kandidat.append((len(alias), resmi))
    if kandidat:
        return sorted(kandidat, reverse=True)[0][1]
    for cab in daftar_cabang:
        c = norm(cab)
        for potong in range(len(c), 4, -1):
            if c[:potong] in n:
                return cab
    return None


# ----------------------------------------------------------------------------
# Deteksi kolom & kategori
# ----------------------------------------------------------------------------
KATA_KATEGORI = ["kategori", "katagori", "jenis", "grup", "group", "klasifikasi", "tipe barang"]
KATA_QTY = ["qty", "quantity", "jumlah", "stok", "stock", "saldo", "sisa"]
KATA_HPP = ["harga beli", "hpp", "harga pokok", "modal", "cost", "beli"]
KATA_NILAI = ["nilai", "total", "subtotal", "jumlah harga", "amount", "value"]
KATA_ITEM = ["nama barang", "item", "produk", "deskripsi", "barang", "sku"]


def cari_kolom(cols, kata_kunci):
    low = [str(c).lower().strip() for c in cols]
    for kk in kata_kunci:
        for c, l in zip(cols, low):
            if l == kk:
                return c
    for kk in kata_kunci:
        for c, l in zip(cols, low):
            if kk in l:
                return c
    return None


def baca_tabel(file_bytes, nama_file):
    """Baca Excel/CSV, cari baris header otomatis."""
    kunci = KATA_KATEGORI + KATA_QTY + KATA_HPP + KATA_NILAI + KATA_ITEM
    if nama_file.lower().endswith((".csv", ".txt")):
        mentah = pd.read_csv(io.BytesIO(file_bytes), header=None, dtype=object,
                             sep=None, engine="python")
    else:
        mentah = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=object)

    baris_header = 0
    skor_terbaik = 0
    for i in range(min(25, len(mentah))):
        nilai = [str(v).lower().strip() for v in mentah.iloc[i].tolist() if pd.notna(v)]
        skor = sum(1 for v in nilai for k in kunci if k in v)
        if skor > skor_terbaik:
            skor_terbaik, baris_header = skor, i

    df = mentah.iloc[baris_header + 1:].copy()
    df.columns = [str(c).strip() if pd.notna(c) else f"kolom_{j}"
                  for j, c in enumerate(mentah.iloc[baris_header].tolist())]
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.dropna(how="all").reset_index(drop=True)
    return df


ATURAN_KATEGORI = [
    ("Aksesoris", ["aksesoris", "accessories", "asesoris", "casing", "case", "charger",
                   "kabel", "headset", "tempered", "anti gores", "antigores", "powerbank",
                   "power bank", "adaptor", "holder", "earphone", "softcase", "hardcase"]),
    ("Sparepart", ["sparepart", "spare part", "spare-part", "part", "lcd", "baterai",
                   "battery", "board", "konektor", "connector", "flexible", "fleksibel",
                   "mesin", "modul", "ic ", "touchscreen", "keyboard"]),
    ("Laptop", ["laptop", "notebook", "netbook", "macbook", "komputer", "pc "]),
    ("Handphone", ["handphone", "hand phone", "smartphone", "ponsel", "phone", "tablet",
                   "hape", "hp ", " hp"]),
]


def tebak_kategori(nilai):
    v = f" {str(nilai).lower().strip()} "
    for target, kata in ATURAN_KATEGORI:
        for k in kata:
            if k in v:
                return target
    return "(belum dipetakan)"


def ke_angka(seri):
    """Ubah teks angka (format Indonesia maupun internasional) jadi numerik."""
    if seri is None:
        return None
    s = seri.astype(str).str.replace(r"[^\d,.\-]", "", regex=True).str.strip()

    def satu(v):
        if not isinstance(v, str):
            return 0.0
        if v in ("", "-", "nan", "None"):
            return 0.0
        neg = v.startswith("-")
        v = v.lstrip("-")
        pos_koma, pos_titik = v.rfind(","), v.rfind(".")
        if pos_koma > pos_titik:            # 1.234.567,89 -> koma = desimal
            v = v.replace(".", "").replace(",", ".")
        elif pos_titik > pos_koma:
            ekor = len(v) - pos_titik - 1
            if ekor == 3 and v.count(".") >= 1 and "," not in v:
                v = v.replace(".", "")      # 1.234.567 -> pemisah ribuan
            else:
                v = v.replace(",", "")      # 1,234,567.89
        else:
            v = v.replace(",", "").replace(".", "")
        try:
            x = float(v)
        except ValueError:
            return 0.0
        return -x if neg else x

    return s.map(satu).astype(float)


def fmt_rp(x):
    try:
        return "Rp " + f"{float(x):,.0f}".replace(",", ".")
    except Exception:
        return "-"




def hitung_status(row, toleransi):
    if row["Budget"] == 0:
        return "Tanpa budget"
    d = row["Selisih"] / row["Budget"] * 100
    if d > toleransi:
        return "Over"
    if d < -toleransi:
        return "Kurang"
    return "Sesuai"


def bandingkan(stok_valid, budget_df, cabang_aktif, toleransi=5):
    """stok_valid: kolom Cabang, Kategori, NilaiStok, Qty, KategoriAsli."""
    agg = stok_valid.groupby(["Cabang", "Kategori"], as_index=False).agg(
        NilaiStok=("NilaiStok", "sum"), Qty=("Qty", "sum"), Item=("KategoriAsli", "size"))
    hasil = budget_df[budget_df["Cabang"].isin(cabang_aktif)].merge(
        agg, on=["Cabang", "Kategori"], how="left")
    hasil[["NilaiStok", "Qty", "Item"]] = hasil[["NilaiStok", "Qty", "Item"]].fillna(0)
    hasil["Selisih"] = hasil["NilaiStok"] - hasil["Budget"]
    hasil["Serapan %"] = (hasil["NilaiStok"] / hasil["Budget"] * 100).round(1)
    hasil["Status"] = hasil.apply(lambda r: hitung_status(r, toleransi), axis=1)
    return hasil
