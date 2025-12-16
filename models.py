from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin # <--- [BARU] Untuk fitur login
from datetime import datetime

# Inisialisasi object SQLAlchemy
db = SQLAlchemy()

# ==========================================
# MODEL 1: USER (Pengguna / Admin) [BARU]
# ==========================================
# UserMixin memberikan fitur standar user (is_authenticated, dll) otomatis
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    # Kita simpan password dalam bentuk HASH (acak), bukan teks asli
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Role: 'admin' atau 'member'. Nanti berguna untuk Otorisasi.
    role = db.Column(db.String(20), default='member')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# MODEL 2: BUKU
# ==========================================
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi ke Peminjaman (Satu buku bisa dipinjam berkali-kali dalam history)
    loans = db.relationship('Loan', backref='book', lazy=True)

# ==========================================
# MODEL 3: PEMINJAMAN
# ==========================================
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    borrower_name = db.Column(db.String(100), nullable=False)
    loan_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True) # Kosong = Belum kembali
    
    # Foreign Key ke tabel Book
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)