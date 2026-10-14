# ============================================================
#  PROGRAM KASIR TOKO ELEKTRONIK (versi Flask)
#  UTS Algoritma dan Pemrograman - Semester 1
# ============================================================
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "kasir-maju-jaya-7f3k9x2m-bebas-jaehyun-hiwom9027-790IOPGHj"   # dipakai Flask untuk menyimpan session

# ---------- DATA AWAL ----------
produk = [
    {"kode": "E001", "nama": "Smartphone Samsung A15", "harga": 3200000, "diskon": 10, "stok": 10},
    {"kode": "E002", "nama": "Laptop Asus Vivobook 14", "harga": 8500000, "diskon": 5, "stok": 5},
    {"kode": "E003", "nama": "Smart TV LED 32 Inch", "harga": 2800000, "diskon": 15, "stok": 7},
    {"kode": "E004", "nama": "Headphone Bluetooth", "harga": 450000, "diskon": 20, "stok": 20},
    {"kode": "E005", "nama": "Power Bank 10000mAh", "harga": 250000, "diskon": 0, "stok": 30},
    {"kode": "E006", "nama": "Smartwatch Xiaomi", "harga": 900000, "diskon": 12, "stok": 8},
]

promo = {
    "HEMAT10":   {"jenis": "persen",  "nilai": 10,    "min_belanja": 1000000, "maks": 500000},
    "ELEKTRO50": {"jenis": "nominal", "nilai": 50000, "min_belanja": 500000,  "maks": 50000},
    "MAHASISWA": {"jenis": "persen",  "nilai": 5,     "min_belanja": 0,       "maks": 300000},
}

cicilan_opsi = {3: 0, 6: 1, 12: 1.5}   # tenor (bulan) -> bunga per bulan (%)
MIN_CICILAN = 1000000


# ---------- FUNGSI BANTU ----------
def format_rp(angka):
    """Contoh: 3200000 -> Rp3.200.000"""
    return "Rp" + f"{angka:,.0f}".replace(",", ".")

app.jinja_env.filters["rp"] = format_rp   # supaya bisa dipakai di template: {{ x|rp }}


def cari_produk(kode):
    for p in produk:
        if p["kode"] == str(kode).upper():
            return p
    return None


def harga_setelah_diskon(p):
    return p["harga"] * (100 - p["diskon"]) / 100


def detail_keranjang():
    """Keranjang disimpan di session sebagai {kode: jumlah}. Fungsi ini mengubahnya jadi baris detail."""
    rows = []
    for kode, jumlah in session.get("keranjang", {}).items():
        p = cari_produk(kode)
        if p:
            satuan = harga_setelah_diskon(p)
            rows.append({"p": p, "jumlah": jumlah, "satuan": satuan, "jml": satuan * jumlah})
    return rows


def hitung_total(rows):
    """Mengembalikan (total_normal, total_diskon_produk, subtotal)."""
    normal = sum(r["p"]["harga"] * r["jumlah"] for r in rows)
    setelah = sum(r["jml"] for r in rows)
    return normal, normal - setelah, setelah


def hitung_potongan(kode, subtotal):
    """Potongan promo (0 jika tidak ada / tidak memenuhi syarat)."""
    info = promo.get(kode)
    if not info or subtotal < info["min_belanja"]:
        return 0
    if info["jenis"] == "persen":
        potongan = subtotal * info["nilai"] / 100
    else:
        potongan = info["nilai"]
    return min(potongan, info["maks"], subtotal)


def hitung_cicilan(total, tenor):
    bunga = cicilan_opsi[tenor]
    total_akhir = total + total * bunga / 100 * tenor
    return bunga, total_akhir, total_akhir / tenor


def gagal(pesan, tujuan="index"):
    flash(pesan, "err")
    return redirect(url_for(tujuan))


# ---------- HALAMAN UTAMA ----------
@app.route("/")
def index():
    rows = detail_keranjang()
    normal, diskon, subtotal = hitung_total(rows)
    kode_promo = session.get("promo")
    potongan = hitung_potongan(kode_promo, subtotal)
    if kode_promo and potongan == 0:      # belanja turun di bawah minimal -> promo dilepas
        session.pop("promo")
        kode_promo = None
    return render_template(
        "produk.html", produk=produk, rows=rows, normal=normal, diskon=diskon,
        subtotal=subtotal, kode_promo=kode_promo, potongan=potongan,
        total=subtotal - potongan, cicilan_opsi=cicilan_opsi, min_cicilan=MIN_CICILAN,
    )


# ---------- KERANJANG ----------
@app.post("/keranjang/tambah")
def tambah_ke_keranjang():
    p = cari_produk(request.form.get("kode", ""))
    if p is None:
        return gagal("Kode barang tidak ditemukan.")
    if p["stok"] == 0:
        return gagal("Stok barang habis.")
    try:
        jumlah = int(request.form.get("jumlah", ""))
    except ValueError:
        return gagal("Jumlah harus berupa angka.")
    if jumlah < 1:
        return gagal("Jumlah minimal 1.")

    keranjang = session.get("keranjang", {})
    sudah = keranjang.get(p["kode"], 0)
    if sudah + jumlah > p["stok"]:
        return gagal(f"Stok tidak cukup (tersedia {p['stok']}, di keranjang {sudah}).")

    keranjang[p["kode"]] = sudah + jumlah
    session["keranjang"] = keranjang
    flash(f"Berhasil: {jumlah} x {p['nama']} masuk keranjang.", "ok")
    return redirect(url_for("index"))


