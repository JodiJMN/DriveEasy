"""
init_db.py — Inisialisasi & seeding database SQLite untuk DriveEasy
====================================================================
Jalankan SEKALI saat pertama deploy:

    python init_db.py

Aman dijalankan ulang — menggunakan INSERT OR IGNORE sehingga data
yang sudah ada tidak akan di-overwrite.

Environment variables (opsional, bisa set di .env):
    ADMIN_PASSWORD  — password admin default (default: Admin@DriveEasy2024)
"""

import os, sys
from dotenv import load_dotenv

# Tambahkan folder proyek ke sys.path agar bisa import dari app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app import app, init_db

if __name__ == '__main__':
    with app.app_context():
        init_db()
        print("=" * 55)
        print("  [OK] Database berhasil diinisialisasi!")
        print("=" * 55)
        print()
        print("  Akun admin default:")
        print("    Username : admin")
        print(f"    Password : {os.environ.get('ADMIN_PASSWORD', 'Admin@DriveEasy2024')}")
        print()
        print("  [!] SEGERA ganti password default setelah login!")
        print("=" * 55)
