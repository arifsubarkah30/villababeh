import sqlite3
import datetime

DB_NAME = "villa.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calendar Table (date YYYY-MM-DD, status, price, note)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar (
            date TEXT PRIMARY KEY,
            status TEXT DEFAULT 'ready',
            price INTEGER DEFAULT 1500000,
            note TEXT DEFAULT ''
        )
    ''')

    # Facilities Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            category TEXT DEFAULT 'Umum',
            image_url TEXT DEFAULT ''
        )
    ''')

    try:
        cursor.execute("ALTER TABLE facilities ADD COLUMN image_url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # Gallery Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image_url TEXT NOT NULL,
            category TEXT DEFAULT 'Umum'
        )
    ''')

    # Bookings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT NOT NULL,
            guest_phone TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            total_price INTEGER NOT NULL,
            status TEXT DEFAULT 'confirmed',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Payments Table (Track DP, 2nd payment, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            payment_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        )
    ''')

    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Expenses Table (Track Villa Operational & Maintenance Expenses)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'Operasional',
            amount INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    default_settings = {
        "villa_name": "Villa Babeh",
        "tagline": "Mountain View Villa - Hunian Mewah & Asri untuk Liburan Keluarga Terbaik",
        "description": "Villa Babeh menawarkan pengalaman menginap istimewa dengan fasilitas lengkap, kolam renang pribadi, pemandangan gunung & alam indah, dan suasana yang tenang & sejuk.",
        "whatsapp": "6281234567890",
        "weekday_price": "1500000",
        "weekend_price": "2200000",
        "address": "Jl. Raya Puncak No. 88, Bogor, Jawa Barat",
        "admin_pin": "1234",
        "hero_image": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80",
        "villa_logo": "/static/images/logo.jpg"
    }

    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Update villa_logo if empty
    cursor.execute("SELECT value FROM settings WHERE key='villa_logo'")
    row = cursor.fetchone()
    if not row or not row[0]:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('villa_logo', '/static/images/logo.jpg')")

    # Seed default facilities if empty
    cursor.execute("SELECT COUNT(*) FROM facilities")
    if cursor.fetchone()[0] == 0:
        default_facilities = [
            ("Kolam Renang Pribadi", "Kolam renang bersih dengan kedalaman anak & dewasa + sunbed", "swimming-pool", "Utama", "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80"),
            ("4 Kamar Tidur AC", "Kamar tidur luas dengan bed berkualitas hotel bintang 4 & AC dingin", "bed", "Kamar", "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=800&q=80"),
            ("Dapur & Alat BBQ Lengkap", "Dilengkapi kulkas, kompor, alat masak, dispenser, dan pemanggang BBQ", "utensils", "Fasilitas", "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80"),
            ("Smart TV & Free WiFi", "Internet kecepatan tinggi, Netflix, YouTube, dan Sound System Karaoke", "tv", "Hiburan", "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80"),
            ("Halaman Luas & Gazebo", "Area rumput hijau asri cocok untuk gathering, outbound, & bersantai", "trees", "Outdoor", "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80"),
            ("Parkir Kategori 5 Mobil", "Area parkir aman dan luas di dalam benteng pagar villa", "car", "Keamanan", "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80")
        ]
        cursor.executemany("INSERT INTO facilities (name, description, icon, category, image_url) VALUES (?, ?, ?, ?, ?)", default_facilities)

    # Seed default gallery if empty
    cursor.execute("SELECT COUNT(*) FROM gallery")
    if cursor.fetchone()[0] == 0:
        default_gallery = [
            ("Tampak Depan & Halaman", "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80", "Outdoor"),
            ("Private Swimming Pool", "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80", "Kolam"),
            ("Ruang Keluarga & TV", "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80", "Interior"),
            ("Kamar Utama AC", "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=800&q=80", "Kamar"),
            ("Dapur & Area BBQ", "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80", "Dapur"),
            ("Taman & Gazebo", "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80", "Outdoor")
        ]
        cursor.executemany("INSERT INTO gallery (title, image_url, category) VALUES (?, ?, ?)", default_gallery)

    # Seed default expenses if empty
    cursor.execute("SELECT COUNT(*) FROM expenses")
    if cursor.fetchone()[0] == 0:
        default_expenses = [
            ("Listrik & Wifi Bulan September", "Operasional", 650000, "2026-09-05", "Tagihan bulanan PLN & Biznet"),
            ("Pembersihan Kolam & Obat Chlorine", "Kebersihan", 350000, "2026-09-10", "Beli kaporit & perawatan air kolam"),
            ("Gaji Staf Kebersihan & Jaga Villa", "Gaji Staff", 1500000, "2026-09-28", "Honor operasional bulanan")
        ]
        cursor.executemany("INSERT INTO expenses (title, category, amount, expense_date, notes) VALUES (?, ?, ?, ?, ?)", default_expenses)

    conn.commit()
    conn.close()

def get_settings():
    conn = get_db_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def update_settings(settings_dict):
    conn = get_db_connection()
    for k, v in settings_dict.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
    conn.commit()
    conn.close()

