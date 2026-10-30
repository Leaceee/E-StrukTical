
# ==========================================================
# APP.PY - E-STRUKTICAL
# Flask Application
# ==========================================================

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from werkzeug.utils import secure_filename

import pytesseract
from PIL import Image
import os
from datetime import datetime

from models import (
    get_user_by_email,
    create_user,
    verify_user,

    get_user_poin,
    list_struk_by_user,
    count_struk_by_user,
    list_redeem_by_user,

    list_hadiah,
    redeem_hadiah,
    get_hadiah_by_id,

    add_struk_upload,
    get_connection,
    tambah_poin_user,
    kurangi_poin,
    simpan_redeem,
    get_riwayat_redeem,

    ocr_struk,
    validasi_struk
)


# ==========================================================
# KONFIGURASI APLIKASI
# ==========================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "estruktical-secret"
)

UPLOAD_DIR = os.path.join(
    "static",
    "uploads"
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "pdf"
}


# ==========================================================
# VALIDASI FILE UPLOAD
# ==========================================================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ==========================================================
# HALAMAN UTAMA
# ==========================================================

@app.route("/")
def index():
    return redirect(url_for("login"))


# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = verify_user(email, password)

        if not user:
            flash("Email atau password salah", "danger")
            return redirect(url_for("login"))

        # Pastikan akun memiliki data poin
        get_user_poin(user["id"])

        session["user_id"] = user["id"]
        session["nama"] = user.get("nama") or user.get("name")
        session["email"] = user.get("email")

        session["display_name"] = (
            session.get("nama")
            or session.get("email")
        )

        flash("Login berhasil", "success")

        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ==========================================================
# REGISTER
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        try:
            nama = request.form["nama"]
            email = request.form["email"]
            password = request.form["password"]

            alamat = request.form.get("alamat")
            nohp = request.form.get("no_hp")

            # Periksa email
            if get_user_by_email(email):

                flash("Email sudah terdaftar", "danger")

                return redirect(url_for("register"))

            # Buat akun dan data poin awal
            create_user(
                nama,
                email,
                password,
                alamat,
                nohp
            )

            flash(
                "Registrasi berhasil, silakan login",
                "success"
            )

            return redirect(url_for("login"))

        except Exception as e:

            print("REGISTER ERROR:", e)

            flash(
                "Terjadi kesalahan saat membuat akun",
                "danger"
            )

            return redirect(url_for("register"))

    return render_template("register.html")


# ==========================================================
# DASHBOARD
# ==========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Pastikan data poin tersedia
    poin = get_user_poin(user_id)
    total_poin = poin["total_poin"]

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:

        # Ambil semua struk pengguna
        cur.execute("""
            SELECT *
            FROM struk
            WHERE user_id = %s
            ORDER BY tanggal_upload DESC
        """, (user_id,))

        struk_list = cur.fetchall()

        total_struk = len(struk_list)

    finally:
        cur.close()
        conn.close()

    return render_template(
        "dashboard.html",
        struk_list=struk_list,
        total_poin=total_poin,
        total_struk=total_struk,
        display_name=session.get("display_name"),
        redeem_list=[]
    )


# ==========================================================
# PROFIL PENGGUNA
# ==========================================================

@app.route("/profil")
def profil():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    poin = get_user_poin(user_id)
    total_poin = poin["total_poin"]

    struk_count = count_struk_by_user(user_id)

    return render_template(
        "profil.html",
        total_poin=total_poin,
        struk_count=struk_count,
        nama=session.get("nama"),
        email=session.get("email")
    )


# ==========================================================
# KARTU IDENTITAS USER
# ==========================================================

