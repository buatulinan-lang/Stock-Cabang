import random, io
import pandas as pd
import logic

bdf = logic.load_budget()
cab = sorted(bdf["Cabang"].unique())
assert len(cab) == 18, cab
assert abs(bdf["Budget"].sum() - 6_919_262_000) < 1, bdf["Budget"].sum()
print("budget OK:", len(cab), "cabang, total", logic.fmt_rp(bdf["Budget"].sum()))

# deteksi cabang dari nama file ala JasperReports
tes = {
 "rincian_stok_001mflashklende_20260818.xlsx": "KLENDER",
 "stok_teluk_jambe_agustus.xlsx": "KARAWANG",
 "STOK TELUKJAMBE 2026.xls": "KARAWANG",
 "laporan-stok-jatiwaringin.csv": "JATIWARINGIN",
 "stok_jatimulya_0823.xlsx": "JATIMULYA",
 "stok_jatibening.xlsx": "JATIBENING",
 "rincian_cibubur.xlsx": "CIBUBUR",
 "004mflashradjiman.xlsx": "RADJIMAN",
}
for f, exp in tes.items():
    got = logic.tebak_cabang(f, cab)
    assert got == exp, (f, got, exp)
print("deteksi cabang OK")

# parser angka format Indonesia & internasional
s = pd.Series(["1.234.567", "Rp 2.500.000,50", "3,000", "1500", "-", None])
print("angka:", list(logic.ke_angka(s)))

# kategori
for v, exp in [("HANDPHONE","Handphone"),("Sparepart LCD","Sparepart"),("Aksesoris HP","Aksesoris"),
               ("LAPTOP / NOTEBOOK","Laptop"),("Voucher Pulsa","Lainnya"),("ELEKTRONIK","Lainnya"),("KARTU PERDANA","Lainnya")]:
    got = logic.tebak_kategori(v)
    assert got == exp, (v, got, exp)
print("kategori OK")

# ---- generate dummy export 18 cabang, dengan header nyampah 3 baris ----
random.seed(7)
kat_asli = ["HANDPHONE","LAPTOP","SPAREPART","AKSESORIS","ELEKTRONIK"]
frames = []
for c in cab:
    rows = []
    for i in range(60):
        k = random.choice(kat_asli)
        rows.append({"No": i+1, "Nama Barang": f"{k} item {i}", "Kategori Barang": k,
                     "Qty": random.randint(1,40), "Harga Beli": random.randrange(50_000, 8_000_000, 50_000),
                     "Harga Jual": 0})
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame([["LAPORAN STOK"],["Periode 24 Jul - 23 Agu 2026"],[""]]).to_excel(w, index=False, header=False, startrow=0)
        df.to_excel(w, index=False, startrow=3)
    raw = buf.getvalue()
    t = logic.baca_tabel(raw, f"stok_{c.lower()}.xlsx")
    assert "Kategori Barang" in t.columns, t.columns.tolist()
    t["Cabang"] = c
    t["KategoriAsli"] = t["Kategori Barang"]
    t["Qty"] = logic.ke_angka(t["Qty"]); t["Harga"] = logic.ke_angka(t["Harga Beli"])
    t["NilaiStok"] = t["Qty"]*t["Harga"]
    t["Kategori"] = t["KategoriAsli"].map(logic.tebak_kategori)
    frames.append(t)
stok = pd.concat(frames, ignore_index=True)
print("header auto-detect OK; baris stok:", len(stok), "| Lainnya:", (stok["Kategori"]==logic.LAINNYA).sum())

sv = stok[stok["Kategori"].isin(logic.KATEGORI_BUDGET + [logic.LAINNYA])]
hasil = logic.bandingkan(sv, bdf, cab, toleransi=5)
assert len(hasil) == 90, len(hasil)  # 18 cabang x (4 kategori + Lainnya)
assert abs(hasil["Budget"].sum() - 6_919_262_000) < 1
assert abs(hasil["NilaiStok"].sum() - sv["NilaiStok"].sum()) < 1, "total nilai stok harus utuh"
assert set(hasil["Status"]) <= {"Over","Kurang","Sesuai","Tanpa budget"}
print(hasil["Status"].value_counts().to_dict())
print(hasil.head(6).to_string(index=False))

# cabang tanpa data stok -> harus muncul sebagai Kurang, nilai 0
h2 = logic.bandingkan(sv[sv["Cabang"]!="CONDET"], bdf, cab, 5)
row = h2[(h2["Cabang"]=="CONDET") & (h2["Kategori"].isin(logic.KATEGORI_BUDGET))]
assert (row["NilaiStok"]==0).all() and (row["Status"]=="Kurang").all()
print("cabang tanpa data OK")
print("\nSEMUA TES LULUS")
