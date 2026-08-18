# Dashboard Cek Stok vs Budget Purchasing — MFlash

Membandingkan **nilai stok aktual (HPP)** tiap cabang & kategori terhadap **master budget purchasing**
(18 cabang × 4 kategori, total Rp 6.919.262.000), lalu menandai status **Kurang / Sesuai / Over**.

## Isi
- `app.py` — antarmuka Streamlit
- `logic.py` — logika inti (parsing file, deteksi cabang, pemetaan kategori, perbandingan)
- `budget_master.json` — master budget hasil ekstraksi dari *Master Budget Purchasing MFlash.xlsx*
- `test_logic.py` — uji otomatis logika inti
- `requirements.txt`

## Menjalankan lokal
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ke Streamlit Cloud
Push seluruh folder ke repo GitHub, lalu buat app baru dengan main file `app.py`.

## Cara pakai
1. Upload 18 file stok cabang (Excel/CSV) sekaligus di panel kiri.
2. Cek **pemetaan kolom** — kolom kategori, qty, dan harga beli dideteksi otomatis dari file pertama.
3. Cek **cabang per file** — cabang ditebak dari nama file; `TELUK JAMBE` otomatis dibaca `KARAWANG`.
4. Buka panel **pemetaan kategori** untuk memastikan semua kategori di file jatuh ke 4 kategori budget.
   Kategori yang tidak terpetakan akan diperingatkan beserta nilainya, jadi tidak ada nilai yang hilang diam-diam.
5. Baca ringkasan, tab Per Cabang / Per Kategori / Detail, lalu download hasil Excel multi-sheet.

## Aturan status
Selisih = Nilai Stok − Budget. Dengan toleransi *t* % (default 5):
- Selisih > +t% → **Over**
- Selisih < −t% → **Kurang**
- selebihnya → **Sesuai**

Cabang yang filenya tidak diupload tetap muncul dengan nilai stok 0 (status Kurang), supaya kekurangan data terlihat.

## Menambah/mengubah alias nama cabang
Edit `ALIAS_CABANG` di `logic.py`. Kunci ditulis huruf kecil tanpa spasi (mis. `"telukjambe": "KARAWANG"`).

## Catatan
Budget purchasing berbasis harga beli, jadi dasar perbandingan default adalah **Qty × Harga Beli**.
Bila file stok sudah menyediakan kolom nilai persediaan, pilih opsi *Kolom nilai stok langsung* di sidebar.