@app.route("/kartu-user")
def kartu_user():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Ambil data user
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:

        cur.execute("""
            SELECT nama, email, alamat
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cur.fetchone()

        # Hitung poin dari tabel poin
        # Bukan dari penjumlahan seluruh struk
        poin = get_user_poin(user_id)
        total_poin = poin["total_poin"]

        # Hitung jumlah struk
        cur.execute("""
            SELECT COUNT(*) AS total_struk
            FROM struk
            WHERE user_id = %s
        """, (user_id,))

        total_struk = cur.fetchone()["total_struk"]

    finally:
        cur.close()
        conn.close()

    return render_template(
        "kartu_user.html",
        user=user,
        total_poin=total_poin,
        total_struk=total_struk
    )


# ==========================================================
# DAFTAR HADIAH
# ==========================================================

@app.route("/hadiah")
def hadiah_list():

    if "user_id" not in session:
        return redirect(url_for("login"))

    hadiahs = list_hadiah()

    poin = get_user_poin(session["user_id"])
    total = poin["total_poin"]

    return render_template(
        "daftar_hadiah.html",
        hadiahs=hadiahs,
        total_poin=total
    )


# ==========================================================
# REDEEM HADIAH BERDASARKAN ID
# ==========================================================

@app.route("/redeem/<int:hid>", methods=["GET", "POST"])
def redeem(hid):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        res = redeem_hadiah(
            session["user_id"],
            hid
        )

        flash(
            res["msg"],
            "success" if res["ok"] else "danger"
        )

        return redirect(url_for("hadiah_list"))

    hadiah = get_hadiah_by_id(hid)

    if not hadiah:
        flash("Hadiah tidak ditemukan", "danger")
        return redirect(url_for("hadiah_list"))

    return render_template(
        "redeem_hadiah.html",
        hadiah=hadiah
    )


# ==========================================================
# HALAMAN PENUKARAN HADIAH
# ==========================================================

@app.route("/penukaran-hadiah", methods=["GET", "POST"])
def penukaran_hadiah():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":

        try:

            nama_hadiah = request.form["nama_hadiah"]
            poin_hadiah = int(request.form["poin"])

            if poin_hadiah <= 0:
                flash("Jumlah poin tidak valid", "danger")
                return redirect(url_for("penukaran_hadiah"))

            total_poin = get_user_poin(user_id)["total_poin"]

            if total_poin < poin_hadiah:

                flash(
                    "Poin tidak mencukupi",
                    "danger"
                )

                return redirect(url_for("penukaran_hadiah"))

            # Kurangi poin
            berhasil = kurangi_poin(
                user_id,
                poin_hadiah
            )

            if not berhasil:
                flash("Poin tidak mencukupi", "danger")
                return redirect(url_for("penukaran_hadiah"))

            # Simpan riwayat
            simpan_redeem(
                user_id,
                nama_hadiah,
                poin_hadiah
            )

            flash(
                "Hadiah berhasil ditukarkan!",
                "success"
            )

            return redirect(url_for("penukaran_hadiah"))

        except Exception as e:

            print("REDEEM ERROR:", e)

            flash(
                "Terjadi kesalahan saat menukarkan hadiah",
                "danger"
            )

            return redirect(url_for("penukaran_hadiah"))

    # Ambil data terbaru
    total_poin = get_user_poin(user_id)["total_poin"]

    riwayat = get_riwayat_redeem(user_id)

    return render_template(
        "penukaran_hadiah.html",
        total_poin=total_poin,
        riwayat=riwayat
    )


# ==========================================================
# API REDEEM HADIAH
# ==========================================================

@app.route("/api/redeem", methods=["POST"])
def api_redeem():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    try:

        data = request.get_json(silent=True) or {}

        nama_hadiah = data.get("nama_hadiah")
        poin_hadiah = int(data.get("poin", 0))

        user_id = session["user_id"]

        if not nama_hadiah or poin_hadiah <= 0:

            return jsonify({
                "success": False,
                "message": "Data hadiah tidak valid"
            }), 400

        total_poin = get_user_poin(user_id)["total_poin"]

        if total_poin < poin_hadiah:

            return jsonify({
                "success": False,
                "message": "Poin tidak mencukupi"
            })

        # Kurangi poin
        berhasil = kurangi_poin(
            user_id,
            poin_hadiah
        )

        if not berhasil:

            return jsonify({
                "success": False,
                "message": "Poin tidak mencukupi"
            })

        # Simpan riwayat redeem
        simpan_redeem(
            user_id,
            nama_hadiah,
            poin_hadiah
        )

        # Ambil jumlah poin terbaru
        poin_baru = get_user_poin(user_id)["total_poin"]

        riwayat_terbaru = {
            "nama_user": session.get("nama", "User"),
            "hadiah": nama_hadiah,
            "tanggal": datetime.now().strftime("%d-%m-%Y")
        }

        return jsonify({
            "success": True,
            "message": "Hadiah berhasil ditukarkan",
            "total_poin": poin_baru,
            "riwayat_terbaru": riwayat_terbaru
        })

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Jumlah poin tidak valid"
        }), 400

    except Exception as e:

        print("API REDEEM ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan pada server"
        }), 500


# ==========================================================
# UPLOAD STRUK
# ==========================================================

@app.route("/upload-struk/<jenis>", methods=["POST"])
def upload_struk(jenis):

    if "user_id" not in session:
        return redirect(url_for("login"))

    jenis = jenis.lower().strip()

    jenis_diizinkan = [
        "belanja",
        "food",
        "topup"
    ]

    if jenis not in jenis_diizinkan:

        flash(
            "Jenis struk tidak dikenal",
            "danger"
        )

        return redirect(url_for("dashboard"))

    file = request.files.get("foto_struk")

    if not file or file.filename == "":

        flash(
            "Silakan pilih file struk terlebih dahulu",
            "danger"
        )

        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):

        flash(
            "Format file tidak didukung",
            "danger"
        )

        return redirect(url_for("dashboard"))

    filename = secure_filename(file.filename)

    # Buat nama file unik agar tidak menimpa file sebelumnya
    nama_file, ekstensi = os.path.splitext(filename)

    filename = (
        f"{session['user_id']}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        f"{ekstensi.lower()}"
    )

    path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    try:

        file.save(path)

        # OCR hanya untuk gambar
        if ekstensi.lower() == ".pdf":

            hasil_ocr = ""

        else:

            with Image.open(path) as image:

                hasil_ocr = pytesseract.image_to_string(
                    image,
                    config="--psm 6"
                ).lower()

        # Deteksi nama transaksi
        if "lemon" in hasil_ocr:

            nama_transaksi = "Lemontea"

        elif "indomaret" in hasil_ocr:

            nama_transaksi = "Belanja Indomaret"

        elif "alfamart" in hasil_ocr:

            nama_transaksi = "Belanja Alfamart"

        elif jenis == "topup":

            nama_transaksi = "Top-Up E-Wallet"

        else:

            nama_transaksi = "Struk Tidak Terdeteksi"

        # Simpan struk dengan status Pending
        # Poin belum diberikan pada tahap upload
        add_struk_upload(
            user_id=session["user_id"],
            nama_user=(
                session.get("nama")
                or session.get("email")
            ),
            nama_transaksi=nama_transaksi,
            jenis_struk=jenis,
            foto_struk=filename,
            status_validasi="Pending",
            poin_didapat=0
        )

        flash(
            "Struk berhasil diupload, menunggu validasi admin",
            "success"
        )

    except Exception as e:

        print("UPLOAD STRUK ERROR:", e)

        # Hapus file jika penyimpanan database gagal
        if os.path.exists(path):
            os.remove(path)

        flash(
            "Terjadi kesalahan saat mengunggah struk",
            "danger"
        )

    return redirect(url_for("dashboard"))


# ==========================================================
# ADMIN - DAFTAR STRUK
# ==========================================================

@app.route("/admin/struk")
def admin_struk():

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Catatan:
    # Tambahkan pemeriksaan role admin sebelum publikasi.
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:

        cur.execute("""
            SELECT
                s.*,
                u.nama
            FROM struk s
            JOIN users u ON s.user_id = u.id
            WHERE s.status_validasi = 'Pending'
            ORDER BY s.tanggal_upload DESC
        """)

        data = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template(
        "admin_struk.html",
        data=data
    )


# ==========================================================
# ADMIN - VALIDASI STRUK
# ==========================================================

@app.route("/admin/validasi/<int:id>/<status>", methods=["GET", "POST"])
def admin_validasi(id, status):

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Catatan keamanan:
    # Route ini wajib diberi pemeriksaan role admin.
    # Jangan publikasikan aplikasi sebelum akses admin diamankan.

    if status not in ("Valid", "Invalid"):

        flash(
            "Status validasi tidak dikenal",
            "danger"
        )

        return redirect(url_for("admin_struk"))

    try:

        # Semua proses validasi dan pemberian poin
        # ditangani oleh satu fungsi di models.py.
        hasil = validasi_struk(id, status)

        flash(
            hasil["msg"],
            "success" if hasil["ok"] else "warning"
        )

    except Exception as e:

        print("VALIDASI STRUK ERROR:", e)

        flash(
            "Terjadi kesalahan saat memvalidasi struk",
            "danger"
        )

    return redirect(url_for("admin_struk"))


# ==========================================================
# DELETE STRUK
# ==========================================================

@app.route("/delete-struk/<int:id>", methods=["POST", "GET"])
def delete_struk(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur = conn.cursor()

    try:

        # Hanya pemilik struk yang dapat menghapus
        cur.execute("""
            DELETE FROM struk
            WHERE id = %s
              AND user_id = %s
        """, (
            id,
            session["user_id"]
        ))

        berhasil = cur.rowcount > 0

        conn.commit()

        if berhasil:

            flash(
                "Struk berhasil dihapus",
                "success"
            )

        else:

            flash(
                "Struk tidak ditemukan atau bukan milik Anda",
                "warning"
            )

    except Exception as e:

        conn.rollback()

        print("DELETE STRUK ERROR:", e)

        flash(
            "Gagal menghapus struk",
            "danger"
        )

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("dashboard"))


# ==========================================================
# LOGOUT
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Anda telah logout.",
        "success"
    )

    return redirect(url_for("login"))


# ==========================================================
# MENJALANKAN APLIKASI
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
