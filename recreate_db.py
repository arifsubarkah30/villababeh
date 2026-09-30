import os
import sqlite3

def recreate_database():
    db_file = 'villa.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("Removed existing villa.db")
        except Exception as e:
            print(f"Could not remove villa.db: {e}")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 1. Calendar Table
    cursor.execute('''
        CREATE TABLE calendar (
            date TEXT PRIMARY KEY,
            status TEXT DEFAULT 'ready',
            price INTEGER DEFAULT 1500000,
            note TEXT DEFAULT ''
        )
    ''')

    # 2. Facilities Table
    cursor.execute('''
        CREATE TABLE facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            category TEXT DEFAULT 'Umum',
            image_url TEXT DEFAULT ''
        )
    ''')

    # 3. Gallery Table
    cursor.execute('''
        CREATE TABLE gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image_url TEXT NOT NULL,
            category TEXT DEFAULT 'Umum'
        )
    ''')

    # 4. Bookings Table
    cursor.execute('''
        CREATE TABLE bookings (
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

    # 5. Payments Table
    cursor.execute('''
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            payment_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        )
    ''')

    # 6. Settings Table
    cursor.execute('''
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # 7. Expenses Table
    cursor.execute('''
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'Operasional',
            amount INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Master Settings
    default_settings = {
        "villa_name": "Villa Babeh",
        "tagline": "Mountain View Villa - Hunian Mewah & Asri untuk Liburan Keluarga Terbaik",
        "description": "Villa Babeh menawarkan pengalaman menginap istimewa dengan fasilitas lengkap, kolam renang pribadi, pemandangan gunung & alam indah, dan suasana yang tenang & sejuk.",
        "whatsapp": "6281295398434",
        "weekday_price": "1500000",
        "middle_price": "1800000",
        "weekend_price": "2200000",
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
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Master Facilities (Hotel Quality Default Facilities)
    default_facilities = [
        ("Kolam Renang Pribadi", "Kolam renang bersih dengan kedalaman anak & dewasa + sunbed santai", "swimming-pool", "Utama", "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80"),
        ("4 Kamar Tidur AC", "Kamar tidur luas dengan bed berkualitas hotel bintang 4 & AC dingin", "bed", "Kamar", "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=800&q=80"),
        ("Dapur & Alat BBQ Lengkap", "Dilengkapi kulkas, kompor, alat masak, dispenser, dan pemanggang BBQ", "utensils", "Fasilitas", "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80"),
        ("Smart TV & Free WiFi", "Internet kecepatan tinggi, Netflix, YouTube, dan Sound System Karaoke", "tv", "Hiburan", "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80"),
        ("Halaman Luas & Gazebo", "Area rumput hijau asri cocok untuk gathering, outbound, & bersantai", "trees", "Outdoor", "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80"),
        ("Parkir Kategori 5 Mobil", "Area parkir aman dan luas di dalam benteng pagar villa", "car", "Keamanan", "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80")
    ]
    cursor.executemany("INSERT INTO facilities (name, description, icon, category, image_url) VALUES (?, ?, ?, ?, ?)", default_facilities)

    # Master Gallery Photos
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
    print("Database villa.db freshly created with all master settings, facilities, and gallery!")

if __name__ == "__main__":
    recreate_database()
