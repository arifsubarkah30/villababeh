import sqlite3
import datetime
import os
import shutil

class PgRowWrapper:
    def __init__(self, record):
        self._record = dict(record) if record else {}

    def __getitem__(self, item):
        return self._record.get(item)

    def get(self, key, default=None):
        return self._record.get(key, default)

    def keys(self):
        return self._record.keys()

class PgCursorWrapper:
    def __init__(self, pg_cursor):
        self._cursor = pg_cursor
        self.lastrowid = None

    def execute(self, sql, params=None):
        params = params or ()
        sql_conv = sql.replace("?", "%s")
        if "INSERT OR REPLACE INTO settings" in sql_conv:
            sql_conv = sql_conv.replace(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (%s, %s)",
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            )
        elif "INSERT OR REPLACE INTO calendar" in sql_conv:
            sql_conv = sql_conv.replace(
                "INSERT OR REPLACE INTO calendar (date, status, price, note) VALUES (%s, %s, %s, %s)",
                "INSERT INTO calendar (date, status, price, note) VALUES (%s, %s, %s, %s) ON CONFLICT (date) DO UPDATE SET status = EXCLUDED.status, price = EXCLUDED.price, note = EXCLUDED.note"
            )
        elif "INSERT OR IGNORE INTO pricing_rules" in sql_conv:
            sql_conv = sql_conv.replace(
                "INSERT OR IGNORE INTO pricing_rules (day_of_week, category, price) VALUES (%s, %s, %s)",
                "INSERT INTO pricing_rules (day_of_week, category, price) VALUES (%s, %s, %s) ON CONFLICT (day_of_week) DO NOTHING"
            )
        elif "INSERT OR IGNORE INTO settings" in sql_conv:
            sql_conv = sql_conv.replace(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (%s, %s)",
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING"
            )

        if any(tok in sql_conv for tok in ["INSERT INTO bookings", "INSERT INTO payments", "INSERT INTO expenses", "INSERT INTO facilities", "INSERT INTO gallery"]):
            if "RETURNING" not in sql_conv:
                sql_conv = sql_conv + " RETURNING id"
                self._cursor.execute(sql_conv, params)
                res = self._cursor.fetchone()
                if res:
                    self.lastrowid = res["id"] if isinstance(res, dict) else res[0]
                return self

        self._cursor.execute(sql_conv, params)
        return self

    def executemany(self, sql, params_list):
        for params in params_list:
            self.execute(sql, params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return PgRowWrapper(row) if row else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [PgRowWrapper(r) for r in rows]

class PgConnWrapper:
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self):
        import psycopg2.extras
        return PgCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_db = os.path.join(base_dir, "villa.db")
    
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        tmp_db = os.path.join("/tmp", "villa.db")
        if not os.path.exists(tmp_db):
            if os.path.exists(bundled_db):
                try:
                    shutil.copy2(bundled_db, tmp_db)
                except Exception:
                    pass
        return tmp_db
    return bundled_db

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        import psycopg2
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url)
        return PgConnWrapper(conn)
    else:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Pricing Rules Table (day_of_week PRIMARY KEY, category, price NUMERIC)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing_rules (
                day_of_week TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                price NUMERIC NOT NULL
            )
        ''')

        default_pricing_rules = [
            ("Sunday", "WEEKDAY", 1800000),
            ("Monday", "WEEKDAY", 1800000),
            ("Tuesday", "WEEKDAY", 1800000),
            ("Wednesday", "WEEKDAY", 1800000),
            ("Thursday", "WEEKDAY", 1800000),
            ("Friday", "MIDDLE", 2200000),
            ("Saturday", "WEEKEND", 3850000)
        ]
        for day, cat, pr in default_pricing_rules:
            cursor.execute("INSERT OR IGNORE INTO pricing_rules (day_of_week, category, price) VALUES (?, ?, ?)", (day, cat, pr))

        # Calendar Table (date YYYY-MM-DD, status, price, note)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar (
                date TEXT PRIMARY KEY,
                status TEXT DEFAULT 'ready',
                price INTEGER DEFAULT 1800000,
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
            "whatsapp": "6281295398434",
            "weekday_price": "1800000",
            "middle_price": "2200000",
            "weekend_price": "3850000",
            "address": "Jl. Raya Puncak No. 88, Bogor, Jawa Barat",
            "admin_pin": "1234",
            "hero_image": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80",
            "villa_logo": "/static/images/logo.jpg",
            "highlight_1_title": "4 Kamar",
            "highlight_1_sub": "AC + Bed Super King",
            "highlight_2_title": "Private Pool",
            "highlight_2_sub": "Kolam Renang Bersih",
            "highlight_3_title": "30 Orang",
            "highlight_3_sub": "Kapasitas Tamu",
            "highlight_4_title": "Smart TV",
            "highlight_4_sub": "Sound Karaoke & WiFi"
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
                ("Kolam Renang Pribadi", "Kolam renang bersih dengan kedalaman anak & dewasa + sunbed santai", "swimming-pool", "Utama", "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80"),
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

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"init_db warning/error: {e}")


def get_settings():
    conn = get_db_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def get_pricing_rules():
    conn = get_db_connection()
    rows = conn.execute("SELECT day_of_week, category, price FROM pricing_rules").fetchall()
    conn.close()
    rules = {}
    for r in rows:
        rules[r["day_of_week"]] = {
            "category": r["category"],
            "price": int(r["price"])
        }
    
    defaults = {
        "Sunday": {"category": "WEEKDAY", "price": 1800000},
        "Monday": {"category": "WEEKDAY", "price": 1800000},
        "Tuesday": {"category": "WEEKDAY", "price": 1800000},
        "Wednesday": {"category": "WEEKDAY", "price": 1800000},
        "Thursday": {"category": "WEEKDAY", "price": 1800000},
        "Friday": {"category": "MIDDLE", "price": 2200000},
        "Saturday": {"category": "WEEKEND", "price": 3850000},
    }
    for day, item in defaults.items():
        if day not in rules:
            rules[day] = item
    return rules

def update_pricing_rule_by_category(category, price):
    conn = get_db_connection()
    conn.execute("UPDATE pricing_rules SET price = ? WHERE category = ?", (price, category))
    conn.commit()
    conn.close()

def update_settings(settings_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in settings_dict.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
        
        # Sync pricing_rules table automatically
        if k == "weekday_price":
            try:
                cursor.execute("UPDATE pricing_rules SET price = ? WHERE category = 'WEEKDAY'", (int(v),))
            except Exception:
                pass
        elif k == "middle_price":
            try:
                cursor.execute("UPDATE pricing_rules SET price = ? WHERE category = 'MIDDLE'", (int(v),))
            except Exception:
                pass
        elif k == "weekend_price":
            try:
                cursor.execute("UPDATE pricing_rules SET price = ? WHERE category = 'WEEKEND'", (int(v),))
            except Exception:
                pass

    conn.commit()
    conn.close()

INDONESIAN_DAYS = {
    "Sunday": "Minggu",
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu"
}

def get_night_price(date_obj, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    date_str = date_obj.strftime("%Y-%m-%d")
    day_name_en = date_obj.strftime("%A")
    day_name_id = INDONESIAN_DAYS.get(day_name_en, day_name_en)

    # Priority 1: SPECIAL DATE PRICE (custom price explicitly set in calendar table for this exact date)
    row = conn.execute("SELECT price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()
    if row and row["price"] is not None and row["price"] > 0:
        price = int(row["price"])
        is_special = True
    else:
        # Priority 3: DAY-OF-WEEK PRICE from pricing_rules
        rule = conn.execute("SELECT price, category FROM pricing_rules WHERE day_of_week = ?", (day_name_en,)).fetchone()
        if rule and rule["price"] is not None:
            price = int(rule["price"])
        else:
            # Fallback
            if day_name_en == "Saturday":
                price = 3850000
            elif day_name_en == "Friday":
                price = 2200000
            else:
                price = 1800000
        is_special = False

    if close_conn:
        conn.close()

    return price, is_special, day_name_id, day_name_en

def calculate_booking_price(check_in_str, check_out_str):
    start = datetime.datetime.strptime(check_in_str, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(check_out_str, "%Y-%m-%d").date()

    conn = get_db_connection()
    breakdown = []
    total_price = 0
    curr = start

    while curr < end:
        date_str = curr.strftime("%Y-%m-%d")
        price, is_special, day_id, day_en = get_night_price(curr, conn)
        
        row = conn.execute("SELECT status FROM calendar WHERE date = ?", (date_str,)).fetchone()
        status = row["status"] if row else "ready"

        breakdown.append({
            "date": date_str,
            "day_name": day_id,
            "day_name_en": day_en,
            "price": price,
            "is_special": is_special,
            "status": status
        })
        total_price += price
        curr += datetime.timedelta(days=1)

    conn.close()
    return {
        "check_in": check_in_str,
        "check_out": check_out_str,
        "nights": len(breakdown),
        "breakdown": breakdown,
        "total_price": total_price
    }

def get_released_months():
    settings = get_settings()
    raw = settings.get("released_months", "")
    if not raw:
        today = datetime.date.today()
        default_months = [
            f"{today.year:04d}-{today.month:02d}",
            f"{today.year:04d}-{(today.month % 12) + 1:02d}",
            f"{today.year:04d}-{(today.month + 1) % 12 + 1:02d}"
        ]
        return set(default_months)
    return set([m.strip() for m in raw.split(",") if m.strip()])

def toggle_release_month(year, month, release=True):
    released = get_released_months()
    month_key = f"{year:04d}-{month:02d}"
    if release:
        released.add(month_key)
    else:
        released.discard(month_key)
    
    val = ",".join(sorted(list(released)))
    update_settings({"released_months": val})
    return release

def get_month_calendar(year, month, for_public=False):
    conn = get_db_connection()

    prefix = f"{year:04d}-{month:02d}-%"
    rows = conn.execute("SELECT date, status, price, note FROM calendar WHERE date LIKE ?", (prefix,)).fetchall()

    db_map = {row["date"]: dict(row) for row in rows}

    first_day = datetime.date(year, month, 1)
    if month == 12:
        last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    month_key = f"{year:04d}-{month:02d}"
    released_set = get_released_months()
    is_released = month_key in released_set

    result = {}
    curr = first_day
    while curr <= last_day:
        date_str = curr.strftime("%Y-%m-%d")
        if date_str in db_map:
            item = dict(db_map[date_str])
        else:
            default_price, is_special, _, _ = get_night_price(curr, conn)
            item = {
                "date": date_str,
                "status": "ready",
                "price": default_price,
                "note": ""
            }
        
        # If public view and month is NOT released: mark ready status as not_available
        if for_public and not is_released:
            if item["status"] == "ready":
                item["status"] = "not_available"
                item["note"] = "🔒 Belum Dirilis"
        
        result[date_str] = item
        curr += datetime.timedelta(days=1)

    conn.close()

    return {
        "dates": result,
        "is_released": is_released
    }

def batch_update_dates(start_date, end_date, status=None, price=None, note=None):
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    
    conn = get_db_connection()

    curr = start
    while curr <= end:
        date_str = curr.strftime("%Y-%m-%d")
        existing = conn.execute("SELECT status, price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()
        
        day_default_price, _, _, _ = get_night_price(curr, conn)

        new_status = status if status else (existing["status"] if existing else "ready")
        new_price = price if price is not None else (existing["price"] if existing else day_default_price)
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

