# models.py
from koneksi import get_connection
from datetime import datetime
import bcrypt
import pytesseract
from PIL import Image
# ==========================
# USER
# ==========================
def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data

def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user



def create_user(nama, email, password, alamat, nohp):
    conn = get_connection()
    cur = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cur.execute("""
        INSERT INTO users (nama, email, password, alamat, no_hp)
        VALUES (%s, %s, %s, %s, %s)
    """, (nama, email, hashed, alamat, nohp))

    user_id = cur.lastrowid

    # 🔥 AUTO BUAT ROW POIN (WAJIB)
    cur.execute(
        "INSERT INTO poin (user_id, total_poin) VALUES (%s, 0)",
        (user_id,)
    )

    conn.commit()
    cur.close()
    conn.close()



def verify_user(email, password):
    user = get_user_by_email(email)
    if not user:
        return None
    if bcrypt.checkpw(password.encode(), user['password'].encode()):
        return user
    return None


# ==========================
# POIN
# ==========================
def get_user_poin(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT total_poin FROM poin WHERE user_id=%s", (user_id,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    return {"total_poin": data["total_poin"] if data else 0}


def tambah_poin_user(user_id, poin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE poin SET total_poin = total_poin + %s
        WHERE user_id = %s
    """, (poin, user_id))
    conn.commit()
    cur.close()
    conn.close()
    
    
    

# ==========================
# STRUK
# ==========================
def add_struk_upload(
    user_id,
    nama_user,
    nama_transaksi,
    jenis_struk,
    foto_struk,
    status_validasi='Pending',
    poin_didapat=0
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO struk
        (user_id, nama_user, nama_transaksi, jenis_struk, foto_struk, status_validasi, poin_didapat)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        user_id,
        nama_user,
        nama_transaksi,
        jenis_struk,
        foto_struk,
        status_validasi,
        poin_didapat
    ))

    conn.commit()
    cur.close()
    conn.close()


def list_struk_by_user(user_id, limit=10):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            id,
            nama_user,
            jenis_struk,
            nama_transaksi,
            status_validasi,
            tanggal_upload
        FROM struk
        WHERE user_id=%s
        ORDER BY tanggal_upload DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_riwayat_struk(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            nama_user,
            nama_transaksi,
            jenis_struk,
            status_validasi,
            tanggal_upload
        FROM struk
        WHERE user_id=%s
        ORDER BY tanggal_upload DESC
    """, (user_id,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# 🔥 INI YANG BIKIN ERROR TADI — SEKARANG SUDAH ADA
def get_riwayat_struk(user_id):
    return list_struk_by_user(user_id, limit=20)


def count_struk_by_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM struk WHERE user_id=%s", (user_id,))
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total

# =========================
# OCR STRUK
# =========================
def ocr_struk(file_path):
    text = pytesseract.image_to_string(Image.open(file_path))
    return text
# =========================
# DETEKSI NAMA TRANSAKSI
# =========================
def deteksi_nama_transaksi(ocr_text, jenis):
    if jenis == "food":
        if "lemon" in ocr_text:
            return "1x Lemontea"
        elif "burger" in ocr_text:
            return "Burger"
        return "Struk Minuman"

    if jenis == "belanja":
        if "indomaret" in ocr_text:
            return "Belanja Indomaret"
        elif "alfamart" in ocr_text:
            return "Belanja Alfamart"
        return "Struk Belanja"

    if jenis == "topup":
        return "Top-Up E-Wallet"

    return "Struk"

# =========================
# SIMPAN STRUK (PENDING)
# =========================
def simpan_struk(user_id, nama_user, jenis, nama_transaksi, hasil_ocr, filename):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO struk
        (user_id, nama_user, jenis_struk, nama_transaksi, hasil_ocr,
        foto_struk, status_validasi, poin_didapat)
        VALUES (%s,%s,%s,%s,%s,%s,'Pending',0)
    """, (user_id, nama_user, jenis, nama_transaksi, hasil_ocr, filename))

    conn.commit()
    cur.close()
    conn.close()
    
# =========================
# ADMIN VALIDASI
# =========================
def validasi_struk(id, status):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # ambil data struk
    cur.execute("SELECT user_id, jenis_struk FROM struk WHERE id=%s", (id,))
    struk = cur.fetchone()

    poin_map = {
        'belanja': 10,
        'food': 15,
        'topup': 5
    }
    poin = poin_map.get(struk['jenis_struk'], 5)

    if status == 'Valid':
        # update struk
        cur.execute("""
            UPDATE struk
            SET status_validasi='Valid', poin_didapat=%s
            WHERE id=%s
        """, (poin, id))

        # 🔥 TAMBAHKAN KE TOTAL POIN USER
        cur.execute("""
            UPDATE poin
            SET total_poin = total_poin + %s
            WHERE user_id = %s
        """, (poin, struk['user_id']))

    else:
        cur.execute("""
            UPDATE struk
            SET status_validasi='Invalid', poin_didapat=0
            WHERE id=%s
        """, (id,))

    conn.commit()
    cur.close()
    conn.close()



def tambah_poin_user(user_id, poin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE poin SET total_poin = total_poin + %s WHERE user_id=%s", (poin, user_id))
    conn.commit()
    cur.close()
    conn.close()
    
# ===========================
# Delete Struk
# ===========================
def delete_struk(struk_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM struk WHERE id=%s", (struk_id,))

    conn.commit()
    cur.close()
    conn.close()



# ==========================
# REDEEM
# ==========================
def list_redeem_by_user(user_id, limit=5):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            r.tanggal_redeem,
            h.nama_hadiah,
            r.status
        FROM redeem r
        JOIN hadiah h ON r.hadiah_id = h.id
        WHERE r.user_id=%s
        ORDER BY r.tanggal_redeem DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def list_hadiah():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM hadiah ORDER BY poin_dibutuhkan")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_hadiah_by_id(hid):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM hadiah WHERE id=%s", (hid,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data


def redeem_hadiah(user_id, hadiah_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT poin_dibutuhkan FROM hadiah WHERE id=%s", (hadiah_id,))
    hadiah = cur.fetchone()

    cur.execute("SELECT total_poin FROM poin WHERE user_id=%s", (user_id,))
    poin = cur.fetchone()

    if poin['total_poin'] < hadiah['poin_dibutuhkan']:
        return {"ok": False, "msg": "Poin tidak cukup"}

    cur.execute("""
        INSERT INTO redeem 
        (user_id, hadiah_id, tanggal_redeem, poin_terpakai, status)
        VALUES (%s,%s,NOW(),%s,'Pending')
    """, (user_id, hadiah_id, hadiah['poin_dibutuhkan']))

    cur.execute(
        "UPDATE poin SET total_poin = total_poin - %s WHERE user_id=%s",
        (hadiah['poin_dibutuhkan'], user_id)
    )

    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True, "msg": "Redeem berhasil"}

def kurangi_poin(user_id, poin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE poin
        SET total_poin = total_poin - %s
        WHERE user_id = %s
    """, (poin, user_id))
    conn.commit()
    cur.close()
    conn.close()
    
def simpan_redeem(user_id, hadiah_nama, poin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO redeem (user_id, hadiah_nama, poin_terpakai, tanggal_redeem, status)
        VALUES (%s, %s, %s, NOW(), 'success')
    """, (user_id, hadiah_nama, poin))
    conn.commit()
    cur.close()
    conn.close()


def get_riwayat_redeem(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT hadiah_nama, poin_terpakai, tanggal_redeem
        FROM redeem
        WHERE user_id = %s
        ORDER BY tanggal_redeem DESC
    """, (user_id,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data




