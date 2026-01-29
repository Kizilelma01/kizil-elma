from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime
import sqlite3
import random # Rastgele sayı için eklendi
import string

app = Flask(__name__)
app.secret_key = 'kizil_elma_ultra_secure_2026'

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Veritabanını sıfırdan ve doğru sütunlarla oluşturur
def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             anahtar TEXT UNIQUE, 
             fullname TEXT, 
             bitis_tarihi TEXT, 
             role TEXT DEFAULT 'user',
             ip_address TEXT DEFAULT NULL,
             created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
             action TEXT, detail TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        admin = conn.execute('SELECT * FROM users WHERE anahtar = ?', ('KIZILELMA2026',)).fetchone()
        if not admin:
            conn.execute('INSERT INTO users (anahtar, fullname, bitis_tarihi, role) VALUES (?, ?, ?, ?)',
                         ('KIZILELMA2026', 'admin', '2026-12-31', 'admin'))
        conn.commit()

init_db()

# --- OTOMATİK ANAHTAR OLUŞTURUCU ---
def anahtar_olustur():
    sayilar = ''.join(random.choices(string.digits, k=5))
    return f"KIZILELMA{sayilar}"

def log_ekle(user_id, action, detail):
    with get_db() as conn:
        conn.execute('INSERT INTO logs (user_id, action, detail) VALUES (?, ?, ?)', (user_id, action, detail))
        conn.commit()

# --- ROTALAR ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        anahtar_input = request.form.get('anahtar')
        user_ip = request.remote_addr
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE anahtar = ?', (anahtar_input,)).fetchone()
            if user:
                if user['ip_address'] is None:
                    conn.execute('UPDATE users SET ip_address = ? WHERE id = ?', (user_ip, user['id']))
                    conn.commit()
                elif user['ip_address'] != user_ip and user['role'] != 'admin':
                    flash('Bu anahtar başka bir cihazda kilitli!')
                    return redirect(url_for('login'))
                session.update({'user_id': user['id'], 'fullname': user['fullname'], 'role': user['role']})
                return redirect(url_for('index'))
        flash('Geçersiz anahtar!')
    return render_template('login.html')

@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        bitis = datetime.strptime(user['bitis_tarihi'], "%Y-%m-%d")
        kalan = max(0, (bitis - datetime.now()).days)
    return render_template('index.html', user=user, kalan_sure=kalan)

# --- YÖNETİM PANELİ: KULLANICI EKLEME (GÜNCELLENDİ) ---
@app.route('/admin/user/add', methods=['POST'])
def user_add():
    if session.get('role') != 'admin': return "Yetkisiz", 403
    
    fullname = request.form.get('fullname')
    bitis_tarihi = request.form.get('bitis_tarihi')
    yeni_anahtar = anahtar_olustur() # Anahtarı sistem otomatik oluşturur
    
    with get_db() as conn:
        conn.execute('INSERT INTO users (anahtar, fullname, bitis_tarihi) VALUES (?, ?, ?)',
                     (yeni_anahtar, fullname, bitis_tarihi))
        conn.commit()
    
    flash(f'Kullanıcı Eklendi! Anahtar: {yeni_anahtar}')
    return redirect(url_for('admin_panel'))

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin': return "Yetkisiz!", 403
    with get_db() as conn:
        users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
        logs = conn.execute('SELECT logs.*, users.fullname FROM logs JOIN users ON logs.user_id = users.id ORDER BY timestamp DESC LIMIT 100').fetchall()
    return render_template('admin.html', users=users, logs=logs)

# --- DİĞER ROTALAR ---
@app.route('/kisi-cozumleri')
def kisi_sayfasi(): return render_template('sorgu.html')
@app.route('/gsm-cozumleri')
def gsm_sayfasi(): return render_template('gsm_sorgu.html')
@app.route('/adres-cozumleri')
def adres_sayfasi(): return render_template('adres_sorgu.html')
@app.route('/diger-cozumleri')
def diger_sayfasi(): return render_template('diger.html')
@app.route('/profil')
def profil_sayfasi():
    with get_db() as conn:
        u = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        q = conn.execute('SELECT COUNT(*) as c FROM logs WHERE user_id = ? AND action LIKE "%Sorgu%"', (u['id'],)).fetchone()['c']
        l = conn.execute('SELECT timestamp FROM logs WHERE user_id = ? AND action = "Giriş" ORDER BY timestamp DESC LIMIT 1', (u['id'],)).fetchone()
    return render_template('profil.html', user=u, total_queries=q, last_login=l, kalan=max(0, (datetime.strptime(u['bitis_tarihi'], "%Y-%m-%d") - datetime.now()).days))

@app.route('/cikis')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
