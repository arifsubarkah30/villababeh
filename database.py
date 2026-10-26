import sqlite3
import datetime
import os
import shutil
import calendar as pycal
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------------------------
# POSTGRESQL & SQLITE COMPATIBILITY WRAPPERS
# -------------------------------------------------------------

class PgRowWrapper:
    def __init__(self, record):
        if not record:
            self._record = {}
        else:
            d = dict(record)
            for k, v in d.items():
                if isinstance(v, datetime.datetime):
                    d[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(v, datetime.date):
                    d[k] = v.strftime("%Y-%m-%d")
                elif str(type(v)).find('Decimal') != -1:
                    d[k] = int(v) if v % 1 == 0 else float(v)
            self._record = d

    def __getitem__(self, item):
        return self._record.get(item)

    def get(self, key, default=None):
        return self._record.get(key, default)

    def keys(self):
        return self._record.keys()

    def values(self):
        return self._record.values()

    def items(self):
        return self._record.items()

    def __contains__(self, key):
        return key in self._record

    def __iter__(self):
        return iter(self._record)


class PgCursorWrapper:
    def __init__(self, pg_cursor, pg_conn=None):
        self._cursor = pg_cursor
        self._conn = pg_conn
        self.lastrowid = None

    def execute(self, sql, params=None):
        params = params or ()
        sql_conv = sql.replace("?", "%s")
        sql_conv = sql_conv.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        
        # PostgreSQL syntax transformations
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
        elif "INSERT OR REPLACE INTO special_prices" in sql_conv:
            sql_conv = sql_conv.replace(
                "INSERT OR REPLACE INTO special_prices (date, price, note, is_active) VALUES (%s, %s, %s, %s)",
                "INSERT INTO special_prices (date, price, note, is_active) VALUES (%s, %s, %s, %s) ON CONFLICT (date) DO UPDATE SET price = EXCLUDED.price, note = EXCLUDED.note, is_active = EXCLUDED.is_active"
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
        elif "INSERT OR REPLACE INTO" in sql_conv:
            sql_conv = sql_conv.replace("INSERT OR REPLACE INTO", "INSERT INTO")
        elif "INSERT OR IGNORE INTO" in sql_conv:
            sql_conv = sql_conv.replace("INSERT OR IGNORE INTO", "INSERT INTO") + " ON CONFLICT DO NOTHING"

        if any(tok in sql_conv for tok in ["INSERT INTO bookings", "INSERT INTO payments", "INSERT INTO expenses", "INSERT INTO facilities", "INSERT INTO gallery", "INSERT INTO calendar_blocks", "INSERT INTO special_prices"]):
            if "RETURNING" not in sql_conv:
                sql_conv = sql_conv + " RETURNING id"
                try:
                    self._cursor.execute(sql_conv, params)
                    res = self._cursor.fetchone()
                    if res:
                        self.lastrowid = res.get("id") if isinstance(res, dict) else res[0]
                    return self
                except Exception as err:
                    if self._conn:
                        try:
                            self._conn.rollback()
                        except Exception:
                            pass
                    raise err

        try:
            self._cursor.execute(sql_conv, params)
        except Exception as err:
            if self._conn:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            raise err
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
        return PgCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), self._conn)

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


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
        url_to_use = db_url.replace("postgres://", "postgresql://", 1)
        if "sslmode" not in url_to_use:
            separator = "&" if "?" in url_to_use else "?"
            url_to_use += f"{separator}sslmode=require"
        try:
            conn = psycopg2.connect(url_to_use)
            conn.autocommit = True
            return PgConnWrapper(conn)
        except Exception as err:
            print(f"CRITICAL: Supabase PG connection failed: {err}")
            raise RuntimeError(f"Gagal terhubung ke Supabase Database: {err}")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables and seeds default values safely without resetting existing data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        is_pg = os.environ.get("DATABASE_URL") is not None
        id_pk = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"

        table_definitions = [
            # 1. Pricing Rules
            '''
            CREATE TABLE IF NOT EXISTS pricing_rules (
                day_of_week VARCHAR(15) PRIMARY KEY,
                category VARCHAR(20) NOT NULL,
                price NUMERIC NOT NULL
            )
            ''',
            # 2. Calendar per-date status and price
            '''
            CREATE TABLE IF NOT EXISTS calendar (
                date VARCHAR(10) PRIMARY KEY,
                status VARCHAR(20) DEFAULT 'ready',
                price NUMERIC DEFAULT 1800000,
                note TEXT DEFAULT ''
            )
            ''',
            # 3. Special Prices per-date override
            '''
            CREATE TABLE IF NOT EXISTS special_prices (
                date VARCHAR(10) PRIMARY KEY,
                price NUMERIC NOT NULL,
                note TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT true
            )
            ''',
            # 4. Calendar Blocks (Maintenance, Closure)
            f'''
            CREATE TABLE IF NOT EXISTS calendar_blocks (
                {id_pk},
                start_date VARCHAR(10) NOT NULL,
                end_date VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'MAINTENANCE',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            # 5. Facilities
            f'''
            CREATE TABLE IF NOT EXISTS facilities (
                {id_pk},
                name VARCHAR(100) NOT NULL,
                description TEXT,
                icon VARCHAR(50),
                category VARCHAR(50) DEFAULT 'Umum',
                image_url TEXT DEFAULT '',
                public_url TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
            ''',
            # 6. Gallery
            f'''
            CREATE TABLE IF NOT EXISTS gallery (
                {id_pk},
                title VARCHAR(100) NOT NULL,
                image_url TEXT NOT NULL,
                public_url TEXT DEFAULT '',
                category VARCHAR(50) DEFAULT 'Umum',
                sort_order INTEGER DEFAULT 0
            )
            ''',
            # 7. Bookings
            f'''
            CREATE TABLE IF NOT EXISTS bookings (
                {id_pk},
                booking_code VARCHAR(50) UNIQUE,
                guest_name VARCHAR(100) NOT NULL,
                guest_phone VARCHAR(50) NOT NULL,
                guest_ig VARCHAR(100) DEFAULT '-',
                total_guests VARCHAR(50) DEFAULT '25 Orang',
                check_in VARCHAR(10) NOT NULL,
                check_out VARCHAR(10) NOT NULL,
                total_price NUMERIC NOT NULL,
                status VARCHAR(30) DEFAULT 'PENDING',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            # 8. Payments
            f'''
            CREATE TABLE IF NOT EXISTS payments (
                {id_pk},
                booking_id INTEGER NOT NULL,
                payment_name VARCHAR(100) NOT NULL,
                amount NUMERIC NOT NULL,
                payment_date VARCHAR(30) DEFAULT CURRENT_TIMESTAMP,
                payment_method VARCHAR(50) DEFAULT 'Transfer Bank',
                notes TEXT
            )
            ''',
            # 9. Settings
            '''
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT
            )
            ''',
            # 10. Expenses
            f'''
            CREATE TABLE IF NOT EXISTS expenses (
                {id_pk},
                title VARCHAR(150) NOT NULL,
                category VARCHAR(50) DEFAULT 'Operasional',
                amount NUMERIC NOT NULL,
                expense_date VARCHAR(10) NOT NULL,
                payment_method VARCHAR(50) DEFAULT 'Transfer Bank',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            # 11. Booking Status History
            f'''
            CREATE TABLE IF NOT EXISTS booking_status_history (
                {id_pk},
                booking_id INTEGER NOT NULL,
                previous_status VARCHAR(30),
                new_status VARCHAR(30) NOT NULL,
                reason TEXT,
                changed_by VARCHAR(100) DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            # 12. Audit Logs
            f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                {id_pk},
                user_id VARCHAR(100),
                action VARCHAR(100) NOT NULL,
                entity VARCHAR(100) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        ]

        for stmt in table_definitions:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"Table init note: {e}")

        # Seed default pricing rules safely
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
            try:
                cursor.execute("INSERT OR IGNORE INTO pricing_rules (day_of_week, category, price) VALUES (?, ?, ?)", (day, cat, pr))
            except Exception:
                pass

        # Seed default settings safely
        initial_admin_hash = generate_password_hash("1234")
        default_settings = {
            "villa_name": "Villa Babeh",
            "tagline": "Mountain View Villa - Hunian Mewah & Asri untuk Liburan Keluarga Terbaik",
            "description": "Villa Babeh menawarkan pengalaman menginap istimewa dengan fasilitas lengkap, kolam renang pribadi, pemandangan gunung & alam indah, dan suasana yang tenang & sejuk.",
            "whatsapp": "6281295398434",
            "weekday_price": "1800000",
            "middle_price": "2200000",
            "weekend_price": "3850000",
            "dp_percentage": "50",
            "max_capacity": "25 Orang",
            "bedroom_count": "4 Kamar",
            "address": "Jl.Jogjogan Kec. Cisarua Kab. Bogor Jawa Barat",
            "admin_pin": "1234",
            "admin_username": "admin",
            "admin_email": "admin@villababeh.com",
            "admin_password_hash": initial_admin_hash,
            "hero_image": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80",
            "villa_logo": "/static/images/logo.jpg",
            "highlight_1_title": "4 Kamar",
            "highlight_1_sub": "Bersih dan Nyaman",
            "highlight_2_title": "Private Pool",
            "highlight_2_sub": "Kolam Renang Bersih",
            "highlight_3_title": "25 Orang",
            "highlight_3_sub": "Kapasitas Tamu",
            "highlight_4_title": "Smart TV",
            "highlight_4_sub": "Sound Karaoke & WiFi"
        }

        for k, v in default_settings.items():
            try:
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
            except Exception:
                pass

        conn.commit()
        conn.close()
        print("Database initialization check complete.")
    except Exception as e:
        print(f"init_db warning/error: {e}")


# -------------------------------------------------------------
# SETTINGS & PRICING RULES MANAGEMENT
# -------------------------------------------------------------

DEFAULT_SETTINGS = {
    "villa_name": "Villa Babeh",
    "tagline": "Mountain View Villa - Hunian Mewah & Asri untuk Liburan Keluarga Terbaik",
    "description": "Villa Babeh menawarkan pengalaman menginap istimewa dengan fasilitas lengkap, kolam renang pribadi, pemandangan gunung & alam indah, dan suasana yang tenang & sejuk.",
    "whatsapp": "6281295398434",
    "weekday_price": "1800000",
    "middle_price": "2200000",
    "weekend_price": "3850000",
    "dp_percentage": "50",
    "max_capacity": "25 Orang",
    "bedroom_count": "4 Kamar",
    "address": "Jl.Jogjogan Kec. Cisarua Kab. Bogor Jawa Barat",
    "admin_pin": "1234",
    "admin_username": "admin",
    "admin_email": "admin@villababeh.com",
    "hero_image": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80",
    "villa_logo": "/static/images/logo.jpg",
    "highlight_1_title": "4 Kamar",
    "highlight_1_sub": "Bersih dan Nyaman",
    "highlight_2_title": "Private Pool",
    "highlight_2_sub": "Kolam Renang Bersih",
    "highlight_3_title": "25 Orang",
    "highlight_3_sub": "Kapasitas Tamu",
    "highlight_4_title": "Smart TV",
    "highlight_4_sub": "Sound Karaoke & WiFi"
}

def get_settings():
    res = dict(DEFAULT_SETTINGS)
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        for row in rows:
            if row["key"] is not None and row["value"] is not None:
                res[row["key"]] = row["value"]
    except Exception as e:
        print(f"get_settings warning: {e}")
    return res

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

def get_pricing_rules():
    conn = get_db_connection()
    rules = {}
    try:
        rows = conn.execute("SELECT day_of_week, category, price FROM pricing_rules").fetchall()
        for r in rows:
            rules[r["day_of_week"]] = {
                "category": r["category"],
                "price": int(r["price"])
            }
    except Exception as e:
        print(f"get_pricing_rules note: {e}")
    finally:
        conn.close()

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


# -------------------------------------------------------------
# ADMIN AUTHENTICATION & PASSWORD MANAGEMENT
# -------------------------------------------------------------

def get_admin_credentials():
    s = get_settings()
    return {
        "password_hash": s.get("admin_password_hash"),
        "pin": s.get("admin_pin", "1234"),
        "username": s.get("admin_username", "admin"),
        "email": s.get("admin_email", "admin@villababeh.com")
    }

def verify_admin_login(identifier, password):
    creds = get_admin_credentials()
    ident = str(identifier or "").strip().lower()
    pwd = str(password or "").strip()

    # Check username / email match
    username_match = (
        not ident or 
        ident == creds["username"].lower() or 
        ident == creds["email"].lower() or 
        ident == "admin"
    )
    if not username_match:
        return {"success": False, "message": "Username atau email tidak terdaftar!"}

    # 1. Check secure password hash
    if creds["password_hash"]:
        try:
            if check_password_hash(creds["password_hash"], pwd):
                return {"success": True, "message": "Login berhasil!", "username": creds["username"], "email": creds["email"]}
        except Exception:
            pass

    # 2. Check legacy PIN fallback for backward compatibility
    if pwd == str(creds["pin"]).strip():
        # Automatically upgrade to strong hash
        try:
            new_hash = generate_password_hash(pwd)
            update_settings({"admin_password_hash": new_hash})
        except Exception:
            pass
        return {"success": True, "message": "Login berhasil!", "username": creds["username"], "email": creds["email"]}

    return {"success": False, "message": "Password salah. Silakan coba lagi."}

def change_admin_password(old_password, new_password, confirm_password):
    if not new_password or len(str(new_password).strip()) < 6:
        return {"success": False, "message": "Password baru minimal 6 karakter!"}

    if new_password != confirm_password:
        return {"success": False, "message": "Konfirmasi password baru tidak cocok!"}

    v = verify_admin_login("admin", old_password)
    if not v["success"]:
        return {"success": False, "message": "Password lama yang Anda masukkan salah!"}

    new_hash = generate_password_hash(str(new_password).strip())
    update_data = {"admin_password_hash": new_hash}
    if str(new_password).strip().isdigit() and len(str(new_password).strip()) <= 8:
        update_data["admin_pin"] = str(new_password).strip()

    update_settings(update_data)

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO audit_logs (user_id, action, entity, details)
            VALUES (?, 'CHANGE_PASSWORD', 'ADMIN', 'Admin changed password successfully')
        ''', ("admin",))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return {"success": True, "message": "Password admin berhasil diganti! Gunakan password baru untuk login berikutnya."}


# -------------------------------------------------------------
# CALENDAR, DATES & PRICING ENGINE
# -------------------------------------------------------------

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

    price = None
    is_special = False

    # Priority 1: SPECIAL DATE PRICE (special_prices table)
    try:
        sp_row = conn.execute("SELECT price, note FROM special_prices WHERE date = ? AND is_active = true", (date_str,)).fetchone()
        if sp_row and sp_row["price"] is not None and int(sp_row["price"]) > 0:
            price = int(sp_row["price"])
            is_special = True
    except Exception:
        pass

    # Priority 2: Per-date price in calendar table
    if price is None:
        try:
            cal_row = conn.execute("SELECT price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()
            if cal_row and cal_row["price"] is not None and int(cal_row["price"]) > 0:
                price = int(cal_row["price"])
                is_special = True
        except Exception:
            pass

    # Priority 3: Day-of-week rule from pricing_rules
    if price is None:
        try:
            rule = conn.execute("SELECT price, category FROM pricing_rules WHERE day_of_week = ?", (day_name_en,)).fetchone()
            if rule and rule["price"] is not None and int(rule["price"]) > 0:
                price = int(rule["price"])
        except Exception:
            pass

    # Priority 4: Default fallback
    if price is None:
        if day_name_en == "Saturday":
            price = 3850000
        elif day_name_en == "Friday":
            price = 2200000
        else:
            price = 1800000

    if close_conn:
        conn.close()

    return price, is_special, day_name_id, day_name_en


def calculate_booking_price(check_in_str, check_out_str):
    start = datetime.datetime.strptime(check_in_str, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(check_out_str, "%Y-%m-%d").date()

    if end <= start:
        raise ValueError("Tanggal Check-out harus setelah Check-in")

    conn = get_db_connection()
    breakdown = []
    total_price = 0
    curr = start

    while curr < end:
        date_str = curr.strftime("%Y-%m-%d")
        price, is_special, day_id, day_en = get_night_price(curr, conn)
        
        status = "ready"
        try:
            row = conn.execute("SELECT status FROM calendar WHERE date = ?", (date_str,)).fetchone()
            if row and row["status"]:
                status = row["status"]
        except Exception:
            pass

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
    
    settings = get_settings()
    dp_pct = int(settings.get("dp_percentage", 50))
    dp_amount = int(round(total_price * (dp_pct / 100.0)))
    remaining_balance = total_price - dp_amount

    return {
        "check_in": check_in_str,
        "check_out": check_out_str,
        "nights": len(breakdown),
        "breakdown": breakdown,
        "total_price": total_price,
        "dp_percentage": dp_pct,
        "dp_amount": dp_amount,
        "remaining_balance": remaining_balance
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

    _, num_days = pycal.monthrange(year, month)
    start_date_str = f"{year:04d}-{month:02d}-01"
    end_date_str = f"{year:04d}-{month:02d}-{num_days:02d}"

    # 1. Fetch calendar records
    cal_map = {}
    try:
        rows = conn.execute(
            "SELECT date, status, price, note FROM calendar WHERE CAST(date AS TEXT) >= ? AND CAST(date AS TEXT) <= ?",
            (start_date_str, end_date_str)
        ).fetchall()
        for r in rows:
            if r and r["date"]:
                cal_map[str(r["date"])] = dict(r)
    except Exception as e:
        print(f"Calendar query note: {e}")

    # 2. Fetch special_prices records
    sp_map = {}
    try:
        sp_rows = conn.execute(
            "SELECT date, price, note FROM special_prices WHERE CAST(date AS TEXT) >= ? AND CAST(date AS TEXT) <= ? AND is_active = true",
            (start_date_str, end_date_str)
        ).fetchall()
        for r in sp_rows:
            if r and r["date"]:
                sp_map[str(r["date"])] = dict(r)
    except Exception:
        pass

    # 3. Fetch confirmed bookings overlapping this month
    confirmed_dates = set()
    try:
        b_rows = conn.execute('''
            SELECT check_in, check_out, guest_name FROM bookings
            WHERE (status = 'CONFIRMED' OR status = 'confirmed')
              AND CAST(check_in AS TEXT) <= ? AND CAST(check_out AS TEXT) >= ?
        ''', (end_date_str, start_date_str)).fetchall()
        for b in b_rows:
            ci = datetime.datetime.strptime(str(b["check_in"])[:10], "%Y-%m-%d").date()
            co = datetime.datetime.strptime(str(b["check_out"])[:10], "%Y-%m-%d").date()
            cur = ci
            while cur < co:
                confirmed_dates.add(cur.strftime("%Y-%m-%d"))
                cur += datetime.timedelta(days=1)
    except Exception as e:
        print(f"Confirmed bookings check note: {e}")

    # 4. Fetch pending bookings overlapping this month
    pending_dates = set()
    try:
        p_rows = conn.execute('''
            SELECT check_in, check_out, guest_name FROM bookings
            WHERE (status = 'PENDING' OR status = 'pending')
              AND CAST(check_in AS TEXT) <= ? AND CAST(check_out AS TEXT) >= ?
        ''', (end_date_str, start_date_str)).fetchall()
        for b in p_rows:
            ci = datetime.datetime.strptime(str(b["check_in"])[:10], "%Y-%m-%d").date()
            co = datetime.datetime.strptime(str(b["check_out"])[:10], "%Y-%m-%d").date()
            cur = ci
            while cur < co:
                pending_dates.add(cur.strftime("%Y-%m-%d"))
                cur += datetime.timedelta(days=1)
    except Exception as e:
        print(f"Pending bookings check note: {e}")

    month_key = f"{year:04d}-{month:02d}"
    released_set = get_released_months()
    is_released = month_key in released_set

    result = {}
    curr = datetime.date(year, month, 1)
    last_date = datetime.date(year, month, num_days)

    while curr <= last_date:
        date_str = curr.strftime("%Y-%m-%d")
        default_price, is_special, _, _ = get_night_price(curr, conn)
        
        if date_str in cal_map:
            item = dict(cal_map[date_str])
            if date_str in sp_map:
                item["price"] = int(sp_map[date_str]["price"])
                item["is_special"] = True
            else:
                item["price"] = int(item.get("price") or default_price)
        elif date_str in sp_map:
            item = {
                "date": date_str,
                "status": "ready",
                "price": int(sp_map[date_str]["price"]),
                "note": sp_map[date_str].get("note") or "",
                "is_special": True
            }
        else:
            item = {
                "date": date_str,
                "status": "ready",
                "price": default_price,
                "note": "",
                "is_special": is_special
            }

        # Apply confirmed booking status overlay
        if date_str in confirmed_dates:
            item["status"] = "booked"
            item["note"] = "🔒 Terisi / Dikonfirmasi"
        # Apply pending booking status overlay
        elif date_str in pending_dates:
            item["status"] = "pending"
            item["note"] = "⏳ Menunggu Konfirmasi"

        # Apply public release gating
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

        # 1. Update special_prices if price explicitly given
        if price is not None and int(price) > 0:
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO special_prices (date, price, note, is_active)
                    VALUES (?, ?, ?, true)
                ''', (date_str, int(price), note or ''))
            except Exception as e:
                print(f"Update special_prices note: {e}")

        # 2. Update calendar table
        day_default_price, _, _, _ = get_night_price(curr, conn)
        existing = None
        try:
            existing = conn.execute("SELECT status, price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()
        except Exception:
            pass

        new_status = status if status else (existing["status"] if existing else "ready")
        new_price = int(price) if price is not None else (int(existing["price"]) if existing and existing["price"] else day_default_price)
        new_note = note if note is not None else (existing["note"] if existing else "")

        conn.execute('''
            INSERT OR REPLACE INTO calendar (date, status, price, note)
            VALUES (?, ?, ?, ?)
        ''', (date_str, new_status, new_price, new_note))
        
        curr += datetime.timedelta(days=1)

    conn.commit()
    conn.close()


# -------------------------------------------------------------
# BOOKING MANAGEMENT & WORKFLOW ENGINE
# -------------------------------------------------------------

def create_booking_request(guest_name, guest_phone, check_in, check_out, guest_ig="-", total_guests="25 Orang", notes=""):
    import random
    start = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(check_out, "%Y-%m-%d").date()
    
    if end <= start:
        return {"status": "error", "message": "Tanggal Check-out harus setelah Check-in"}

    calc_res = calculate_booking_price(check_in, check_out)
    
    conn = get_db_connection()
    
    # 1. Check overlap with CONFIRMED bookings
    overlap = conn.execute('''
        SELECT booking_code, guest_name FROM bookings
        WHERE (status = 'CONFIRMED' OR status = 'confirmed')
          AND CAST(check_in AS TEXT) < ? AND CAST(check_out AS TEXT) > ?
    ''', (check_out, check_in)).fetchone()

    if overlap:
        conn.close()
        return {"status": "error", "message": f"Maaf, tanggal {check_in} s/d {check_out} sudah terkonfirmasi oleh pemesan lain ({overlap['guest_name']})!"}

    # 2. Check overlap with calendar_blocks
    overlap_block = conn.execute('''
        SELECT status, note FROM calendar_blocks
        WHERE CAST(start_date AS TEXT) < ? AND CAST(end_date AS TEXT) > ?
    ''', (check_out, check_in)).fetchone()

    if overlap_block:
        conn.close()
        return {"status": "error", "message": f"Maaf, tanggal tersebut dalam masa pemeliharaan ({overlap_block['note'] or 'Maintenance'})!"}

    code_suffix = str(random.randint(1000, 9999))
    booking_code = f"VB-{check_in.replace('-', '')}-{code_suffix}"
    total_price = calc_res['total_price']
    combined_notes = f"Tamu: {total_guests} | IG: {guest_ig}" if not notes else f"{notes} | Tamu: {total_guests} | IG: {guest_ig}"

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (booking_code, guest_name, guest_phone, guest_ig, total_guests, check_in, check_out, total_price, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
    ''', (booking_code, guest_name, guest_phone, guest_ig, total_guests, check_in, check_out, total_price, combined_notes))
    
    booking_id = cursor.lastrowid
    
    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason, changed_by)
            VALUES (?, NULL, 'PENDING', 'Permohonan booking baru dari website', 'tamu')
        ''', (booking_id,))
    except Exception:
        pass

    try:
        conn.execute('''
            INSERT INTO audit_logs (user_id, action, entity, details)
            VALUES ('guest', 'CREATE_BOOKING', 'BOOKING', ?)
        ''', (f"Booking {booking_code} created by {guest_name} for {check_in} to {check_out}",))
    except Exception:
        pass

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "booking_id": booking_id,
        "booking_code": booking_code,
        "total_price": total_price,
        "dp_amount": calc_res['dp_amount'],
        "remaining_balance": calc_res['remaining_balance'],
        "breakdown": calc_res['breakdown'],
        "message": "Permintaan booking berhasil dikirim! Status saat ini: Menunggu Konfirmasi Admin."
    }


def confirm_booking(booking_id, admin_user="admin"):
    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    check_in = str(booking["check_in"])[:10]
    check_out = str(booking["check_out"])[:10]
    guest_name = booking["guest_name"]

    # Verify no date conflict with other confirmed bookings
    overlap = conn.execute('''
        SELECT booking_code, guest_name FROM bookings
        WHERE (status = 'CONFIRMED' OR status = 'confirmed') AND id != ?
          AND CAST(check_in AS TEXT) < ? AND CAST(check_out AS TEXT) > ?
    ''', (booking_id, check_out, check_in)).fetchone()

    if overlap:
        conn.close()
        return {
            "status": "error",
            "message": f"Konflik tanggal! Jadwal tersebut sudah terisi oleh {overlap['guest_name']} ({overlap['booking_code']})."
        }

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = ?", (booking_id,))

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason, changed_by)
            VALUES (?, ?, 'CONFIRMED', 'Disetujui oleh admin', ?)
        ''', (booking_id, prev_status, admin_user))
    except Exception:
        pass

    try:
        conn.execute('''
            INSERT INTO audit_logs (user_id, action, entity, details)
            VALUES (?, 'CONFIRM_BOOKING', 'BOOKING', ?)
        ''', (admin_user, f"Booking ID {booking_id} confirmed for {guest_name}"))
    except Exception:
        pass

    conn.commit()
    conn.close()

    # Mark stay nights in calendar as booked
    start = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(check_out, "%Y-%m-%d").date() - datetime.timedelta(days=1)
    batch_update_dates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), status="booked", note=f"Dikonfirmasi: {guest_name}")

    return {"status": "success", "message": f"Pemesanan berhasil disetujui (Dikonfirmasi)!"}


def reject_booking(booking_id, reason="", admin_user="admin"):
    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = 'REJECTED' WHERE id = ?", (booking_id,))

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason, changed_by)
            VALUES (?, ?, 'REJECTED', ?, ?)
        ''', (booking_id, prev_status, reason or 'Ditolak oleh admin', admin_user))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Pemesanan berhasil ditolak (REJECTED)."}


