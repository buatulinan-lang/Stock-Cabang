# Dashboard Cek Stok vs Budget Purchasing — MFlash

Membandingkan **nilai stok aktual** tiap cabang & kategori terhadap **master budget purchasing**
(18 cabang × 4 kategori, total Rp 6.919.262.000), lalu menandai **Kurang / Sesuai / Over**.

## Isi
- `app.py` — antarmuka Streamlit
- `logic.py` — logika inti (parsing file, deteksi cabang, pemetaan kategori, perbandingan)
- `budget_master.json` — master budget hasil ekstraksi dari *Master Budget Purchasing MFlash.xlsx*
- `data/` — **taruh file stok cabang di sini** lalu push ke GitHub; dashboard membacanya otomatis
- `test_logic.py`, `test_warbong.py` — uji otomatis logika inti
- `requirements.txt`

## Menjalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Alur pemakaian (data permanen di GitHub)
1. Salin file stok 18 cabang ke folder `data/`, commit & push.
2. Deploy repo ke Streamlit Cloud dengan main file `app.py`. Dashboard langsung membaca `data/`.
3. Ganti periode = ganti isi `data/` lalu push. Upload manual di sidebar tetap tersedia untuk
   cek cepat tanpa mengubah repo.

## Format file yang didukung
Export **Daftar Barang dan Jasa** dikenali otomatis:

| Kolom di file        | Dipakai sebagai            |
|----------------------|----------------------------|
| `Kategori Barang`    | kategori                   |
| `Kts (Semua Gdng)`   | qty                        |
| `Nilai Satuan`       | harga satuan (HPP)         |
| `Nilai Total`        | **nilai stok** (default)   |
| `Jenis Barang`       | filter `Inventory`         |

⚠️ **Penting — jangan gandakan nilai.** `Nilai Total` sudah = qty × harga satuan.
Bila kolom itu dikalikan qty lagi, nilai stok menggelembung (contoh WARBONG:
Rp 384.002.787 menjadi Rp 1.407.799.604). Karena itu mode default adalah
*Pakai kolom nilai total*, dan app menolak/memperingatkan bila kolom bernama "total"
dipilih sebagai harga satuan.

## Kategori
Empat kategori berbudget: Aksesoris, Handphone, Laptop, Sparepart.
Kategori sistem lain (ELEKTRONIK, PARFUM, CCTV, KARTU PERDANA, ASET, JASA, SEWA, dst.)
masuk kategori **Lainnya** — tetap dihitung di total nilai stok, tanpa budget pembanding.
Pemetaan bisa diubah manual di panel *Pemetaan kategori*.

## Filter Inventory
Baris `Service` dan `Non Inventory` bukan persediaan dan dikeluarkan dari nilai stok
(bisa dimatikan di sidebar).

## Aturan status
Selisih = Nilai Stok − Budget. Dengan toleransi *t* % (default 5):
Selisih > +t% → **Over**; < −t% → **Kurang**; selebihnya → **Sesuai**;
kategori tanpa budget → **Tanpa budget**.

## Kontrol audit
Panel **Validasi pembacaan file** menampilkan per file: jumlah baris, baris non-Inventory
yang dibuang, dan total nilai stok terbaca — cocokkan dengan total di file asli sebelum
memakai angkanya. Sheet `Validasi` juga ikut di hasil export Excel.

## File gabungan (satu file untuk semua cabang)
`gabung.py` menggabungkan 18 export cabang jadi satu CSV berkolom `Cabang` + `Kategori Budget`:

```bash
python gabung.py <folder_berisi_export> stok_gabungan.csv
```

App otomatis mengenali file yang punya kolom `Cabang` (termasuk `.csv.gz`) — tidak perlu
memilih cabang per file. Versi terkompresi `data/stok_gabungan.csv.gz` sudah disertakan
(±2 MB, dari 16 MB) supaya ringan di repo GitHub.

## Alias nama cabang
Edit `ALIAS_CABANG` di `logic.py` (huruf kecil tanpa spasi), mis. `"telukjambe": "KARAWANG"`.
