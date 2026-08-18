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
KATA_KATEGORI = ["kategori barang", "kategori", "katagori", "jenis", "grup", "group",
                 "klasifikasi"]
KATA_QTY = ["kts (semua gdng)", "kts", "qty", "quantity", "kuantitas", "jumlah", "stok",
            "stock", "saldo", "sisa"]
# kolom harga SATUAN (harus dikali qty)
KATA_HPP = ["nilai satuan", "harga satuan", "harga beli", "hpp", "harga pokok", "modal",
            "cost", "beli"]
# kolom yang SUDAH berupa nilai total (JANGAN dikali qty lagi)
KATA_NILAI = ["nilai total", "nilai persediaan", "total nilai", "subtotal", "jumlah harga",
              "amount", "value", "nilai"]
KATA_JENIS = ["jenis barang", "jenis item", "tipe barang", "item type"]
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


LAINNYA = "Lainnya"

# Kategori sistem yang identik dengan kategori budget.
PADANAN_PERSIS = {
    "aksesoris": "Aksesoris", "accessories": "Aksesoris", "asesoris": "Aksesoris",
    "handphone": "Handphone", "hp": "Handphone", "smartphone": "Handphone",
    "laptop": "Laptop", "notebook": "Laptop",
    "sparepart": "Sparepart", "spare part": "Sparepart", "spare-part": "Sparepart",
}

# Dipakai hanya bila tidak ada padanan persis. Sengaja konservatif: kata kunci
# tingkat produk (lcd, baterai, casing, dst) TIDAK dipakai supaya kategori sistem
# yang tidak dikenal jatuh ke "Lainnya", bukan salah masuk kategori berbudget.
ATURAN_KATEGORI = [
    ("Aksesoris", ["aksesoris", "accessories", "asesoris"]),
    ("Sparepart", ["sparepart", "spare part", "spare-part"]),
    ("Laptop", ["laptop", "notebook", "netbook", "macbook"]),
    ("Handphone", ["handphone", "hand phone", "smartphone", "ponsel", "hape"]),
]


def tebak_kategori(nilai):
    """Kategori sistem -> kategori budget. Yang tak dikenal masuk 'Lainnya' (tanpa budget)."""
    v = str(nilai).strip().lower()
    if v in PADANAN_PERSIS:
        return PADANAN_PERSIS[v]
    for target, kata in ATURAN_KATEGORI:
        for k in kata:
            if k in v:
                return target
    return LAINNYA


def ke_angka(seri):
    """Ubah kolom jadi numerik.

    Nilai yang sudah numerik (hasil baca Excel) dipakai apa adanya — tidak
    di-parse ulang sebagai teks, supaya desimal seperti 253390.625 tidak
    salah dibaca sebagai pemisah ribuan.
    """
    if seri is None:
        return None

    def satu(v):
        if v is None or (isinstance(v, float) and v != v):
            return 0.0
        if isinstance(v, bool):
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        v = re.sub(r"[^\d,.\-]", "", str(v)).strip()
        if v in ("", "-", "."):
            return 0.0
        neg = v.startswith("-")
        v = v.lstrip("-")
        pos_koma, pos_titik = v.rfind(","), v.rfind(".")
        if pos_koma > pos_titik:                    # 1.234.567,89 -> koma desimal
            v = v.replace(".", "").replace(",", ".")
        elif pos_titik > pos_koma:
            ekor = len(v) - pos_titik - 1
            if "," not in v and ekor == 3:          # 1.234.567 -> pemisah ribuan
                v = v.replace(".", "")
            else:                                   # 1,234,567.89
                v = v.replace(",", "")
        else:
            v = v.replace(",", "").replace(".", "")
        try:
            x = float(v)
        except ValueError:
            return 0.0
        return -x if neg else x

    return seri.map(satu).astype(float)


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
    """Gabungkan realisasi stok dengan budget.

    stok_valid: kolom Cabang, Kategori, NilaiStok, Qty, KategoriAsli.
    Kategori di luar 4 kategori berbudget tetap ikut, dengan Budget = 0 dan
    status "Tanpa budget", supaya total nilai stok di ringkasan tetap utuh.
    """
    agg = stok_valid.groupby(["Cabang", "Kategori"], as_index=False).agg(
        NilaiStok=("NilaiStok", "sum"), Qty=("Qty", "sum"), Item=("KategoriAsli", "size"))
    kerangka = budget_df[budget_df["Cabang"].isin(cabang_aktif)]
    hasil = kerangka.merge(agg, on=["Cabang", "Kategori"], how="outer")
    hasil = hasil[hasil["Cabang"].isin(cabang_aktif)]
    hasil[["Budget", "NilaiStok", "Qty", "Item"]] = hasil[
        ["Budget", "NilaiStok", "Qty", "Item"]].fillna(0)
    hasil["Selisih"] = hasil["NilaiStok"] - hasil["Budget"]
    aman = hasil["Budget"].where(hasil["Budget"] != 0)
    hasil["Serapan %"] = (hasil["NilaiStok"] / aman * 100).round(1)
    hasil["Status"] = hasil.apply(lambda r: hitung_status(r, toleransi), axis=1)
    urut = {k: i for i, k in enumerate(KATEGORI_BUDGET + [LAINNYA])}
    hasil = hasil.sort_values(
        ["Cabang", "Kategori"], key=lambda c: c.map(urut) if c.name == "Kategori" else c
    ).reset_index(drop=True)
    return hasil