def cancel_booking(booking_id, reason="", admin_user="admin"):
    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (booking_id,))

    # If it was confirmed, free calendar dates back to ready
    if prev_status in ('CONFIRMED', 'confirmed'):
        start = datetime.datetime.strptime(str(booking['check_in'])[:10], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(str(booking['check_out'])[:10], "%Y-%m-%d").date() - datetime.timedelta(days=1)
        batch_update_dates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), status="ready", note="")

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason, changed_by)
            VALUES (?, ?, 'CANCELLED', ?, ?)
        ''', (booking_id, prev_status, reason or 'Dibatalkan', admin_user))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Pemesanan berhasil dibatalkan (CANCELLED)."}


def update_booking_status(booking_id, new_status, reason="", admin_user="admin"):
    valid_statuses = ['PENDING', 'WAITING_PAYMENT', 'WAITING_VERIFICATION', 'CONFIRMED', 'REJECTED', 'EXPIRED', 'CANCELLED', 'COMPLETED']
    norm_status = new_status.upper().strip()
    if norm_status not in valid_statuses:
        return {"status": "error", "message": f"Status tidak valid: {new_status}"}

    if norm_status == 'CONFIRMED':
        return confirm_booking(booking_id, admin_user)
    elif norm_status == 'REJECTED':
        return reject_booking(booking_id, reason, admin_user)
    elif norm_status == 'CANCELLED':
        return cancel_booking(booking_id, reason, admin_user)

    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (norm_status, booking_id))

    if prev_status in ('CONFIRMED', 'confirmed') and norm_status in ('EXPIRED', 'CANCELLED', 'REJECTED'):
        start = datetime.datetime.strptime(str(booking['check_in'])[:10], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(str(booking['check_out'])[:10], "%Y-%m-%d").date() - datetime.timedelta(days=1)
        batch_update_dates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), status="ready", note="")

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (booking_id, prev_status, norm_status, reason or 'Update status', admin_user))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Status booking berhasil diperbarui ke: {norm_status}"}


# -------------------------------------------------------------
# FINANCIAL EXPENSES & PAYMENTS ENGINE
# -------------------------------------------------------------

def get_expenses(month=None, start_date=None, end_date=None, category=None):
    conn = get_db_connection()
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if start_date and end_date:
        query += " AND CAST(expense_date AS TEXT) >= ? AND CAST(expense_date AS TEXT) <= ?"
        params.extend([start_date, end_date])
    elif month and month != 'all':
        query += " AND CAST(expense_date AS TEXT) LIKE ?"
        params.append(f"{month}-%")

    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY expense_date DESC, id DESC"
    
    rows = []
    try:
        rows = conn.execute(query, tuple(params)).fetchall()
    except Exception as e:
        print(f"get_expenses error: {e}")
    finally:
        conn.close()
        
    return [dict(r) for r in rows]


def add_expense(title, category, amount, expense_date, notes="", payment_method="Transfer Bank"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (title, category, amount, expense_date, payment_method, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, category, int(amount), expense_date, payment_method, notes))
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
    print("Database Supabase Data Architecture ready.")
