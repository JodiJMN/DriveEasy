"""
DriveEasy — Flask Backend v2  (app.py)
======================================
Struktur Route:
  Public  : /, /cars, /cars/<slug>, /booking/<id>, /booking/success
             /feedback
  Admin   : /admin/login, /admin/logout
            /admin/dashboard
            /admin/cars  (list, add, edit, delete, toggle)
            /admin/categories
            /admin/discounts
            /admin/bookings
            /admin/availability/<car_id>
            /admin/reviews  (list, toggle approve, delete)
"""

import os, uuid, json
from datetime import datetime, date
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pyodbc

load_dotenv()
# ─────────────────────────────────────────────────────
# App & Config
# ─────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Folder paths
BASE_DIR      = app.root_path
UPLOAD_KTP    = os.path.join(BASE_DIR, 'static', 'uploads', 'ktp')
UPLOAD_CARS   = os.path.join(BASE_DIR, 'static', 'img', 'cars')
ALLOWED_IMG   = {'png', 'jpg', 'jpeg', 'webp', 'jfif'}
ALLOWED_DOCS  = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_UPLOAD_MB = 5

app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

for d in [UPLOAD_KTP, UPLOAD_CARS]:
    os.makedirs(d, exist_ok=True)

# ─────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────
DB = {
    'server':   os.environ.get('DB_SERVER'),
    'database': os.environ.get('DB_NAME'),
    'username': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'driver':   os.environ.get('DB_DRIVER'),
}

