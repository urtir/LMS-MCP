import sqlite3
import os

# Koneksi ke database menggunakan environment variables
DATABASE_DIR = os.getenv('DATABASE_DIR', './data')
WAZUH_DB_NAME = os.getenv('WAZUH_DB_NAME', 'wazuh_archives.db')
DB_PATH = os.path.join(DATABASE_DIR, WAZUH_DB_NAME)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Cek jumlah records
cursor.execute('SELECT COUNT(*) FROM wazuh_archives')
print('Total records:', cursor.fetchone()[0])

# Cek contoh data
cursor.execute('SELECT * FROM wazuh_archives LIMIT 3')
rows = cursor.fetchall()
for i, row in enumerate(rows):
    print(f"Row {i+1}:", row)

# Cek distribusi rule_level
cursor.execute('SELECT rule_level, COUNT(*) FROM wazuh_archives GROUP BY rule_level ORDER BY rule_level')
print('\nRule Level Distribution:')
for row in cursor.fetchall():
    print(f"Level {row[0]}: {row[1]} alerts")

# Cek agent yang paling aktif
cursor.execute('SELECT agent_name, COUNT(*) as count FROM wazuh_archives WHERE agent_name IS NOT NULL GROUP BY agent_name ORDER BY count DESC LIMIT 5')
print('\nTop 5 Active Agents:')
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} alerts")

conn.close()
