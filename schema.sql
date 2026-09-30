-- Schema Database Villa Babeh untuk Supabase / PostgreSQL

-- 1. Table Calendar
CREATE TABLE IF NOT EXISTS calendar (
    date VARCHAR(10) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'ready',
    price INTEGER DEFAULT 1500000,
    note TEXT DEFAULT ''
);

-- 2. Table Facilities
CREATE TABLE IF NOT EXISTS facilities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    category VARCHAR(50) DEFAULT 'Umum',
    image_url TEXT DEFAULT ''
);

-- 3. Table Gallery
CREATE TABLE IF NOT EXISTS gallery (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    image_url TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'Umum'
);

-- 4. Table Bookings
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    guest_name VARCHAR(100) NOT NULL,
    guest_phone VARCHAR(50) NOT NULL,
    check_in VARCHAR(10) NOT NULL,
    check_out VARCHAR(10) NOT NULL,
    total_price INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table Payments
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    payment_name VARCHAR(100) NOT NULL,
    amount INTEGER NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 6. Table Settings
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT
);

-- 7. Table Expenses
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    category VARCHAR(50) DEFAULT 'Operasional',
    amount INTEGER NOT NULL,
    expense_date VARCHAR(10) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data Awal (Default Settings)
INSERT INTO settings (key, value) VALUES
('villa_name', 'Villa Babeh'),
('tagline', 'Mountain View Villa - Hunian Mewah & Asri untuk Liburan Keluarga Terbaik'),
('description', 'Villa Babeh menawarkan pengalaman menginap istimewa dengan fasilitas lengkap, kolam renang pribadi, pemandangan gunung & alam indah, dan suasana yang tenang & sejuk.'),
('whatsapp', '6281234567890'),
('weekday_price', '1500000'),
('weekend_price', '2200000'),
('address', 'Jl. Raya Puncak No. 88, Bogor, Jawa Barat'),
('admin_pin', '1234'),
('hero_image', 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80'),
('villa_logo', '/static/images/logo.jpg')
ON CONFLICT (key) DO NOTHING;

-- Data Awal Fasilitas
INSERT INTO facilities (name, description, icon, category, image_url) VALUES
('Kolam Renang Pribadi', 'Kolam renang bersih dengan kedalaman anak & dewasa + sunbed', 'swimming-pool', 'Utama', 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80'),
('4 Kamar Tidur AC', 'Kamar tidur luas dengan bed berkualitas hotel bintang 4 & AC dingin', 'bed', 'Kamar', 'https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=800&q=80'),
('Dapur & Alat BBQ Lengkap', 'Dilengkapi kulkas, kompor, alat masak, dispenser, dan pemanggang BBQ', 'utensils', 'Fasilitas', 'https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80'),
('Smart TV & Free WiFi', 'Internet kecepatan tinggi, Netflix, YouTube, dan Sound System Karaoke', 'tv', 'Hiburan', 'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80'),
('Halaman Luas & Gazebo', 'Area rumput hijau asri cocok untuk gathering, outbound, & bersantai', 'trees', 'Outdoor', 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80'),
('Parkir Kategori 5 Mobil', 'Area parkir aman dan luas di dalam benteng pagar villa', 'car', 'Keamanan', 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80');

-- Data Awal Galeri
INSERT INTO gallery (title, image_url, category) VALUES
('Tampak Depan & Halaman', 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80', 'Outdoor'),
('Private Swimming Pool', 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80', 'Kolam'),
('Ruang Keluarga & TV', 'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80', 'Interior'),
('Kamar Utama AC', 'https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=800&q=80', 'Kamar'),
('Dapur & Area BBQ', 'https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80', 'Dapur'),
('Taman & Gazebo', 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80', 'Outdoor');

-- Data Awal Pengeluaran
INSERT INTO expenses (title, category, amount, expense_date, notes) VALUES
('Listrik & Wifi Bulan September', 'Operasional', 650000, '2026-09-05', 'Tagihan bulanan PLN & Biznet'),
('Pembersihan Kolam & Obat Chlorine', 'Kebersihan', 350000, '2026-09-10', 'Beli kaporit & perawatan air kolam'),
('Gaji Staf Kebersihan & Jaga Villa', 'Gaji Staff', 1500000, '2026-09-28', 'Honor operasional bulanan');
