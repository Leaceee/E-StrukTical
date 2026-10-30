
# ==========================================================
# MODELS.PY - E-STRUKTICAL
# Database, User, Poin, Struk, OCR, Validasi, dan Redeem
# ==========================================================

from koneksi import get_connection
from datetime import datetime
import bcrypt
import pytesseract
from PIL import Image


# ==========================================================
# USER
# ==========================================================

def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
        return cur.fetchone()

    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        return cur.fetchone()

    finally:
        cur.close()
        conn.close()


def create_user(nama, email, password, alamat, nohp):
    conn = get_connection()
    cur = conn.cursor()

    try:
        hashed = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt()
        ).decode()

        cur.execute("""
            INSERT INTO users
            (nama, email, password, alamat, no_hp)
            VALUES (%s, %s, %s, %s, %s)
        """, (nama, email, hashed, alamat, nohp))

        user_id = cur.lastrowid

        # Otomatis membuat saldo poin awal
        cur.execute("""
            INSERT INTO poin (user_id, total_poin)
            VALUES (%s, 0)
        """, (user_id,))

        conn.commit()
        return user_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def verify_user(email, password):
    user = get_user_by_email(email)

    if not user:
        return None

    if bcrypt.checkpw(
        password.encode(),
        user['password'].encode()
    ):
        return user

    return None


# ==========================================================
# POIN
# ==========================================================

def ensure_user_poin(user_id):
    """
    Memastikan pengguna memiliki satu baris data poin.
    Tidak mereset saldo apabila data sudah tersedia.
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO poin (user_id, total_poin)
            VALUES (%s, 0)
            ON DUPLICATE KEY UPDATE user_id = user_id
        """, (user_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def get_user_poin(user_id):
    """
    Mengambil jumlah poin pengguna.
    Jika belum memiliki data poin, sistem membuatnya.
    """

    ensure_user_poin(user_id)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT total_poin
            FROM poin
            WHERE user_id = %s
        """, (user_id,))

        data = cur.fetchone()

        return {
            "total_poin": data["total_poin"] if data else 0
        }

    finally:
        cur.close()
        conn.close()


def tambah_poin_user(user_id, poin):
    """
    Menambahkan poin ke akun pengguna.
    """

    if poin <= 0:
        raise ValueError("Jumlah poin harus lebih dari 0")

    ensure_user_poin(user_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE poin
            SET total_poin = total_poin + %s
            WHERE user_id = %s
        """, (poin, user_id))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def kurangi_poin(user_id, poin):
    """
    Mengurangi poin hanya jika saldo mencukupi.
    """

    if poin <= 0:
        return False

    ensure_user_poin(user_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE poin
            SET total_poin = total_poin - %s
            WHERE user_id = %s
              AND total_poin >= %s
        """, (poin, user_id, poin))

        berhasil = cur.rowcount > 0
        conn.commit()

        return berhasil

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# ==========================================================
# STRUK
# ==========================================================

def add_struk_upload(
    user_id,
    nama_user,
    nama_transaksi,
    jenis_struk,
    foto_struk,
    status_validasi='Pending',
    poin_didapat=0
):
    # Pastikan data poin pengguna tersedia
    ensure_user_poin(user_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO struk
            (
                user_id,
                nama_user,
                nama_transaksi,
                jenis_struk,
                foto_struk,
                status_validasi,
                poin_didapat
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
        return cur.lastrowid

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def list_struk_by_user(user_id, limit=10):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT
                id,
                nama_user,
                jenis_struk,
                nama_transaksi,
                status_validasi,
                tanggal_upload
            FROM struk
            WHERE user_id = %s
            ORDER BY tanggal_upload DESC
            LIMIT %s
        """, (user_id, limit))

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


def get_riwayat_struk(user_id):
    return list_struk_by_user(user_id, limit=20)


