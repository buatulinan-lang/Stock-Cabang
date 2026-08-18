"""Gabungkan export 'Daftar Barang dan Jasa' semua cabang jadi satu CSV."""
import glob, os, re, sys, warnings
import pandas as pd
import logic
warnings.filterwarnings("ignore")

SRC = sys.argv[1] if len(sys.argv) > 1 else "/root/.claude/uploads/d7f21ad4-f096-5389-b2b1-b6e0a81ddcd6"
OUT = sys.argv[2] if len(sys.argv) > 2 else "stok_gabungan.csv"
cab_master = sorted(logic.load_budget()["Cabang"].unique())

frames, log, dilihat = [], [], {}
for p in sorted(glob.glob(os.path.join(SRC, "*daftar_barang*"))):
    nama = re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(p))
    kode = re.search(r"_(\d{3})mflash", nama)
    kode = kode.group(1) if kode else ""
    cab = logic.tebak_cabang(nama, cab_master)
    kunci = (kode, cab)
    if kunci in dilihat:                       # file kembar (uuid beda, isi sama)
        log.append({"Kode": kode, "Cabang": cab, "File": nama, "Baris": 0,
                    "Nilai Total": 0, "Catatan": "duplikat, dilewati"})
        continue
    dilihat[kunci] = nama
    df = logic.baca_tabel(open(p, "rb").read(), nama)
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("kolom_")]]
    df.insert(0, "Cabang", cab)
    df.insert(1, "Kode Cabang", kode)
    df["File Sumber"] = nama
    for k in ("Kts (Semua Gdng)", "Nilai Satuan", "Nilai Total"):
        if k in df.columns:
            df[k] = logic.ke_angka(df[k])
    df["Kategori Budget"] = df["Kategori Barang"].map(logic.tebak_kategori)
    frames.append(df)
    log.append({"Kode": kode, "Cabang": cab, "File": nama, "Baris": len(df),
                "Nilai Total": df["Nilai Total"].sum(), "Catatan": ""})

gab = pd.concat(frames, ignore_index=True)
gab.to_csv(OUT, index=False)
ringkas = pd.DataFrame(log)
print(ringkas.to_string(index=False))
print(f"\nTotal baris: {len(gab):,} | total nilai: {gab['Nilai Total'].sum():,.0f}")
print("Cabang belum ada:", [c for c in cab_master if c not in set(gab['Cabang'])])
ringkas.to_csv("ringkasan_per_file.csv", index=False)