def get_month_calendar(year, month):
    conn = get_db_connection()
    settings = get_settings()
    default_weekday = int(settings.get("weekday_price", 1500000))
    default_weekend = int(settings.get("weekend_price", 2200000))

    prefix = f"{year:04d}-{month:02d}-%"
    rows = conn.execute("SELECT date, status, price, note FROM calendar WHERE date LIKE ?", (prefix,)).fetchall()
    conn.close()

    db_map = {row["date"]: dict(row) for row in rows}

    first_day = datetime.date(year, month, 1)
    if month == 12:
        last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    result = {}
    curr = first_day
    while curr <= last_day:
        date_str = curr.strftime("%Y-%m-%d")
        if date_str in db_map:
            result[date_str] = db_map[date_str]
        else:
            is_weekend = curr.weekday() in (4, 5, 6)
            default_price = default_weekend if is_weekend else default_weekday
            result[date_str] = {
                "date": date_str,
                "status": "ready",
                "price": default_price,
                "note": ""
            }
        curr += datetime.timedelta(days=1)

    return result

def batch_update_dates(start_date, end_date, status=None, price=None, note=None):
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    
    conn = get_db_connection()
    curr = start
    while curr <= end:
        date_str = curr.strftime("%Y-%m-%d")
        existing = conn.execute("SELECT status, price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()
        
        new_status = status if status else (existing["status"] if existing else "ready")
        new_price = price if price is not None else (existing["price"] if existing else (2200000 if curr.weekday() in (4,5,6) else 1500000))
        new_note = note if note is not None else (existing["note"] if existing else "")

        conn.execute('''
            INSERT OR REPLACE INTO calendar (date, status, price, note)
            VALUES (?, ?, ?, ?)
        ''', (date_str, new_status, new_price, new_note))
        curr += datetime.timedelta(days=1)
        
    conn.commit()
    conn.close()

# Indonesian National Holidays Data & Sync Helper
INDONESIA_HOLIDAYS = {
    # 2026
    "2026-01-01": "Tahun Baru Masehi",
    "2026-01-16": "Isra Mikraj Nabi Muhammad SAW",
    "2026-02-17": "Tahun Baru Imlek 2577 Kongzili",
    "2026-03-19": "Hari Suci Nyepi Saka 1948",
    "2026-03-20": "Hari Raya Idul Fitri 1447 H",
    "2026-03-21": "Hari Raya Idul Fitri 1447 H",
    "2026-04-03": "Wafat Yesus Kristus",
    "2026-04-05": "Hari Paskah",
    "2026-05-01": "Hari Buruh Internasional",
    "2026-05-14": "Kenaikan Yesus Kristus",
    "2026-05-27": "Hari Raya Idul Adha 1447 H",
    "2026-05-31": "Hari Raya Waisak 2570 BE",
    "2026-06-01": "Hari Lahir Pancasila",
    "2026-06-16": "Tahun Baru Islam 1448 H",
    "2026-08-17": "Hari Kemerdekaan RI",
    "2026-08-25": "Maulid Nabi Muhammad SAW",
    "2026-12-25": "Hari Raya Natal",
    # 2025
    "2025-01-01": "Tahun Baru Masehi",
    "2025-01-27": "Isra Mikraj Nabi Muhammad SAW",
    "2025-01-29": "Tahun Baru Imlek 2576 Kongzili",
    "2025-03-29": "Hari Suci Nyepi Saka 1947",
    "2025-03-31": "Hari Raya Idul Fitri 1446 H",
    "2025-04-01": "Hari Raya Idul Fitri 1446 H",
    "2025-04-18": "Wafat Yesus Kristus",
    "2025-05-01": "Hari Buruh Internasional",
    "2025-05-12": "Hari Raya Waisak 2569 BE",
    "2025-05-29": "Kenaikan Yesus Kristus",
    "2025-06-01": "Hari Lahir Pancasila",
    "2025-06-06": "Hari Raya Idul Adha 1446 H",
    "2025-06-27": "Tahun Baru Islam 1447 H",
    "2025-08-17": "Hari Kemerdekaan RI",
    "2025-09-05": "Maulid Nabi Muhammad SAW",
    "2025-12-25": "Hari Raya Natal"
}

def sync_national_holidays(year):
    conn = get_db_connection()
    settings = get_settings()
    weekend_price = int(settings.get("weekend_price", 2200000))

    count = 0
    for date_str, name in INDONESIA_HOLIDAYS.items():
        if date_str.startswith(str(year)):
            existing = conn.execute("SELECT status, price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()
            current_status = existing["status"] if existing else "ready"
            current_note = existing["note"] if existing else ""

            if "Libur" not in current_note and "Tanggal Merah" not in current_note:
                new_note = f"🔴 Libur: {name}" if not current_note else f"{current_note} (🔴 Libur: {name})"
            else:
                new_note = current_note

            # Set weekend rate for national holiday if price was default
            new_price = existing["price"] if (existing and existing["price"]) else weekend_price

            conn.execute('''
                INSERT OR REPLACE INTO calendar (date, status, price, note)
                VALUES (?, ?, ?, ?)
            ''', (date_str, current_status, new_price, new_note))
            count += 1

    conn.commit()
    conn.close()
    return count

def get_expenses(month=None):
    conn = get_db_connection()
    if month and month != 'all':
        prefix = f"{month}-%"
        rows = conn.execute("SELECT * FROM expenses WHERE expense_date LIKE ? ORDER BY expense_date DESC", (prefix,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_expense(title, category, amount, expense_date, notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (title, category, amount, expense_date, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, category, amount, expense_date, notes))
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id

def delete_expense(expense_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