def count_struk_by_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT COUNT(*) FROM struk WHERE user_id = %s",
            (user_id,)
        )

        return cur.fetchone()[0]

    finally:
        cur.close()
        conn.close()


# ==========================================================
# OCR STRUK
# ==========================================================

def ocr_struk(file_path):
    with Image.open(file_path) as image:
        text = pytesseract.image_to_string(image)

    return text


# ==========================================================
# DETEKSI NAMA TRANSAKSI
# ==========================================================

def deteksi_nama_transaksi(ocr_text, jenis):
    ocr_text = ocr_text.lower()
    jenis = jenis.lower().strip()

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


# ==========================================================
# SIMPAN STRUK (PENDING)
# ==========================================================

def simpan_struk(
    user_id,
    nama_user,
    jenis,
    nama_transaksi,
    hasil_ocr,
    filename
):
    ensure_user_poin(user_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO struk
            (
                user_id,
                nama_user,
                jenis_struk,
                nama_transaksi,
                hasil_ocr,
                foto_struk,
                status_validasi,
                poin_didapat
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending', 0)
        """, (
            user_id,
            nama_user,
            jenis,
            nama_transaksi,
            hasil_ocr,
            filename
        ))

        conn.commit()
        return cur.lastrowid

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# ==========================================================
# ADMIN VALIDASI STRUK
# ==========================================================

def validasi_struk(struk_id, status):

    if status not in ('Valid', 'Invalid'):
        return {
            "ok": False,
            "msg": "Status validasi tidak dikenal"
        }

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Memulai transaksi database
        conn.start_transaction()

        # Mengunci baris struk selama validasi
        cur.execute("""
            SELECT user_id, jenis_struk, status_validasi
            FROM struk
            WHERE id = %s
            FOR UPDATE
        """, (struk_id,))

        struk = cur.fetchone()

        if not struk:
            conn.rollback()

            return {
                "ok": False,
                "msg": "Struk tidak ditemukan"
            }

        # Mencegah validasi berulang
        if struk['status_validasi'] != 'Pending':
            conn.rollback()

            return {
                "ok": False,
                "msg": "Struk sudah pernah divalidasi"
            }

        if status == 'Valid':

            # Normalisasi jenis struk
            jenis = str(
                struk['jenis_struk']
            ).lower().strip()

            jenis = (
                jenis
                .replace(" ", "")
                .replace("/", "")
                .replace("-", "")
                .replace("_", "")
            )

            # Aturan pemberian poin
            poin_map = {
                'belanja': 10,
                'food': 15,
                'fooddrinks': 15,
                'topup': 5,
                'ewallet': 5
            }

            poin = poin_map.get(jenis)

            if poin is None:
                conn.rollback()

                return {
                    "ok": False,
                    "msg": "Jenis struk tidak dikenali"
                }

            # Pastikan data poin tersedia
            cur.execute("""
                INSERT INTO poin (user_id, total_poin)
                VALUES (%s, 0)
                ON DUPLICATE KEY UPDATE user_id = user_id
            """, (struk['user_id'],))

            # Update status dan poin pada struk
            cur.execute("""
                UPDATE struk
                SET status_validasi = 'Valid',
                    poin_didapat = %s
                WHERE id = %s
            """, (poin, struk_id))

            # Tambahkan poin ke akun pengguna
            cur.execute("""
                UPDATE poin
                SET total_poin = total_poin + %s
                WHERE user_id = %s
            """, (poin, struk['user_id']))

        else:

            # Struk ditolak tanpa pemberian poin
            cur.execute("""
                UPDATE struk
                SET status_validasi = 'Invalid',
                    poin_didapat = 0
                WHERE id = %s
            """, (struk_id,))

            poin = 0

        conn.commit()

        if status == 'Valid':
            pesan = (
                f"Struk berhasil divalidasi. "
                f"Poin bertambah {poin}."
            )
        else:
            pesan = "Struk berhasil ditolak."

        return {
            "ok": True,
            "msg": pesan
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# ==========================================================
# DELETE STRUK
# ==========================================================

def delete_struk(struk_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "DELETE FROM struk WHERE id = %s",
            (struk_id,)
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# ==========================================================
# REDEEM / PENUKARAN HADIAH
# ==========================================================

def list_redeem_by_user(user_id, limit=5):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT
                r.tanggal_redeem,
                h.nama_hadiah,
                r.status
            FROM redeem r
            JOIN hadiah h ON r.hadiah_id = h.id
            WHERE r.user_id = %s
            ORDER BY r.tanggal_redeem DESC
            LIMIT %s
        """, (user_id, limit))

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


def list_hadiah():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT *
            FROM hadiah
            ORDER BY poin_dibutuhkan
        """)

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


def get_hadiah_by_id(hid):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM hadiah WHERE id = %s",
            (hid,)
        )

        return cur.fetchone()

    finally:
        cur.close()
        conn.close()


def redeem_hadiah(user_id, hadiah_id):
    """
    Menukarkan poin dengan hadiah.
    Pengecekan saldo dan pengurangan poin dilakukan
    dalam satu transaksi.
    """

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        # Ambil data hadiah
        cur.execute("""
            SELECT id, nama_hadiah, poin_dibutuhkan
            FROM hadiah
            WHERE id = %s
            FOR UPDATE
        """, (hadiah_id,))

        hadiah = cur.fetchone()

        if not hadiah:
            conn.rollback()
            return {
                "ok": False,
                "msg": "Hadiah tidak ditemukan"
            }

        # Pastikan data poin tersedia
        cur.execute("""
            INSERT INTO poin (user_id, total_poin)
            VALUES (%s, 0)
            ON DUPLICATE KEY UPDATE user_id = user_id
        """, (user_id,))

        # Ambil dan kunci saldo poin
        cur.execute("""
            SELECT total_poin
            FROM poin
            WHERE user_id = %s
            FOR UPDATE
        """, (user_id,))

        data_poin = cur.fetchone()

        if not data_poin:
            conn.rollback()
            return {
                "ok": False,
                "msg": "Data poin pengguna tidak ditemukan"
            }

        total_poin = data_poin['total_poin']
        biaya = hadiah['poin_dibutuhkan']

        if total_poin < biaya:
            conn.rollback()
            return {
                "ok": False,
                "msg": "Poin tidak cukup"
            }

        # Simpan transaksi redeem
        cur.execute("""
            INSERT INTO redeem
            (
                user_id,
                hadiah_id,
                tanggal_redeem,
                poin_terpakai,
                status
            )
            VALUES (%s, %s, NOW(), %s, 'Pending')
        """, (user_id, hadiah_id, biaya))

        # Kurangi saldo poin
        cur.execute("""
            UPDATE poin
            SET total_poin = total_poin - %s
            WHERE user_id = %s
        """, (biaya, user_id))

        conn.commit()

        return {
            "ok": True,
            "msg": "Redeem berhasil",
            "total_poin": total_poin - biaya,
            "hadiah": hadiah['nama_hadiah']
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def simpan_redeem(user_id, hadiah_nama, poin):
    """
    Menyimpan riwayat redeem dengan nama hadiah.
    Fungsi ini dipertahankan untuk kompatibilitas
    dengan kode lama.
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO redeem
            (
                user_id,
                hadiah_nama,
                poin_terpakai,
                tanggal_redeem,
                status
            )
            VALUES (%s, %s, %s, NOW(), 'success')
        """, (user_id, hadiah_nama, poin))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def get_riwayat_redeem(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT
                hadiah_nama,
                poin_terpakai,
                tanggal_redeem
            FROM redeem
            WHERE user_id = %s
            ORDER BY tanggal_redeem DESC
        """, (user_id,))

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


# ==========================================================
# SELESAI - MODELS.PY
# ==========================================================