def get_db():
    conn_str = (
        f"DRIVER={DB['driver']};"
        f"SERVER={DB['server']};"
        f"DATABASE={DB['database']};"
        f"UID={DB['username']};"
        f"PWD={DB['password']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def qdb(sql, params=(), one=False):
    """SELECT helper — returns list[dict] or dict."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return rows[0] if (one and rows) else (None if one else rows)
    finally:
        conn.close()

def xdb(sql, params=()):
    """INSERT/UPDATE/DELETE helper — returns last inserted id."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        last_id = None
        try:
            cur.execute("SELECT SCOPE_IDENTITY()")
            r = cur.fetchone()
            if r and r[0]: last_id = int(r[0])
        except Exception:
            pass
        conn.commit()
        return last_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ─────────────────────────────────────────────────────
# Database Initializer — jalankan otomatis saat app start
# ─────────────────────────────────────────────────────
def init_db():
    """Buat tabel-tabel yang dibutuhkan jika belum ada."""
    ddl_reviews = """
        IF NOT EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'Reviews'
        )
        BEGIN
            CREATE TABLE Reviews (
                id          INT IDENTITY(1,1) PRIMARY KEY,
                name        NVARCHAR(100)  NOT NULL,
                email       NVARCHAR(150)  NULL,
                rating      TINYINT        NOT NULL CHECK (rating BETWEEN 1 AND 5),
                message     NVARCHAR(2000) NOT NULL,
                is_approved BIT            NOT NULL DEFAULT 1,
                created_at  DATETIME       NOT NULL DEFAULT GETDATE()
            );
        END
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(ddl_reviews)
        conn.commit()
        app.logger.info("init_db: tabel Reviews siap.")
    except Exception as e:
        app.logger.error(f"init_db error: {e}")
        conn.rollback()
    finally:
        conn.close()

# Panggil init_db saat aplikasi pertama kali start
with app.app_context():
    try:
        init_db()
    except Exception as _e:
        app.logger.warning(f"init_db skipped: {_e}")

# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def allowed_ext(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def save_upload(file, folder, allowed):
    """Save werkzeug FileStorage to folder. Returns new filename or None."""
    if not file or file.filename == '':
        return None
    if not allowed_ext(file.filename, allowed):
        return None
    ext  = file.filename.rsplit('.', 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(folder, name))
    return name

def fmt_currency(v):
    """Jinja2 filter: format angka ke Rp."""
    try:
        return "Rp {:,.0f}".format(float(v)).replace(",", ".")
    except Exception:
        return "Rp 0"

app.jinja_env.filters['currency'] = fmt_currency

def car_image_url(car):
    """Return accessible URL untuk foto mobil."""
    fn = car.get('image_filename') if isinstance(car, dict) else getattr(car, 'image_filename', None)
    if not fn:
        return "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=600"
    # Jika URL eksternal, langsung return
    if fn.startswith('http'):
        return fn
    local = os.path.join(UPLOAD_CARS, fn)
    if os.path.exists(local):
        return url_for('static', filename=f'img/cars/{fn}')
    # Fallback ke gambar Unsplash per brand
    fallbacks = {
        'toyota': 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=600',
        'honda':  'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=600',
        'mitsubishi': 'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=600',
        'daihatsu': 'https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=600',
        'suzuki': 'https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=600',
    }
    brand = (car.get('brand') or '').lower()
    return fallbacks.get(brand, "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=600")

app.jinja_env.globals['car_image_url'] = car_image_url

# ─────────────────────────────────────────────────────
# Context processor — data global semua template
# ─────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    try:
        cats = qdb("SELECT * FROM Categories WHERE is_active=1 ORDER BY sort_order, id")
    except Exception:
        cats = []
    try:
        approved_reviews = qdb("""
            SELECT TOP 6 id, name, rating, message, created_at
            FROM Reviews
            WHERE is_approved=1
            ORDER BY created_at DESC
        """)
    except Exception:
        approved_reviews = []
    return dict(
        categories=cats,
        current_year=datetime.now().year,
        is_admin=session.get('admin_id') is not None,
        admin_name=session.get('admin_name', ''),
        approved_reviews=approved_reviews,
    )

# ─────────────────────────────────────────────────────
# Admin Auth Guard
# ─────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Silakan login terlebih dahulu.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ═════════════════════════════════════════════════════
# PUBLIC ROUTES
# ═════════════════════════════════════════════════════

@app.route('/')
def index():
    try:
        featured = qdb("""
            SELECT TOP 6
                c.id, c.name, c.brand, c.price_per_day,
                c.transmission, c.capacity, c.image_filename,
                cat.name AS category_name, cat.slug AS category_slug
            FROM Cars c JOIN Categories cat ON c.category_id=cat.id
            WHERE c.is_available=1 AND cat.is_active=1
            ORDER BY c.price_per_day DESC
        """)
        stats = qdb("""
            SELECT
                (SELECT COUNT(*) FROM Cars WHERE is_available=1)    AS total_cars,
                (SELECT COUNT(*) FROM Bookings WHERE status='completed') AS total_bookings
        """, one=True)
        # Active discounts untuk banner
        promos = qdb("""
            SELECT TOP 3 * FROM Discounts
            WHERE is_active=1 AND valid_from<=CAST(GETDATE() AS DATE)
                  AND valid_until>=CAST(GETDATE() AS DATE)
            ORDER BY discount_value DESC
        """)
    except Exception as e:
        app.logger.error(f"index DB error: {e}")
        featured, stats, promos = [], {'total_cars':0,'total_bookings':0}, []
    return render_template('public/index.html',
                           featured_cars=featured, stats=stats, promos=promos)


@app.route('/cars')
@app.route('/cars/<slug>')
def cars(slug=None):
    category = None
    if slug:
        category = qdb("SELECT * FROM Categories WHERE slug=? AND is_active=1",
                        (slug,), one=True)
        if not category:
            abort(404)

    tx  = request.args.get('transmission', '')
    cap = request.args.get('capacity', '')

    sql = """
        SELECT c.id, c.name, c.brand, c.price_per_day,
               c.transmission, c.capacity, c.image_filename,
               c.description, c.year, c.is_available,
               cat.name AS category_name, cat.slug AS category_slug
        FROM Cars c JOIN Categories cat ON c.category_id=cat.id
        WHERE c.is_available=1 AND cat.is_active=1
    """
    params = []
    if category:
        sql += " AND cat.slug=?"; params.append(slug)
    if tx:
        sql += " AND c.transmission=?"; params.append(tx)
    if cap:
        try:
            sql += " AND c.capacity>=?"; params.append(int(cap))
        except (ValueError, TypeError):
            pass  # abaikan param capacity yang tidak valid
    sql += " ORDER BY c.sort_order, c.price_per_day ASC"

    try:
        car_list = qdb(sql, params)
    except Exception as e:
        app.logger.error(f"cars DB error: {e}")
        car_list = []

    return render_template('public/cars.html',
                           car_list=car_list, category=category,
                           active_slug=slug or 'all',
                           filter_tx=tx, filter_cap=cap)


@app.route('/booking/<int:car_id>', methods=['GET', 'POST'])
def booking(car_id):
    car = qdb("""
        SELECT c.*, cat.name AS category_name, cat.slug AS category_slug
        FROM Cars c JOIN Categories cat ON c.category_id=cat.id
        WHERE c.id=? AND c.is_available=1
    """, (car_id,), one=True)
    if not car:
        flash('Mobil tidak tersedia.', 'error')
        return redirect(url_for('index'))

    # Ambil tanggal yang sudah diblokir untuk kalender
    blocked = qdb("""
        SELECT block_start, block_end FROM CarAvailability
        WHERE car_id=? AND block_end >= CAST(GETDATE() AS DATE)
    """, (car_id,))
    blocked_ranges = [
        {"from": str(b['block_start']), "to": str(b['block_end'])}
        for b in blocked
    ]

    # Ambil diskon aktif
    today = date.today().isoformat()
    cat_slug = car.get('category_slug', '')
    discounts = qdb("""
        SELECT * FROM Discounts
        WHERE is_active=1 AND valid_from<=? AND valid_until>=?
          AND (apply_to='all' OR apply_to=?)
        ORDER BY discount_value DESC
    """, (today, today, cat_slug))

    if request.method == 'POST':
        name    = request.form.get('customer_name', '').strip()
        phone   = request.form.get('phone_number', '').strip()
        sd      = request.form.get('start_date', '')
        ed      = request.form.get('end_date', '')
        notes   = request.form.get('notes', '').strip()
        disc_id = request.form.get('discount_id') or None

        errors = []
        if not name:  errors.append('Nama lengkap wajib diisi.')
        if not phone: errors.append('Nomor WhatsApp wajib diisi.')
        if not sd or not ed: errors.append('Tanggal sewa wajib diisi.')

        ktp_file = request.files.get('ktp_file')
        if not ktp_file or ktp_file.filename == '':
            errors.append('File KTP/SIM wajib diunggah.')

        ktp_fn = None
        if ktp_file and ktp_file.filename:
            if not allowed_ext(ktp_file.filename, ALLOWED_DOCS):
                errors.append('Format KTP harus PNG, JPG, atau PDF.')
            else:
                ktp_fn = save_upload(ktp_file, UPLOAD_KTP, ALLOWED_DOCS)

        total_days = 0
        if sd and ed:
            try:
                sdo = datetime.strptime(sd, '%Y-%m-%d').date()
                edo = datetime.strptime(ed, '%Y-%m-%d').date()
                total_days = (edo - sdo).days
                if total_days <= 0:
                    errors.append('Tanggal selesai harus setelah tanggal mulai.')
                if sdo < date.today():
                    errors.append('Tanggal mulai tidak boleh di masa lalu.')
            except ValueError:
                errors.append('Format tanggal tidak valid.')

        if errors:
            for e in errors: flash(e, 'error')
            if ktp_fn:
                try: os.remove(os.path.join(UPLOAD_KTP, ktp_fn))
                except: pass
            return render_template('public/booking.html', car=car,
                                   blocked_ranges=blocked_ranges,
                                   discounts=discounts, form_data=request.form)

        # Hitung harga
        base_price = total_days * float(car['price_per_day'])
        disc_amount = 0.0
        disc_obj = None
        if disc_id:
            disc_obj = qdb("SELECT * FROM Discounts WHERE id=? AND is_active=1",
                           (disc_id,), one=True)
            if disc_obj:
                if disc_obj['discount_type'] == 'percent':
                    disc_amount = base_price * float(disc_obj['discount_value']) / 100
                else:
                    disc_amount = float(disc_obj['discount_value'])

        total_price = max(0, base_price - disc_amount)

        try:
            bid = xdb("""
                INSERT INTO Bookings
                    (car_id, discount_id, customer_name, phone_number,
                     start_date, end_date, base_price, discount_amount,
                     total_price, ktp_filename, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (car_id, disc_id or None, name, phone,
                  sd, ed, base_price, disc_amount,
                  total_price, ktp_fn, notes))

            # Blokir tanggal di CarAvailability
            xdb("""
                INSERT INTO CarAvailability (car_id, block_start, block_end, reason, booking_id)
                VALUES (?,?,?,'booked',?)
            """, (car_id, sd, ed, bid))

            # Increment diskon used_count
            if disc_id:
                xdb("UPDATE Discounts SET used_count=used_count+1 WHERE id=?", (disc_id,))

        except Exception as e:
            app.logger.error(f"booking insert error: {e}")
            flash('Terjadi kesalahan sistem. Silakan coba lagi.', 'error')
            return render_template('public/booking.html', car=car,
                                   blocked_ranges=blocked_ranges,
                                   discounts=discounts, form_data=request.form)

        return redirect(url_for('booking_success',
                                booking_id=bid,
                                car_name=car['name'],
                                customer_name=name,
                                phone_number=phone,
                                start_date=sd, end_date=ed,
                                total_days=total_days,
                                total_price=int(total_price),
                                disc_amount=int(disc_amount)))

    return render_template('public/booking.html', car=car,
                           blocked_ranges=blocked_ranges,
                           discounts=discounts, form_data={})


@app.route('/booking/success')
def booking_success():
    wa_number = os.environ.get('WA_ADMIN_NUMBER', '6281234567890')
    p = request.args
    return render_template('public/success.html',
                           wa_admin_number=wa_number,
                           booking_id=p.get('booking_id'),
                           car_name=p.get('car_name'),
                           customer_name=p.get('customer_name'),
                           phone_number=p.get('phone_number'),
                           start_date=p.get('start_date'),
                           end_date=p.get('end_date'),
                           total_days=p.get('total_days'),
                           total_price=p.get('total_price'),
                           disc_amount=p.get('disc_amount', 0))


# ═════════════════════════════════════════════════════
# ADMIN — Auth
# ═════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_id'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        uname = request.form.get('username', '').strip()
        pwd   = request.form.get('password', '')
        user  = qdb("SELECT * FROM AdminUsers WHERE username=? AND is_active=1",
                    (uname,), one=True)
        if user and check_password_hash(user['password_hash'], pwd):
            session['admin_id']   = user['id']
            session['admin_name'] = user['full_name'] or user['username']
            xdb("UPDATE AdminUsers SET last_login=GETDATE() WHERE id=?", (user['id'],))
            flash(f"Selamat datang, {session['admin_name']}!", 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Username atau password salah.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Berhasil logout.', 'success')
    return redirect(url_for('admin_login'))


# ═════════════════════════════════════════════════════
# ADMIN — Dashboard
# ═════════════════════════════════════════════════════

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats = qdb("""
        SELECT
          (SELECT COUNT(*) FROM Cars)                                  AS total_cars,
          (SELECT COUNT(*) FROM Cars WHERE is_available=1)            AS available_cars,
          (SELECT COUNT(*) FROM Bookings)                             AS total_bookings,
          (SELECT COUNT(*) FROM Bookings WHERE status='pending')      AS pending_bookings,
          (SELECT COUNT(*) FROM Bookings WHERE status='confirmed')    AS confirmed_bookings,
          (SELECT ISNULL(SUM(total_price),0) FROM Bookings
           WHERE status IN ('confirmed','completed')
             AND MONTH(created_at)=MONTH(GETDATE())
             AND YEAR(created_at)=YEAR(GETDATE()))                    AS revenue_this_month
    """, one=True)

    recent_bookings = qdb("""
        SELECT TOP 8
            b.id, b.customer_name, b.phone_number,
            b.start_date, b.end_date, b.total_price, b.status,
            b.created_at, c.name AS car_name, c.brand
        FROM Bookings b JOIN Cars c ON b.car_id=c.id
        ORDER BY b.created_at DESC
    """)

    # Statistik ulasan
    try:
        review_stats = qdb("""
            SELECT
              COUNT(*)                                    AS total_reviews,
              ISNULL(CAST(AVG(CAST(rating AS FLOAT)) AS DECIMAL(3,1)), 0) AS avg_rating,
              SUM(CASE WHEN is_approved=1 THEN 1 ELSE 0 END) AS approved_reviews
            FROM Reviews
        """, one=True)
    except Exception:
        review_stats = {'total_reviews': 0, 'avg_rating': 0, 'approved_reviews': 0}

    return render_template('admin/dashboard.html',
                           stats=stats, recent_bookings=recent_bookings,
                           review_stats=review_stats)


# ═════════════════════════════════════════════════════
# ADMIN — Cars CRUD
# ═════════════════════════════════════════════════════

@app.route('/admin/cars')
@admin_required
def admin_cars():
    cars_list = qdb("""
        SELECT c.*, cat.name AS category_name, cat.slug AS category_slug
        FROM Cars c JOIN Categories cat ON c.category_id=cat.id
        ORDER BY cat.sort_order, c.sort_order, c.id
    """)
    cats = qdb("SELECT * FROM Categories WHERE is_active=1 ORDER BY sort_order")
    return render_template('admin/cars.html', cars_list=cars_list, categories=cats)


@app.route('/admin/cars/add', methods=['GET', 'POST'])
@admin_required
def admin_car_add():
    cats = qdb("SELECT * FROM Categories WHERE is_active=1 ORDER BY sort_order")
    if request.method == 'POST':
        img_fn = None
        img_file = request.files.get('image_file')
        if img_file and img_file.filename:
            img_fn = save_upload(img_file, UPLOAD_CARS, ALLOWED_IMG)
            if not img_fn:
                flash('Format foto tidak valid (PNG/JPG/WEBP).', 'error')
                return render_template('admin/car_form.html', car=None, categories=cats)

        xdb("""
            INSERT INTO Cars (category_id, name, brand, price_per_day,
                              transmission, capacity, image_filename,
                              description, year, color, license_plate,
                              is_available, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            request.form['category_id'], request.form['name'],
            request.form['brand'],       float(request.form['price_per_day']),
            request.form['transmission'],int(request.form['capacity']),
            img_fn,                      request.form.get('description',''),
            request.form.get('year') or None,
            request.form.get('color',''),
            request.form.get('license_plate',''),
            1 if request.form.get('is_available') else 0,
            int(request.form.get('sort_order', 0))
        ))
        flash('Mobil berhasil ditambahkan!', 'success')
        return redirect(url_for('admin_cars'))

    return render_template('admin/car_form.html', car=None, categories=cats)


@app.route('/admin/cars/edit/<int:car_id>', methods=['GET', 'POST'])
@admin_required
def admin_car_edit(car_id):
    car  = qdb("SELECT * FROM Cars WHERE id=?", (car_id,), one=True)
    cats = qdb("SELECT * FROM Categories WHERE is_active=1 ORDER BY sort_order")
    if not car: abort(404)

    if request.method == 'POST':
        img_fn = car['image_filename']  # pertahankan foto lama by default
        img_file = request.files.get('image_file')
        if img_file and img_file.filename:
            new_fn = save_upload(img_file, UPLOAD_CARS, ALLOWED_IMG)
            if new_fn:
                # Hapus foto lama jika ada
                if img_fn and not img_fn.startswith('http'):
                    old_path = os.path.join(UPLOAD_CARS, img_fn)
                    try: os.remove(old_path)
                    except: pass
                img_fn = new_fn
            else:
                flash('Format foto tidak valid.', 'error')

        xdb("""
            UPDATE Cars SET
                category_id=?, name=?, brand=?, price_per_day=?,
                transmission=?, capacity=?, image_filename=?,
                description=?, year=?, color=?, license_plate=?,
                is_available=?, sort_order=?, updated_at=GETDATE()
            WHERE id=?
        """, (
            request.form['category_id'], request.form['name'],
            request.form['brand'],       float(request.form['price_per_day']),
            request.form['transmission'],int(request.form['capacity']),
            img_fn,                      request.form.get('description',''),
            request.form.get('year') or None,
            request.form.get('color',''),
            request.form.get('license_plate',''),
            1 if request.form.get('is_available') else 0,
            int(request.form.get('sort_order', 0)),
            car_id
        ))
        flash('Data mobil berhasil diperbarui!', 'success')
        return redirect(url_for('admin_cars'))

    return render_template('admin/car_form.html', car=car, categories=cats)


@app.route('/admin/cars/delete/<int:car_id>', methods=['POST'])
@admin_required
def admin_car_delete(car_id):
    car = qdb("SELECT * FROM Cars WHERE id=?", (car_id,), one=True)
    if car:
        # Hapus foto lokal
        if car['image_filename'] and not car['image_filename'].startswith('http'):
            try: os.remove(os.path.join(UPLOAD_CARS, car['image_filename']))
            except: pass
        xdb("DELETE FROM CarAvailability WHERE car_id=?", (car_id,))
        xdb("DELETE FROM Cars WHERE id=?", (car_id,))
        flash('Mobil berhasil dihapus.', 'success')
    return redirect(url_for('admin_cars'))


@app.route('/admin/cars/toggle/<int:car_id>', methods=['POST'])
@admin_required
def admin_car_toggle(car_id):
    """Toggle is_available AJAX endpoint."""
    car = qdb("SELECT is_available FROM Cars WHERE id=?", (car_id,), one=True)
    if not car:
        return jsonify({'ok': False}), 404
    new_val = 0 if car['is_available'] else 1
    xdb("UPDATE Cars SET is_available=?, updated_at=GETDATE() WHERE id=?", (new_val, car_id))
    return jsonify({'ok': True, 'is_available': new_val})


# ═════════════════════════════════════════════════════
# ADMIN — Availability
# ═════════════════════════════════════════════════════

@app.route('/admin/availability/<int:car_id>')
@admin_required
def admin_availability(car_id):
    car = qdb("SELECT * FROM Cars WHERE id=?", (car_id,), one=True)
    if not car: abort(404)
    blocks = qdb("""
        SELECT a.*, b.customer_name
        FROM CarAvailability a
        LEFT JOIN Bookings b ON a.booking_id=b.id
        WHERE a.car_id=? ORDER BY a.block_start
    """, (car_id,))
    return render_template('admin/availability.html', car=car, blocks=blocks)


@app.route('/admin/availability/<int:car_id>/add', methods=['POST'])
@admin_required
def admin_availability_add(car_id):
    bs = request.form.get('block_start')
    be = request.form.get('block_end')
    reason = request.form.get('reason', 'maintenance')
    if bs and be:
        xdb("""
            INSERT INTO CarAvailability (car_id, block_start, block_end, reason)
            VALUES (?,?,?,?)
        """, (car_id, bs, be, reason))
        flash('Blokir tanggal berhasil ditambahkan.', 'success')
    return redirect(url_for('admin_availability', car_id=car_id))


@app.route('/admin/availability/delete/<int:block_id>', methods=['POST'])
@admin_required
def admin_availability_delete(block_id):
    row = qdb("SELECT car_id FROM CarAvailability WHERE id=?", (block_id,), one=True)
    xdb("DELETE FROM CarAvailability WHERE id=?", (block_id,))
    flash('Blokir tanggal dihapus.', 'success')
    car_id = row['car_id'] if row else 0
    return redirect(url_for('admin_availability', car_id=car_id))


# ═════════════════════════════════════════════════════
# ADMIN — Discounts
# ═════════════════════════════════════════════════════

@app.route('/admin/discounts')
@admin_required
def admin_discounts():
    discs = qdb("SELECT * FROM Discounts ORDER BY created_at DESC")
    return render_template('admin/discounts.html', discounts=discs)


@app.route('/admin/discounts/add', methods=['POST'])
@admin_required
def admin_discount_add():
    try:
        xdb("""
            INSERT INTO Discounts
                (code, name, description, discount_type, discount_value,
                 min_days, max_uses, valid_from, valid_until, apply_to, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,1)
        """, (
            request.form.get('code') or None,
            request.form['name'],
            request.form.get('description', ''),
            request.form['discount_type'],
            float(request.form['discount_value']),
            int(request.form.get('min_days', 1)),
            int(request.form['max_uses']) if request.form.get('max_uses') else None,
            request.form['valid_from'],
            request.form['valid_until'],
            request.form.get('apply_to', 'all'),
        ))
        flash('Diskon berhasil ditambahkan!', 'success')
    except Exception as e:
        flash(f'Gagal menambahkan diskon: {e}', 'error')
    return redirect(url_for('admin_discounts'))


@app.route('/admin/discounts/edit/<int:disc_id>', methods=['POST'])
@admin_required
def admin_discount_edit(disc_id):
    xdb("""
        UPDATE Discounts SET
            code=?, name=?, description=?, discount_type=?,
            discount_value=?, min_days=?, max_uses=?,
            valid_from=?, valid_until=?, apply_to=?, is_active=?
        WHERE id=?
    """, (
        request.form.get('code') or None,
        request.form['name'],
        request.form.get('description', ''),
        request.form['discount_type'],
        float(request.form['discount_value']),
        int(request.form.get('min_days', 1)),
        int(request.form['max_uses']) if request.form.get('max_uses') else None,
        request.form['valid_from'],
        request.form['valid_until'],
        request.form.get('apply_to', 'all'),
        1 if request.form.get('is_active') else 0,
        disc_id
    ))
    flash('Diskon berhasil diperbarui!', 'success')
    return redirect(url_for('admin_discounts'))


@app.route('/admin/discounts/delete/<int:disc_id>', methods=['POST'])
@admin_required
def admin_discount_delete(disc_id):
    xdb("DELETE FROM Discounts WHERE id=?", (disc_id,))
    flash('Diskon berhasil dihapus.', 'success')
    return redirect(url_for('admin_discounts'))


# ═════════════════════════════════════════════════════
# ADMIN — Bookings
# ═════════════════════════════════════════════════════

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    status_filter = request.args.get('status', '')
    sql = """
        SELECT b.*, c.name AS car_name, c.brand,
               d.name AS discount_name
        FROM Bookings b
        JOIN Cars c ON b.car_id=c.id
        LEFT JOIN Discounts d ON b.discount_id=d.id
    """
    params = []
    if status_filter:
        sql += " WHERE b.status=?"; params.append(status_filter)
    sql += " ORDER BY b.created_at DESC"
    bookings = qdb(sql, params)
    return render_template('admin/bookings.html',
                           bookings=bookings, status_filter=status_filter)


@app.route('/admin/bookings/update-status/<int:bid>', methods=['POST'])
@admin_required
def admin_booking_status(bid):
    new_status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '')
    valid_statuses = ('pending', 'confirmed', 'completed', 'cancelled')
    if new_status in valid_statuses:
        xdb("""
            UPDATE Bookings SET status=?, admin_notes=?, updated_at=GETDATE()
            WHERE id=?
        """, (new_status, admin_notes, bid))

        # Jika dibatalkan, hapus blokir availability
        if new_status == 'cancelled':
            xdb("DELETE FROM CarAvailability WHERE booking_id=?", (bid,))

        flash('Status booking diperbarui.', 'success')
    else:
        flash(f'Status tidak valid: {new_status}.', 'error')
    return redirect(url_for('admin_bookings'))


# ═════════════════════════════════════════════════════
# PUBLIC — Feedback / Ulasan
# ═════════════════════════════════════════════════════

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Halaman form masukan publik (rating, kritik & saran)."""
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip() or None
        rating  = request.form.get('rating', '').strip()
        message = request.form.get('message', '').strip()

        errors = []
        if not name:
            errors.append('Nama wajib diisi.')
        if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
            errors.append('Rating wajib dipilih (1–5 bintang).')
        if not message or len(message) < 10:
            errors.append('Pesan minimal 10 karakter.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('public/feedback.html', form_data=request.form)

        try:
            xdb("""
                INSERT INTO Reviews (name, email, rating, message, is_approved)
                VALUES (?, ?, ?, ?, 1)
            """, (name, email, int(rating), message))
            flash('Terima kasih atas masukan Anda! Ulasan Anda telah berhasil dikirim. 🎉', 'success')
            return redirect(url_for('feedback'))
        except Exception as e:
            app.logger.error(f'feedback insert error: {e}')
            flash('Terjadi kesalahan sistem. Silakan coba lagi.', 'error')

    return render_template('public/feedback.html', form_data={})


# ═════════════════════════════════════════════════════
# ADMIN — Reviews
# ═════════════════════════════════════════════════════

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    """Daftar semua ulasan dari publik."""
    status_filter = request.args.get('status', '')
    if status_filter == 'approved':
        reviews = qdb("""
            SELECT * FROM Reviews WHERE is_approved=1 ORDER BY created_at DESC
        """)
    elif status_filter == 'pending':
        reviews = qdb("""
            SELECT * FROM Reviews WHERE is_approved=0 ORDER BY created_at DESC
        """)
    else:
        reviews = qdb("SELECT * FROM Reviews ORDER BY created_at DESC")

    try:
        rev_stats = qdb("""
            SELECT
              COUNT(*) AS total,
              ISNULL(CAST(AVG(CAST(rating AS FLOAT)) AS DECIMAL(3,1)), 0) AS avg_rating,
              SUM(CASE WHEN is_approved=1 THEN 1 ELSE 0 END) AS approved
            FROM Reviews
        """, one=True)
    except Exception:
        rev_stats = {'total': 0, 'avg_rating': 0, 'approved': 0}

    return render_template('admin/reviews.html',
                           reviews=reviews, rev_stats=rev_stats,
                           status_filter=status_filter)


@app.route('/admin/reviews/toggle/<int:rev_id>', methods=['POST'])
@admin_required
def admin_review_toggle(rev_id):
    """Toggle approve/hide ulasan."""
    row = qdb("SELECT is_approved FROM Reviews WHERE id=?", (rev_id,), one=True)
    if not row:
        return jsonify({'ok': False, 'msg': 'tidak ditemukan'}), 404
    new_val = 0 if row['is_approved'] else 1
    xdb("UPDATE Reviews SET is_approved=? WHERE id=?", (new_val, rev_id))
    return jsonify({'ok': True, 'is_approved': new_val})


@app.route('/admin/reviews/delete/<int:rev_id>', methods=['POST'])
@admin_required
def admin_review_delete(rev_id):
    """Hapus ulasan."""
    xdb("DELETE FROM Reviews WHERE id=?", (rev_id,))
    flash('Ulasan berhasil dihapus.', 'success')
    return redirect(url_for('admin_reviews'))


# ═════════════════════════════════════════════════════
# Error Handlers
# ═════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return render_template('public/404.html'), 404

@app.errorhandler(413)
def too_large(e):
    flash(f'File terlalu besar. Maksimum {MAX_UPLOAD_MB} MB.', 'error')
    return redirect(request.referrer or url_for('index'))

# ─────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)