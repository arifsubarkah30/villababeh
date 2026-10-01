-- =====================================================================
-- VILLA BABEH — FULL SUPABASE DATA ARCHITECTURE (MIGRATION SCRIPT)
-- Single Source of Truth: Supabase PostgreSQL, Auth, Storage, RLS
-- Safe for existing tables (Idempotent)
-- =====================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------
-- 1. PROFILES TABLE (Supabase Auth Integration)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    role TEXT CHECK (role IN ('admin', 'staff')) DEFAULT 'admin',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 2. VILLA SETTINGS TABLE
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS villa_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    villa_name TEXT NOT NULL DEFAULT 'Villa Babeh',
    description TEXT DEFAULT 'Villa Babeh menawarkan pengalaman menginap istimewa dengan fasilitas lengkap, kolam renang pribadi, pemandangan gunung & alam indah, dan suasana yang tenang & sejuk.',
    capacity INTEGER DEFAULT 25,
    bedroom_count INTEGER DEFAULT 4,
    address TEXT DEFAULT 'Jl. Raya Puncak No. 88, Bogor, Jawa Barat',
    whatsapp TEXT DEFAULT '6281295398434',
    instagram TEXT DEFAULT '@villababeh.official',
    google_maps_url TEXT DEFAULT 'https://maps.google.com',
    check_in_time TEXT DEFAULT '14:00 WIB',
    check_out_time TEXT DEFAULT '12:00 WIB',
    admin_pin TEXT DEFAULT '1234',
    hero_image_url TEXT DEFAULT 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80',
    villa_logo_url TEXT DEFAULT '/static/images/logo.jpg',
    highlight_1_title TEXT DEFAULT '4 Kamar',
    highlight_1_sub TEXT DEFAULT 'AC + Bed Super King',
    highlight_2_title TEXT DEFAULT 'Private Pool',
    highlight_2_sub TEXT DEFAULT 'Kolam Renang Bersih',
    highlight_3_title TEXT DEFAULT '30 Orang',
    highlight_3_sub TEXT DEFAULT 'Kapasitas Tamu',
    highlight_4_title TEXT DEFAULT 'Smart TV',
    highlight_4_sub TEXT DEFAULT 'Sound Karaoke & WiFi',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure columns exist in case table was created previously
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS hero_image_url TEXT DEFAULT 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1600&q=80';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS villa_logo_url TEXT DEFAULT '/static/images/logo.jpg';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_1_title TEXT DEFAULT '4 Kamar';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_1_sub TEXT DEFAULT 'AC + Bed Super King';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_2_title TEXT DEFAULT 'Private Pool';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_2_sub TEXT DEFAULT 'Kolam Renang Bersih';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_3_title TEXT DEFAULT '30 Orang';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_3_sub TEXT DEFAULT 'Kapasitas Tamu';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_4_title TEXT DEFAULT 'Smart TV';
ALTER TABLE villa_settings ADD COLUMN IF NOT EXISTS highlight_4_sub TEXT DEFAULT 'Sound Karaoke & WiFi';

-- Initial seed for villa_settings
INSERT INTO villa_settings (villa_name, capacity, bedroom_count)
SELECT 'Villa Babeh', 25, 4
WHERE NOT EXISTS (SELECT 1 FROM villa_settings);

