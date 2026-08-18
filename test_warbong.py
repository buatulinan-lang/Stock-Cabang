import warnings, pandas as pd, logic
warnings.filterwarnings("ignore")
P="/root/.claude/uploads/d7f21ad4-f096-5389-b2b1-b6e0a81ddcd6/74e4d9db-daftar_barang_dan_jasa_010mflashwarbon_260818214205.xlsx"
NAMA="daftar_barang_dan_jasa_010mflashwarbon_260818214205.xlsx"
raw=open(P,'rb').read()
bdf=logic.load_budget(); cab=sorted(bdf["Cabang"].unique())

t=logic.baca_tabel(raw, NAMA)
print("kolom:", [c for c in t.columns if not c.startswith("kolom_")])
kolom=list(t.columns)
kk=logic.cari_kolom(kolom, logic.KATA_KATEGORI)
kn=logic.cari_kolom(kolom, logic.KATA_NILAI)
kq=logic.cari_kolom(kolom, logic.KATA_QTY)
ks=logic.cari_kolom(kolom, logic.KATA_HPP)
kj=logic.cari_kolom(kolom, logic.KATA_JENIS)
print("auto-detect -> kategori:",kk,"| nilai total:",kn,"| qty:",kq,"| satuan:",ks,"| jenis:",kj)
assert (kk,kn,kq,ks,kj)==("Kategori Barang","Nilai Total","Kts (Semua Gdng)","Nilai Satuan","Jenis Barang")

c=logic.tebak_cabang(NAMA, cab); print("cabang:",c); assert c=="WARBONG"

d=pd.DataFrame({"Cabang":c,"KategoriAsli":t[kk].astype(str).str.strip()})
d["NilaiStok"]=logic.ke_angka(t[kn]); d["Qty"]=logic.ke_angka(t[kq])
jenis=t[kj].astype(str).str.strip().str.lower()
d=d[jenis.eq("inventory").values]
print("baris inventory:",len(d))
print("TOTAL NILAI STOK :", f"{d['NilaiStok'].sum():,.0f}")
assert abs(d["NilaiStok"].sum()-384_002_787)<1, d["NilaiStok"].sum()

# mode salah (qty x nilai total) -> harus jauh berbeda; ini yang bikin 1 M
salah=(logic.ke_angka(t[kq])*logic.ke_angka(t[kn])).sum()
print("kalau qty x Nilai Total (salah):", f"{salah:,.0f}")

d["Kategori"]=d["KategoriAsli"].map(logic.tebak_kategori)
print(d.groupby("Kategori")["NilaiStok"].sum().map("{:,.0f}".format))
h=logic.bandingkan(d,bdf,[c],5)
print(h.to_string(index=False))
assert abs(h["NilaiStok"].sum()-384_002_787)<1
bb=h[h["Kategori"].isin(logic.KATEGORI_BUDGET)]
print("\nbudget WARBONG:", f"{bb['Budget'].sum():,.0f}", "| stok berbudget:", f"{bb['NilaiStok'].sum():,.0f}",
      "| Lainnya:", f"{h[h.Kategori=='Lainnya']['NilaiStok'].sum():,.0f}")
assert abs(bb["Budget"].sum()-281_542_000)<1
print("\nTES WARBONG LULUS")