@app.post("/keranjang/hapus/<kode>")
def hapus_dari_keranjang(kode):
    keranjang = session.get("keranjang", {})
    keranjang.pop(kode, None)
    session["keranjang"] = keranjang
    return redirect(url_for("index"))


@app.post("/keranjang/kosongkan")
def kosongkan_keranjang():
    session.pop("keranjang", None)
    session.pop("promo", None)
    return redirect(url_for("index"))


# ---------- PROMO ----------
@app.post("/promo")
def pakai_promo():
    kode = request.form.get("kode", "").strip().upper()
    if kode == "":
        session.pop("promo", None)
        return redirect(url_for("index"))
    if kode not in promo:
        return gagal("Kode promo tidak valid.")
    subtotal = hitung_total(detail_keranjang())[2]
    if subtotal < promo[kode]["min_belanja"]:
        return gagal(f"Promo {kode} butuh minimal belanja {format_rp(promo[kode]['min_belanja'])}.")
    session["promo"] = kode
    flash(f"Promo {kode} dipakai, potongan {format_rp(hitung_potongan(kode, subtotal))}.", "ok")
    return redirect(url_for("index"))


# ---------- CHECKOUT & STRUK ----------
@app.post("/checkout")
def checkout():
    rows = detail_keranjang()
    if not rows:
        return gagal("Keranjang kosong, tambahkan barang dulu.")
    for r in rows:   # cek stok sekali lagi sebelum bayar
        if r["jumlah"] > r["p"]["stok"]:
            return gagal(f"Stok {r['p']['nama']} tidak cukup.")

    normal, diskon, subtotal = hitung_total(rows)
    kode_promo = session.get("promo")
    potongan = hitung_potongan(kode_promo, subtotal)
    total = subtotal - potongan

    metode_pilih = request.form.get("metode")
    total_akhir = total
    if metode_pilih == "tunai":
        try:
            bayar = int(request.form.get("uang", ""))
        except ValueError:
            return gagal("Uang diterima harus berupa angka.")
        if bayar < total:
            return gagal(f"Uang kurang {format_rp(total - bayar)}.")
        metode = "Tunai"
        ket = f"Dibayar {format_rp(bayar)}, kembalian {format_rp(bayar - total)}"
    elif metode_pilih == "transfer":
        metode, ket = "Transfer Bank", "Transfer ke rekening toko 1234-5678-90 (BCA)"
    elif metode_pilih == "ewallet":
        metode, ket = "E-Wallet", "Scan QR toko untuk membayar"
    elif metode_pilih == "cicilan":
        if total < MIN_CICILAN:
            return gagal(f"Cicilan hanya untuk belanja minimal {format_rp(MIN_CICILAN)}.")
        try:
            tenor = int(request.form.get("tenor", ""))
        except ValueError:
            tenor = 0
        if tenor not in cicilan_opsi:
            return gagal("Tenor tidak tersedia.")
        bunga, total_akhir, per_bulan = hitung_cicilan(total, tenor)
        metode = f"Cicilan {tenor} bulan"
        ket = f"Bunga {bunga}%/bulan, cicilan {format_rp(per_bulan)} x {tenor} bulan"
    else:
        return gagal("Pilih metode pembayaran.")

    # simpan data struk, kurangi stok, kosongkan keranjang
    session["struk"] = {
        "items": [{"nama": r["p"]["nama"], "jumlah": r["jumlah"], "satuan": r["satuan"], "jml": r["jml"]} for r in rows],
        "normal": normal, "diskon": diskon, "kode": kode_promo or "-", "potongan": potongan,
        "total": total, "metode": metode, "total_akhir": total_akhir, "ket": ket,
    }
    for r in rows:
        r["p"]["stok"] -= r["jumlah"]
    session.pop("keranjang", None)
    session.pop("promo", None)
    return redirect(url_for("struk"))


@app.route("/struk")
def struk():
    data = session.get("struk")
    if not data:
        return redirect(url_for("index"))
    return render_template("struk.html", s=data)


# ---------- ADMIN: TAMBAH PRODUK ----------
@app.post("/admin/tambah")
def tambah_produk_baru():
    kode = request.form.get("kode", "").strip().upper()
    nama = request.form.get("nama", "").strip()
    if kode == "" or cari_produk(kode) is not None:
        return gagal("Kode kosong atau sudah dipakai.")
    if nama == "":
        return gagal("Nama tidak boleh kosong.")
    try:
        harga = int(request.form.get("harga", ""))
        diskon = int(request.form.get("diskon", ""))
        stok = int(request.form.get("stok", ""))
    except ValueError:
        return gagal("Harga, diskon, dan stok harus berupa angka.")
    if harga < 1:
        return gagal("Harga minimal 1.")
    if not 0 <= diskon <= 100:
        return gagal("Diskon harus 0-100%.")
    if stok < 0:
        return gagal("Stok tidak boleh negatif.")
    produk.append({"kode": kode, "nama": nama, "harga": harga, "diskon": diskon, "stok": stok})
    flash(f"Produk '{nama}' berhasil ditambahkan.", "ok")
    return redirect(url_for("index"))


# ---------- PROGRAM DIMULAI ----------
if __name__ == "__main__":
    app.run(debug=True)