-- ---------------------------------------------------------------------
-- 3. FACILITIES TABLE
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT 'star',
    category TEXT DEFAULT 'Umum',
    image_url TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure columns exist in facilities if table already existed
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS icon TEXT DEFAULT 'star';
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'Umum';
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS image_url TEXT DEFAULT '';
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Initial seed for facilities
INSERT INTO facilities (name, description, icon, category, image_url, sort_order) VALUES
('Private Pool', 'Kolam renang bersih dengan kedalaman anak & dewasa + sunbed santai', 'swimming-pool', 'Utama', 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80', 1),
('Playground', 'Area bermain anak aman dan menyenangkan', 'smile', 'Outdoor', 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80', 2),
('Biliar', 'Meja biliar standar profesional untuk bersantai', 'gamepad-2', 'Hiburan', 'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80', 3),
('Rooftop', 'Area santai rooftop view pegunungan indah', 'sun', 'Outdoor', 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80', 4),
('Lahan Parkir Luas', 'Area parkir aman dalam benteng pagar villa muat hingga 5 mobil', 'car', 'Keamanan', 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80', 5)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- 4. GALLERY TABLE (Metadata connected to Supabase Storage)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gallery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_path TEXT,
    public_url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'Umum',
    sort_order INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure columns exist in gallery if table already existed
ALTER TABLE gallery ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE gallery ADD COLUMN IF NOT EXISTS public_url TEXT;
ALTER TABLE gallery ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'Umum';
ALTER TABLE gallery ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;
ALTER TABLE gallery ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;

-- Initial seed for gallery
INSERT INTO gallery (title, public_url, category, sort_order) VALUES
('Tampak Depan & Halaman', 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80', 'Outdoor', 1),
('Private Swimming Pool', 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=800&q=80', 'Kolam', 2),
('Ruang Keluarga & TV', 'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=800&q=80', 'Interior', 3),
('Kamar Utama AC', 'https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=800&q=80', 'Kamar', 4)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- 5. PRICING RULES TABLE (Standard Day-of-Week Rules)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pricing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL CHECK (category IN ('WEEKDAY', 'MIDDLE', 'WEEKEND')),
    day_of_week TEXT NOT NULL UNIQUE CHECK (day_of_week IN ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')),
    price NUMERIC(12, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Initial seed for pricing_rules
INSERT INTO pricing_rules (category, day_of_week, price) VALUES
('WEEKDAY', 'Sunday', 1800000),
('WEEKDAY', 'Monday', 1800000),
('WEEKDAY', 'Tuesday', 1800000),
('WEEKDAY', 'Wednesday', 1800000),
('WEEKDAY', 'Thursday', 1800000),
('MIDDLE', 'Friday', 2200000),
('WEEKEND', 'Saturday', 3850000)
ON CONFLICT (day_of_week) DO NOTHING;

-- ---------------------------------------------------------------------
-- 6. SPECIAL PRICES TABLE (Specific Date Overrides)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS special_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL UNIQUE,
    price NUMERIC(12, 2) NOT NULL,
    note TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 7. CALENDAR BLOCKS TABLE (Maintenance / Closed Periods)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calendar_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'MAINTENANCE' CHECK (status IN ('MAINTENANCE', 'CLOSED')),
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 8. BOOKINGS TABLE (Customer & Admin Booking Engine)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_code VARCHAR(50) UNIQUE NOT NULL,
    guest_name VARCHAR(100) NOT NULL,
    guest_phone VARCHAR(50) NOT NULL,
    guest_ig VARCHAR(100),
    total_guests VARCHAR(50) DEFAULT '10 Orang',
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    total_price NUMERIC(12, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'CONFIRMED', 'REJECTED', 'CANCELLED', 'COMPLETED')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast query execution
CREATE INDEX IF NOT EXISTS idx_bookings_code ON bookings(booking_code);
CREATE INDEX IF NOT EXISTS idx_bookings_check_in ON bookings(check_in);
CREATE INDEX IF NOT EXISTS idx_bookings_check_out ON bookings(check_out);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_created_at ON bookings(created_at);
CREATE INDEX IF NOT EXISTS idx_special_prices_date ON special_prices(date);
CREATE INDEX IF NOT EXISTS idx_calendar_blocks_range ON calendar_blocks(start_date, end_date);

-- ---------------------------------------------------------------------
-- 9. PAYMENTS TABLE
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    payment_name VARCHAR(100) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    payment_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 10. EXPENSES TABLE (Operational Expenses)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(150) NOT NULL,
    category VARCHAR(50) DEFAULT 'Operasional',
    amount NUMERIC(12, 2) NOT NULL,
    expense_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 11. BOOKING STATUS HISTORY TABLE
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS booking_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 12. AUDIT LOGS TABLE
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE villa_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE facilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE gallery ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE special_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE booking_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist to prevent duplicate errors
DROP POLICY IF EXISTS "Public Read Villa Settings" ON villa_settings;
DROP POLICY IF EXISTS "Public Read Active Facilities" ON facilities;
DROP POLICY IF EXISTS "Public Read Gallery" ON gallery;
DROP POLICY IF EXISTS "Public Read Pricing Rules" ON pricing_rules;
DROP POLICY IF EXISTS "Public Read Special Prices" ON special_prices;
DROP POLICY IF EXISTS "Public Read Calendar Blocks" ON calendar_blocks;
DROP POLICY IF EXISTS "Public Read Bookings Availability" ON bookings;
DROP POLICY IF EXISTS "Public Create Booking Request" ON bookings;
DROP POLICY IF EXISTS "Admin All Villa Settings" ON villa_settings;
DROP POLICY IF EXISTS "Admin All Facilities" ON facilities;
DROP POLICY IF EXISTS "Admin All Gallery" ON gallery;
DROP POLICY IF EXISTS "Admin All Pricing Rules" ON pricing_rules;
DROP POLICY IF EXISTS "Admin All Special Prices" ON special_prices;
DROP POLICY IF EXISTS "Admin All Calendar Blocks" ON calendar_blocks;
DROP POLICY IF EXISTS "Admin All Bookings" ON bookings;
DROP POLICY IF EXISTS "Admin All Payments" ON payments;
DROP POLICY IF EXISTS "Admin All Expenses" ON expenses;
DROP POLICY IF EXISTS "Admin All Status History" ON booking_status_history;
DROP POLICY IF EXISTS "Admin All Audit Logs" ON audit_logs;

-- Public Read Policies
CREATE POLICY "Public Read Villa Settings" ON villa_settings FOR SELECT USING (true);
CREATE POLICY "Public Read Active Facilities" ON facilities FOR SELECT USING (is_active = true);
CREATE POLICY "Public Read Gallery" ON gallery FOR SELECT USING (true);
CREATE POLICY "Public Read Pricing Rules" ON pricing_rules FOR SELECT USING (is_active = true);
CREATE POLICY "Public Read Special Prices" ON special_prices FOR SELECT USING (is_active = true);
CREATE POLICY "Public Read Calendar Blocks" ON calendar_blocks FOR SELECT USING (true);
CREATE POLICY "Public Read Bookings Availability" ON bookings FOR SELECT USING (true);

-- Public Insert Policy for Bookings (Customers can create booking requests)
CREATE POLICY "Public Create Booking Request" ON bookings FOR INSERT WITH CHECK (true);

-- Admin Full Access Policies (authenticated users / service role)
CREATE POLICY "Admin All Villa Settings" ON villa_settings FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Facilities" ON facilities FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Gallery" ON gallery FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Pricing Rules" ON pricing_rules FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Special Prices" ON special_prices FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Calendar Blocks" ON calendar_blocks FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Bookings" ON bookings FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Payments" ON payments FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Expenses" ON expenses FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Status History" ON booking_status_history FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Admin All Audit Logs" ON audit_logs FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- =====================================================================
-- SUPABASE STORAGE BUCKET CREATION (villa-gallery)
-- =====================================================================
INSERT INTO storage.buckets (id, name, public) 
VALUES ('villa-gallery', 'villa-gallery', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Public Access Storage" ON storage.objects;
DROP POLICY IF EXISTS "Admin Upload Storage" ON storage.objects;
DROP POLICY IF EXISTS "Admin Update Storage" ON storage.objects;
DROP POLICY IF EXISTS "Admin Delete Storage" ON storage.objects;

CREATE POLICY "Public Access Storage" ON storage.objects FOR SELECT USING (bucket_id = 'villa-gallery');
CREATE POLICY "Admin Upload Storage" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'villa-gallery');
CREATE POLICY "Admin Update Storage" ON storage.objects FOR UPDATE USING (bucket_id = 'villa-gallery');
CREATE POLICY "Admin Delete Storage" ON storage.objects FOR DELETE USING (bucket_id = 'villa-gallery');
