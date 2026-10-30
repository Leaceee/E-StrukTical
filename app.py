# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, request
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import os
from datetime import datetime
from flask import request, jsonify
from models import ocr_struk
from models import (
    get_user_by_email, create_user, verify_user,
    get_user_poin, list_struk_by_user, count_struk_by_user, list_redeem_by_user,
    list_hadiah, redeem_hadiah, get_hadiah_by_id, add_struk_upload, get_connection, tambah_poin_user,
    kurangi_poin, simpan_redeem, get_riwayat_redeem,
)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.secret_key = "estruktical-secret"  # ganti dengan secret yang aman di production


# Folder upload struk (pastikan ada)
UPLOAD_DIR = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('login'))


# -----------------------------
# LOGIN
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')

        user = verify_user(email, pw)
        if not user:
            flash("Email atau password salah", "danger")
            return redirect(url_for('login'))

        session['user_id'] = user['id']
        session['nama'] = user.get('nama') or user.get('name')
        session['email'] = user.get('email')
        # PENANDA LOGIN
        session['user_id'] = user['id']
        session['nama'] = user.get('nama')          # ← SIMPAN NAMA
        session['email'] = user.get('email')

        # Display name aman (tidak error)
        session['display_name'] = session.get('nama') or session.get('email')

        flash("Login berhasil", "success")
        return redirect(url_for('dashboard'))

    return render_template('login.html')


