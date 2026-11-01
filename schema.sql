-- VetMind AI Database Schema (DDL Structure - Compatible with SQLite, Turso, and PostgreSQL)
-- Tables are created first, followed by performance indexes.


-- Object: table appointments
CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        pet_name TEXT NOT NULL,
        species TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'confirmed',
        created_at TEXT NOT NULL
    , owner_name TEXT, owner_phone TEXT);

-- Object: table broadcast_notifications
CREATE TABLE IF NOT EXISTS broadcast_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        target_country TEXT DEFAULT 'ALL',
        badge_type TEXT DEFAULT 'info',
        created_at TEXT NOT NULL
    );

-- Object: table cases
CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_name TEXT NOT NULL,
            species TEXT NOT NULL,
            age TEXT,
            weight TEXT,
            symptoms TEXT NOT NULL,
            duration TEXT NOT NULL,
            image_filename TEXT,
            triage_level TEXT NOT NULL,
            triage_note TEXT NOT NULL,
            created_at TEXT NOT NULL
        , analysis_json TEXT, user_id INTEGER DEFAULT 1, diagnosis TEXT DEFAULT '', client_name TEXT DEFAULT '');

-- Object: table chat_messages
CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        image_filename TEXT,
        created_at TEXT NOT NULL, image_path TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

-- Object: table client_operations
CREATE TABLE IF NOT EXISTS client_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        client_phone TEXT,
        client_avatar TEXT,
        animal_name TEXT NOT NULL,
        species TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        operation_details TEXT,
        fee_collected REAL DEFAULT 0,
        performed_at TEXT NOT NULL,
        status TEXT DEFAULT 'completed'
    );

-- Object: table clinic_prescriptions
CREATE TABLE IF NOT EXISTS clinic_prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_no TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    animal_name TEXT NOT NULL,
    species TEXT NOT NULL,
    breed TEXT,
    age TEXT,
    weight REAL NOT NULL,
    owner_name TEXT NOT NULL,
    owner_phone TEXT,
    diagnosis TEXT NOT NULL,
    rx_items_json TEXT NOT NULL,
    withdrawal_warning TEXT,
    doctor_instructions TEXT,
    created_at TEXT NOT NULL
);

-- Object: table clinic_profiles
CREATE TABLE IF NOT EXISTS clinic_profiles (
        user_id INTEGER PRIMARY KEY,
        clinic_name TEXT,
        phone TEXT,
        address TEXT,
        consultation_fee TEXT,
        working_hours TEXT,
        emergency_available INTEGER DEFAULT 1,
        notes TEXT
    , logo_filename TEXT, doctor_title TEXT, license_no TEXT, tagline TEXT, header_color TEXT DEFAULT '#047857', watermark_enabled INTEGER DEFAULT 1);

-- Object: table drug_inventory
CREATE TABLE IF NOT EXISTS drug_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drug_name TEXT NOT NULL,
        active_ingredient TEXT NOT NULL,
        category TEXT NOT NULL,
        stock_quantity INTEGER NOT NULL,
        unit TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        price REAL NOT NULL
    , user_id INTEGER DEFAULT 0, min_threshold INTEGER DEFAULT 10);

-- Object: table invoices
CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        service_name TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'paid',
        payment_method TEXT DEFAULT 'cash',
        created_at TEXT NOT NULL
    );

-- Object: table lab_tests
CREATE TABLE IF NOT EXISTS lab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        animal_name TEXT NOT NULL,
        test_type TEXT NOT NULL,
        test_date TEXT NOT NULL,
        result_summary TEXT NOT NULL,
        attachment_filename TEXT,
        created_at TEXT NOT NULL
    );

-- Object: table local_products
CREATE TABLE IF NOT EXISTS local_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT NOT NULL,
        trade_name TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        active_ingredient TEXT NOT NULL,
        category TEXT NOT NULL,
        indication TEXT NOT NULL,
        target_species TEXT NOT NULL,
        dosage_guide TEXT NOT NULL,
        withdrawal_period TEXT,
        approval_reg_no TEXT
    );

-- Object: table settings
CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

-- Object: table support_tickets
CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        doctor_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        country TEXT,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'open',
        created_at TEXT NOT NULL
    );

-- Object: table users
CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'vet',
        created_at TEXT NOT NULL
    , id_card_image TEXT, verification_status TEXT DEFAULT 'pending', is_admin INTEGER DEFAULT 0, country TEXT DEFAULT '???', clinic_name TEXT, syndicate_id TEXT, phone TEXT DEFAULT '+201000000000', avatar_image TEXT DEFAULT '', is_premium INTEGER DEFAULT 0, is_email_verified INTEGER DEFAULT 1, otp_code TEXT DEFAULT '', otp_expiry TEXT DEFAULT '', last_active_at TEXT, otp_expires_at TEXT, preferred_lang TEXT DEFAULT 'ar', bio TEXT DEFAULT '', cover_photo TEXT DEFAULT '', reputation_score INTEGER DEFAULT 100, verified_vet INTEGER DEFAULT 1, specialty TEXT DEFAULT 'طب وجراحة الحيوان', work_place TEXT DEFAULT '', city TEXT DEFAULT '', privacy_show_phone INTEGER DEFAULT 0, privacy_show_email INTEGER DEFAULT 0, privacy_posts_default TEXT DEFAULT 'public');

-- Object: table vaccinations
CREATE TABLE IF NOT EXISTS vaccinations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        animal_name TEXT NOT NULL,
        vaccine_name TEXT NOT NULL,
        dose_number TEXT,
        administered_date TEXT NOT NULL,
        next_due_date TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL
    , species TEXT DEFAULT 'أبقار');

-- Object: table verification_logs
CREATE TABLE IF NOT EXISTS verification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        email TEXT,
        phone TEXT,
        otp_code TEXT,
        channel TEXT,
        status TEXT,
        created_at TEXT
    );

-- Object: table media_files
CREATE TABLE IF NOT EXISTS media_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        mime_type TEXT NOT NULL,
        data_b64 TEXT NOT NULL,
        size_bytes INTEGER DEFAULT 0,
        owner_id INTEGER DEFAULT 0,
        is_private INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );

-- Object: index idx_media_filename
CREATE INDEX IF NOT EXISTS idx_media_filename ON media_files(filename);
