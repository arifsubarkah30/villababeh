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
        sql_conv = sql_conv.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        
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
        elif "INSERT OR REPLACE INTO" in sql_conv:
            sql_conv = sql_conv.replace("INSERT OR REPLACE INTO", "INSERT INTO")
        elif "INSERT OR IGNORE INTO" in sql_conv:
            sql_conv = sql_conv.replace("INSERT OR IGNORE INTO", "INSERT INTO") + " ON CONFLICT DO NOTHING"

        if any(tok in sql_conv for tok in ["INSERT INTO bookings", "INSERT INTO payments", "INSERT INTO expenses", "INSERT INTO facilities", "INSERT INTO gallery", "INSERT INTO calendar_blocks", "INSERT INTO special_prices"]):
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
        url_to_use = db_url.replace("postgres://", "postgresql://", 1)
        if "sslmode" not in url_to_use:
            separator = "&" if "?" in url_to_use else "?"
            url_to_use += f"{separator}sslmode=require"
        try:
            conn = psycopg2.connect(url_to_use)
            return PgConnWrapper(conn)
        except Exception as err:
            print(f"CRITICAL: Supabase PG connection failed: {err}")
            raise RuntimeError(f"Gagal terhubung ke Supabase Database: {err}")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        is_pg = os.environ.get("DATABASE_URL") is not None
        id_pk = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar (
                date TEXT PRIMARY KEY,
                status TEXT DEFAULT 'ready',
                price INTEGER DEFAULT 1800000,
                note TEXT DEFAULT ''
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS special_prices (
                date TEXT PRIMARY KEY,
                price INTEGER NOT NULL,
                note TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT true
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS calendar_blocks (
                {id_pk},
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'MAINTENANCE',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS facilities (
                {id_pk},
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                category TEXT DEFAULT 'Umum',
                image_url TEXT DEFAULT ''
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS gallery (
                {id_pk},
                title TEXT NOT NULL,
                image_url TEXT NOT NULL,
                category TEXT DEFAULT 'Umum'
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS bookings (
                {id_pk},
                booking_code TEXT UNIQUE,
                guest_name TEXT NOT NULL,
                guest_phone TEXT NOT NULL,
                guest_ig TEXT DEFAULT '-',
                total_guests TEXT DEFAULT '10 Orang',
                check_in TEXT NOT NULL,
                check_out TEXT NOT NULL,
                total_price INTEGER NOT NULL,
                status TEXT DEFAULT 'PENDING',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS payments (
                {id_pk},
                booking_id INTEGER NOT NULL,
                payment_name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS expenses (
                {id_pk},
                title TEXT NOT NULL,
                category TEXT DEFAULT 'Operasional',
                amount INTEGER NOT NULL,
                expense_date TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS booking_status_history (
                {id_pk},
                booking_id INTEGER NOT NULL,
                previous_status TEXT,
                new_status TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                {id_pk},
                user_id TEXT,
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                details TEXT,
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

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"init_db warning/error: {e}")

DEFAULT_SETTINGS = {
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

def get_settings():
    res = dict(DEFAULT_SETTINGS)
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        for row in rows:
            if row["key"] and row["value"]:
                res[row["key"]] = row["value"]
    except Exception as e:
        print(f"get_settings warning: {e}")
    return res

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

    # Priority 1: SPECIAL DATE PRICE (special_prices table or calendar table)
    sp_row = conn.execute("SELECT price, note FROM special_prices WHERE date = ?", (date_str,)).fetchone()
    if not sp_row:
        sp_row = conn.execute("SELECT price, note FROM calendar WHERE date = ?", (date_str,)).fetchone()

    if sp_row and sp_row["price"] is not None and int(sp_row["price"]) > 0:
        price = int(sp_row["price"])
        is_special = True
    else:
        # Priority 3: DAY-OF-WEEK PRICE from pricing_rules
        rule = conn.execute("SELECT price, category FROM pricing_rules WHERE day_of_week = ?", (day_name_en,)).fetchone()
        if rule and rule["price"] is not None:
            price = int(rule["price"])
        else:
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

def create_booking_request(guest_name, guest_phone, check_in, check_out, guest_ig="-", total_guests="10 Orang", notes=""):
    import random
    start = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(check_out, "%Y-%m-%d").date()
    
    if end <= start:
        return {"status": "error", "message": "Tanggal Check-out harus setelah Check-in"}

    calc_res = calculate_booking_price(check_in, check_out)
    
    conn = get_db_connection()
    
    # Check date overlap against CONFIRMED bookings
    overlap = conn.execute('''
        SELECT booking_code, guest_name FROM bookings
        WHERE (status = 'CONFIRMED' OR status = 'confirmed')
          AND check_in < ? AND check_out > ?
    ''', (check_out, check_in)).fetchone()

    if overlap:
        conn.close()
        return {"status": "error", "message": f"Maaf, tanggal {check_in} s/d {check_out} sudah terbooking ({overlap['guest_name']})!"}

    # Check date overlap against calendar_blocks
    overlap_block = conn.execute('''
        SELECT status, note FROM calendar_blocks
        WHERE start_date < ? AND end_date > ?
    ''', (check_out, check_in)).fetchone()

    if overlap_block:
        conn.close()
        return {"status": "error", "message": f"Maaf, tanggal tersebut dalam pemeliharaan ({overlap_block['note'] or 'Maintenance'})!"}

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
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason)
            VALUES (?, NULL, 'PENDING', 'Customer booking request created')
        ''', (booking_id,))
    except Exception:
        pass

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "booking_id": booking_id,
        "booking_code": booking_code,
        "total_price": total_price,
        "breakdown": calc_res['breakdown'],
        "message": "Pemesanan berhasil dikirim (Status: PENDING)!"
    }

def confirm_booking(booking_id):
    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    check_in = booking["check_in"]
    check_out = booking["check_out"]
    guest_name = booking["guest_name"]

    overlap = conn.execute('''
        SELECT booking_code, guest_name FROM bookings
        WHERE (status = 'CONFIRMED' OR status = 'confirmed') AND id != ?
          AND check_in < ? AND check_out > ?
    ''', (booking_id, check_out, check_in)).fetchone()

    if overlap:
        conn.close()
        return {
            "status": "error",
            "message": f"Konflik jadwal! Tanggal tersebut sudah terkonfirmasi oleh pemesanan lain ({overlap['guest_name']} / {overlap['booking_code']})"
        }

    overlap_block = conn.execute('''
        SELECT status, note FROM calendar_blocks
        WHERE start_date < ? AND end_date > ?
    ''', (check_out, check_in)).fetchone()

    if overlap_block:
        conn.close()
        return {
            "status": "error",
            "message": f"Konflik jadwal! Tanggal tersebut sedang dalam masa pemeliharaan ({overlap_block['status']}: {overlap_block['note'] or ''})"
        }

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = ?", (booking_id,))

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason)
            VALUES (?, ?, 'CONFIRMED', 'Admin confirmation')
        ''', (booking_id, prev_status))
    except Exception:
        pass

    conn.commit()
    conn.close()

    start = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(check_out, "%Y-%m-%d").date() - datetime.timedelta(days=1)
    batch_update_dates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), status="booked", note=f"Booked: {guest_name}")

    return {"status": "success", "message": f"Pemesanan berhasil dikonfirmasi (CONFIRMED)!"}

def reject_booking(booking_id, reason=""):
    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = 'REJECTED' WHERE id = ?", (booking_id,))

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason)
            VALUES (?, ?, 'REJECTED', ?)
        ''', (booking_id, prev_status, reason or 'Admin rejection'))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Pemesanan ditolak (REJECTED)."}

def cancel_booking(booking_id, reason=""):
    conn = get_db_connection()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return {"status": "error", "message": "Pemesanan tidak ditemukan!"}

    prev_status = booking["status"]
    conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (booking_id,))

    if prev_status in ('CONFIRMED', 'confirmed'):
        start = datetime.datetime.strptime(booking['check_in'], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(booking['check_out'], "%Y-%m-%d").date() - datetime.timedelta(days=1)
        batch_update_dates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), status="ready", note="")

    try:
        conn.execute('''
            INSERT INTO booking_status_history (booking_id, previous_status, new_status, reason)
            VALUES (?, ?, 'CANCELLED', ?)
        ''', (booking_id, prev_status, reason or 'Cancellation'))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Pemesanan dibatalkan (CANCELLED)."}

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

    db_map = {row["date"]: dict(row) for row in rows if row["date"]}

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
    print("Database Supabase Data Architecture ready.")