# -----------------------------
# REGISTER
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            nama = request.form['nama']
            email = request.form['email']
            password = request.form['password']
            alamat = request.form.get('alamat')
            nohp = request.form.get('no_hp')

            # Cek email sudah ada
            if get_user_by_email(email):
                flash("Email sudah terdaftar", "danger")
                return redirect(url_for('register'))

            create_user(
                nama,
                email,
                password,
                alamat,
                nohp
            )

            flash("Registrasi berhasil, silakan login", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print("REGISTER ERROR:", e)
            flash("Terjadi kesalahan saat membuat akun", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')



# -----------------------------
# DASHBOARD
# -----------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # 🔹 Ambil semua struk user
    cur.execute("""
        SELECT *
        FROM struk
        WHERE user_id = %s
        ORDER BY tanggal_upload DESC
    """, (user_id,))
    struk_list = cur.fetchall()

    # 🔹 HITUNG TOTAL POIN (INI YANG SEBELUMNYA KAMU TIDAK LAKUKAN)
    # AMBIL TOTAL POIN REAL (SATU SUMBER)
    cur.execute("""
    SELECT total_poin
    FROM poin
    WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    total_poin = row['total_poin'] if row else 0


    # 🔹 Hitung total struk
    total_struk = len(struk_list)

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        struk_list=struk_list,
        total_poin=total_poin,   # ← INI PENTING
        total_struk=total_struk,
        display_name=session.get('display_name'),
        redeem_list=[]
    )

# -----------------------------
# Profil (kartu identitas user)
# -----------------------------
@app.route('/profil')
def profil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']

    poin = get_user_poin(user_id)
    total_poin = poin['total_poin'] if isinstance(poin, dict) else (poin or 0)
    struk_count = count_struk_by_user(user_id)

    return render_template('profil.html',
                        total_poin=total_poin,
                        struk_count=struk_count,
                        nama=session.get('nama'),
                        email=session.get('email'))

# -----------------------------
# KARTU IDENTITAS USER
# -----------------------------
@app.route('/kartu-user')
def kartu_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # DATA USER
    cur.execute("SELECT nama, email, alamat FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    # TOTAL POIN (SAMA PERSIS DENGAN DASHBOARD)
    cur.execute("""
        SELECT COALESCE(SUM(poin_didapat), 0) AS total_poin
        FROM struk
        WHERE user_id=%s AND status_validasi='Valid'
    """, (user_id,))
    total_poin = cur.fetchone()['total_poin']

    # TOTAL STRUK
    cur.execute("""
        SELECT COUNT(*) AS total_struk
        FROM struk
        WHERE user_id=%s
    """, (user_id,))
    total_struk = cur.fetchone()['total_struk']

    cur.close()
    conn.close()

    return render_template(
        'kartu_user.html',
        user=user,
        total_poin=total_poin,
        total_struk=total_struk
    )

# -----------------------------
# Daftar hadiah
# -----------------------------
@app.route('/hadiah')
def hadiah_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    hadiahs = list_hadiah()
    poin = get_user_poin(session['user_id'])
    total = poin['total_poin'] if isinstance(poin, dict) else (poin or 0)

    return render_template("daftar_hadiah.html", hadiahs=hadiahs, total_poin=total)


# -----------------------------
# Redeem hadiah
# -----------------------------
@app.route('/redeem/<int:hid>', methods=['GET', 'POST'])
def redeem(hid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        res = redeem_hadiah(session['user_id'], hid)
        flash(res['msg'], 'success' if res['ok'] else 'danger')
        return redirect(url_for('hadiah_list'))

    hadiah = get_hadiah_by_id(hid)
    return render_template("redeem_hadiah.html", hadiah=hadiah)

# -------------------------------
# Halaman Penukaran Hadiah
# -------------------------------
@app.route('/penukaran-hadiah', methods=['GET', 'POST'])
def penukaran_hadiah():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        nama_hadiah = request.form['nama_hadiah']
        poin_hadiah = int(request.form['poin'])

        total_poin = get_user_poin(user_id)['total_poin']

        if total_poin < poin_hadiah:
            flash('Poin tidak mencukupi', 'danger')
            return redirect(url_for('penukaran_hadiah'))

        # POTONG POIN
        kurangi_poin(user_id, poin_hadiah)

        # SIMPAN RIWAYAT
        simpan_redeem(user_id, nama_hadiah, poin_hadiah)

        flash('Hadiah berhasil ditukarkan!', 'success')
        return redirect(url_for('penukaran_hadiah'))

    # ⬇️ WAJIB QUERY ULANG SETELAH TRANSAKSI
    total_poin = get_user_poin(user_id)['total_poin']

    riwayat = get_riwayat_redeem(user_id)

    return render_template(
    'penukaran_hadiah.html',
    total_poin=total_poin,
    riwayat=riwayat
)


# ==========================
# API Route
# ==========================
@app.route('/api/redeem', methods=['POST'])
def api_redeem():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.json
    poin_hadiah = int(data['poin'])
    nama_hadiah = data['nama_hadiah']
    user_id = session['user_id']

    poin = get_user_poin(user_id)
    total_poin = poin['total_poin']

    if total_poin < poin_hadiah:
        return jsonify({
            'success': False,
            'message': 'Poin tidak mencukupi'
        })

    # POTONG POIN
    kurangi_poin(user_id, poin_hadiah)

    # SIMPAN RIWAYAT
    simpan_redeem(user_id, nama_hadiah, poin_hadiah)

    # AMBIL POIN TERBARU
    poin_baru = get_user_poin(user_id)['total_poin']
    riwayat_terbaru = get_riwayat_redeem(user_id)
    
    riwayat_terbaru = {
    "nama_user": session.get("username", "User"),
    "hadiah": nama_hadiah,
    "tanggal": datetime.now().strftime("%d-%m-%Y")
}

    return jsonify({
    "success": True,
    "message": "Hadiah berhasil ditukarkan",
    "total_poin": poin_baru,
    "riwayat_terbaru": riwayat_terbaru
})




# ==========================
# UPLOAD STRUK (BELANJA / FOOD / TOPUP)
# ==========================
@app.route('/upload-struk/<jenis>', methods=['POST'])
def upload_struk(jenis):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    file = request.files.get('foto_struk')
    if not file:
        flash("File tidak ditemukan", "danger")
        return redirect(url_for('dashboard'))

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)

    # ===== OCR =====
    text = pytesseract.image_to_string(
    Image.open(path),
    config="--psm 6"
    ).lower()


    # ===== DETEKSI TRANSAKSI =====
    if 'lemon' in text:
        nama_transaksi = 'Lemontea'
    elif 'indomaret' in text:
        nama_transaksi = 'Belanja Indomaret'
    else:
        nama_transaksi = 'Struk Tidak Terdeteksi'

    poin_map = {
        'belanja': 10,
        'food': 15,
        'topup': 5
    }
    poin = poin_map.get(jenis, 5)

    add_struk_upload(
        user_id=session['user_id'],
        nama_user=session.get('nama') or session.get('email'),
        nama_transaksi=nama_transaksi,
        jenis_struk=jenis,
        foto_struk=filename,
        status_validasi='Pending'
    )

    flash("Struk berhasil diupload, menunggu validasi admin", "success")
    return redirect(url_for('dashboard'))



@app.route('/admin/struk')
def admin_struk():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT s.*, u.nama 
        FROM struk s
        JOIN users u ON s.user_id = u.id
        WHERE s.status_validasi = 'Pending'
        ORDER BY s.tanggal_upload DESC
    """)
    data = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('admin_struk.html', data=data)



@app.route('/admin/validasi/<int:id>/<status>')
def admin_validasi(id, status):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Ambil data struk
    cur.execute("SELECT user_id, jenis_struk FROM struk WHERE id=%s", (id,))
    struk = cur.fetchone()

    if not struk:
        flash("Struk tidak ditemukan", "danger")
        return redirect(url_for('admin_struk'))

    poin_map = {
        'belanja': 10,
        'food': 15,
        'topup': 5
    }
    poin = poin_map.get(struk['jenis_struk'], 5)

    if status == 'Valid':
        # Update status struk
        cur.execute("""
            UPDATE struk
            SET status_validasi='Valid', poin_didapat=%s
            WHERE id=%s
        """, (poin, id))

        # Tambah poin user
        cur.execute("""
            UPDATE poin
            SET total_poin = total_poin + %s
            WHERE user_id=%s
        """, (poin, struk['user_id']))

    else:
        cur.execute("""
            UPDATE struk
            SET status_validasi='Invalid'
            WHERE id=%s
        """, (id,))

    conn.commit()
    cur.close()
    conn.close()

    flash("Struk berhasil divalidasi", "success")
    return redirect(url_for('admin_struk'))



# Delete Struk
@app.route('/delete-struk/<int:id>')
def delete_struk(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    # pastikan hanya user pemilik struk yg bisa hapus
    cur.execute(
        "DELETE FROM struk WHERE id=%s AND user_id=%s",
        (id, session['user_id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    flash("Struk berhasil dihapus", "success")
    return redirect(url_for('dashboard'))

# -----------------------------
# Logout
# -----------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah logout.", "success")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
