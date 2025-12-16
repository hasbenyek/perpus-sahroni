import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import or_

# [BARU] Import Library Keamanan Password & Login Manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# Import database models
from models import db, Book, Loan, User  # <--- Pastikan User diimport

load_dotenv()

app = Flask(__name__)

# ==========================================
# KONFIGURASI
# ==========================================
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'kunci-rahasia-dev-default')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///perpustakaan.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==========================================
# INISIALISASI
# ==========================================
db.init_app(app)
migrate = Migrate(app, db)

# [BARU] Inisialisasi Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Kalau belum login, otomatis lempar ke halaman ini

# [BARU] Fungsi Loader (Flask perlu ini untuk memuat user dari ID)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# [BARU] ROUTE AUTHENTICATION (Login/Register)
# ==========================================

# 1. Register (Daftar Akun Baru)
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Kalau sudah login, jangan boleh daftar lagi, lempar ke home
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Cek apakah username sudah ada?
        if User.query.filter_by(username=username).first():
            flash('Username sudah dipakai, pilih yang lain!', 'danger')
            return redirect(url_for('register'))
        
        # Enkripsi Password sebelum simpan ke DB
        hashed_password = generate_password_hash(password)
        
        # Simpan User Baru
        new_user = User(username=username, password_hash=hashed_password, role='member')
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html') # Pastikan file ini ada di templates/auth/

# 2. Login (Masuk Sistem)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Cek apakah user ada DAN password cocok?
        if user and check_password_hash(user.password_hash, password):
            login_user(user) # Buat session login
            flash('Berhasil login!', 'success')
            
            # Cek apakah ada halaman tujuan sebelum login? (Next)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login gagal. Periksa username atau password.', 'danger')
            
    return render_template('auth/login.html')

# 3. Logout (Keluar)
@app.route('/logout')
@login_required # Hanya bisa diakses kalau sudah login
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))


# ==========================================
# ROUTING UTAMA (Protected)
# ==========================================

@app.route('/')
@login_required # [BARU] Harus login untuk lihat dashboard
def index():
    total_books = Book.query.count()
    active_loans = Loan.query.filter_by(return_date=None).count()
    return render_template('index.html', total_books=total_books, active_loans=active_loans)

@app.route('/books')
@login_required # [BARU] Harus login untuk lihat buku
def book_list():
    search_query = request.args.get('q')
    if search_query:
        search_pattern = f"%{search_query}%"
        all_books = Book.query.filter(
            or_(Book.title.ilike(search_pattern), Book.author.ilike(search_pattern))
        ).order_by(Book.created_at.desc()).all()
    else:
        all_books = Book.query.order_by(Book.created_at.desc()).all()

    return render_template('library/book_list.html', books=all_books, search_query=search_query)

@app.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        stock = request.form.get('stock')

        new_book = Book(title=title, author=author, stock=int(stock))
        db.session.add(new_book)
        db.session.commit()
        
        flash('Buku berhasil ditambahkan!', 'success')
        return redirect(url_for('book_list'))
    
    return render_template('library/book_form.html')

@app.route('/loans')
@login_required
def loan_list():
    loans = Loan.query.order_by(Loan.loan_date.desc()).all()
    return render_template('library/loan_list.html', loans=loans)

@app.route('/loan/add/<int:book_id>', methods=['GET', 'POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        borrower = request.form.get('borrower_name')
        if book.stock > 0:
            book.stock -= 1
            new_loan = Loan(borrower_name=borrower, book_id=book.id)
            db.session.add(new_loan)
            db.session.commit()
            flash(f'Buku "{book.title}" berhasil dipinjam oleh {borrower}!', 'success')
            return redirect(url_for('loan_list'))
        else:
            flash('Stok buku habis!', 'danger')
            return redirect(url_for('book_list'))

    return render_template('library/loan_form.html', book=book)

@app.route('/loan/return/<int:loan_id>')
@login_required
def return_book(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.return_date is None:
        loan.return_date = datetime.utcnow() 
        loan.book.stock += 1                 
        db.session.commit()
        flash('Buku berhasil dikembalikan!', 'success')
    return redirect(url_for('loan_list'))

if __name__ == '__main__':
    app.run(debug=True)