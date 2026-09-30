from flask import Flask, render_template, request, jsonify, Response
import database as db
import datetime
import os
import csv
import io
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
if os.environ.get("VERCEL"):
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize database on startup
try:
    db.init_db()
except Exception as e:
    print(f"Startup DB init warning: {e}")


@app.route('/')
def index():
    settings = db.get_settings()
    return render_template('index.html', settings=settings)

@app.route('/admin')
def admin_page():
    settings = db.get_settings()
    return render_template('admin.html', settings=settings)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Tidak ada berkas diunggah"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Nama berkas kosong"}), 400
    
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")
    filename = timestamp + filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    image_url = f"/static/uploads/{filename}"
    return jsonify({"status": "success", "image_url": image_url, "message": "Foto/Logo berhasil diunggah!"})

@app.route('/api/calendar')
def get_calendar():
    year = int(request.args.get('year', datetime.date.today().year))
    month = int(request.args.get('month', datetime.date.today().month))
    calendar_data = db.get_month_calendar(year, month)
    return jsonify({
        "status": "success",
        "year": year,
        "month": month,
        "dates": calendar_data
    })

@app.route('/api/calendar/update', methods=['POST'])
def update_calendar():
    data = request.json or {}
    start_date = data.get('start_date')
    end_date = data.get('end_date') or start_date
    status = data.get('status')
    price = data.get('price')
    note = data.get('note', '')

    if not start_date:
        return jsonify({"status": "error", "message": "Tanggal wajib diisi"}), 400

    try:
        if price is not None and str(price).strip() != '':
            price = int(price)
        else:
            price = None
        db.batch_update_dates(start_date, end_date, status=status, price=price, note=note)
        return jsonify({"status": "success", "message": "Jadwal & harga berhasil diperbarui!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/calendar/sync_holidays', methods=['POST'])
def sync_holidays():
    data = request.json or {}
    year = int(data.get('year', datetime.date.today().year))
    try:
        count = db.sync_national_holidays(year)
        return jsonify({
            "status": "success",
            "message": f"Berhasil menyingkronkan {count} Tanggal Merah / Hari Libur Nasional tahun {year}!"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/verify_pin', methods=['POST'])
def verify_admin_pin():
    data = request.json or {}
    pin = str(data.get('pin', '')).strip()
    current_pin = str(db.get_settings().get('admin_pin', '1234')).strip()
    if pin and pin == current_pin:
        return jsonify({"status": "success", "message": "PIN Admin Valid!"})
    else:
        return jsonify({"status": "error", "message": "PIN Admin salah!"}), 401

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        return jsonify({"status": "success", "settings": db.get_settings()})
    else:
        data = request.json or {}
        if not data:
            return jsonify({"status": "error", "message": "Data tidak boleh kosong"}), 400

        db.update_settings(data)
        return jsonify({"status": "success", "message": "Pengaturan villa berhasil disimpan!", "settings": db.get_settings()})

@app.route('/api/facilities', methods=['GET', 'POST', 'DELETE'])
def handle_facilities():
    conn = db.get_db_connection()
    if request.method == 'GET':
        facilities = conn.execute("SELECT * FROM facilities ORDER BY id ASC").fetchall()
        conn.close()
        return jsonify({"status": "success", "facilities": [dict(f) for f in facilities]})
    
    elif request.method == 'POST':
        data = request.json or {}
        name = data.get('name')
        description = data.get('description', '')
        icon = data.get('icon', 'star')
        category = data.get('category', 'Umum')
        image_url = data.get('image_url', '')

        if not name:
            conn.close()
            return jsonify({"status": "error", "message": "Nama fasilitas wajib diisi"}), 400

        fac_id = data.get('id')
        if fac_id:
            conn.execute("UPDATE facilities SET name=?, description=?, icon=?, category=?, image_url=? WHERE id=?",
                         (name, description, icon, category, image_url, fac_id))
        else:
            conn.execute("INSERT INTO facilities (name, description, icon, category, image_url) VALUES (?, ?, ?, ?, ?)",
                         (name, description, icon, category, image_url))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Fasilitas berhasil disimpan"})

    elif request.method == 'DELETE':
        fac_id = request.args.get('id')
        if fac_id:
            conn.execute("DELETE FROM facilities WHERE id=?", (fac_id,))
            conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Fasilitas dihapus"})

@app.route('/api/gallery', methods=['GET', 'POST', 'DELETE'])
def handle_gallery():
    conn = db.get_db_connection()
    if request.method == 'GET':
        items = conn.execute("SELECT * FROM gallery ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify({"status": "success", "gallery": [dict(item) for item in items]})

    elif request.method == 'POST':
        data = request.json or {}
        title = data.get('title', 'Foto Villa')
        image_url = data.get('image_url')
        category = data.get('category', 'Umum')
        item_id = data.get('id')

        if not image_url:
            conn.close()
            return jsonify({"status": "error", "message": "URL / Berkas Foto wajib diisi"}), 400

        if item_id:
            conn.execute("UPDATE gallery SET title=?, image_url=?, category=? WHERE id=?",
                         (title, image_url, category, item_id))
        else:
            conn.execute("INSERT INTO gallery (title, image_url, category) VALUES (?, ?, ?)",
                         (title, image_url, category))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Foto galeri berhasil disimpan"})

    elif request.method == 'DELETE':
        item_id = request.args.get('id')
        if item_id:
            conn.execute("DELETE FROM gallery WHERE id=?", (item_id,))
            conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Foto galeri dihapus"})

@app.route('/api/bookings', methods=['GET', 'POST', 'DELETE'])
def handle_bookings():
    conn = db.get_db_connection()
    if request.method == 'GET':
        bookings = conn.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
        result = []
        for b in bookings:
            b_dict = dict(b)
            payments = conn.execute("SELECT * FROM payments WHERE booking_id=? ORDER BY id ASC", (b['id'],)).fetchall()
            payments_list = [dict(p) for p in payments]
            total_paid = sum(p['amount'] for p in payments_list)
            remaining_balance = b_dict['total_price'] - total_paid
            
            if remaining_balance <= 0 and total_paid > 0:
                p_status = "LUNAS"
            elif total_paid > 0:
                p_status = "DP TERBAYAR"
            else:
                p_status = "BELUM BAYAR"

            b_dict['payments'] = payments_list
            b_dict['total_paid'] = total_paid
            b_dict['remaining_balance'] = max(0, remaining_balance)
            b_dict['payment_status'] = p_status
            result.append(b_dict)

        conn.close()
        return jsonify({"status": "success", "bookings": result})

    elif request.method == 'POST':
        data = request.json or {}
        guest_name = data.get('guest_name')
        guest_phone = data.get('guest_phone')
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        notes = data.get('notes', '')

        if not (guest_name and guest_phone and check_in and check_out):
            conn.close()
            return jsonify({"status": "error", "message": "Mohon lengkapi formulir pemesanan"}), 400

        start = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(check_out, "%Y-%m-%d").date()
        
        if end <= start:
            conn.close()
            return jsonify({"status": "error", "message": "Tanggal Check-out harus setelah Check-in"}), 400

        total_price = 0
        curr = start
        while curr < end:
            date_str = curr.strftime("%Y-%m-%d")
            row = conn.execute("SELECT status, price FROM calendar WHERE date=?", (date_str,)).fetchone()
            if row and row['status'] == 'booked':
                conn.close()
                return jsonify({"status": "error", "message": f"Maaf, tanggal {date_str} sudah terbooking!"}), 400
            
            p = row['price'] if row else (2200000 if curr.weekday() in (4,5,6) else 1500000)
            total_price += p
            curr += datetime.timedelta(days=1)

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (guest_name, guest_phone, check_in, check_out, total_price, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (guest_name, guest_phone, check_in, check_out, total_price, notes))
        conn.commit()
        booking_id = cursor.lastrowid
        conn.close()

        db.batch_update_dates(check_in, (end - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), status="booked", note=f"Booked: {guest_name}")

        return jsonify({
            "status": "success",
            "booking_id": booking_id,
            "total_price": total_price,
            "message": "Pemesanan berhasil dibuat!"
        })

    elif request.method == 'DELETE':
        booking_id = request.args.get('id')
        if booking_id:
            booking = conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
            if booking:
                start = datetime.datetime.strptime(booking['check_in'], "%Y-%m-%d").date()
                end = datetime.datetime.strptime(booking['check_out'], "%Y-%m-%d").date() - datetime.timedelta(days=1)
                db.batch_update_dates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), status="ready", note="")
                conn.execute("DELETE FROM payments WHERE booking_id=?", (booking_id,))
                conn.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
                conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Booking dibatalkan"})

@app.route('/api/payments', methods=['GET', 'POST', 'DELETE'])
def handle_payments():
    conn = db.get_db_connection()
    if request.method == 'GET':
        booking_id = request.args.get('booking_id')
        if not booking_id:
            conn.close()
            return jsonify({"status": "error", "message": "booking_id wajib"}), 400
        
        payments = conn.execute("SELECT * FROM payments WHERE booking_id=? ORDER BY id ASC", (booking_id,)).fetchall()
        booking = conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        conn.close()

        p_list = [dict(p) for p in payments]
        total_paid = sum(p['amount'] for p in p_list)
        total_price = booking['total_price'] if booking else 0
        remaining_balance = total_price - total_paid

        return jsonify({
            "status": "success",
            "payments": p_list,
            "total_price": total_price,
            "total_paid": total_paid,
            "remaining_balance": max(0, remaining_balance)
        })

    elif request.method == 'POST':
        data = request.json or {}
        booking_id = data.get('booking_id')
        payment_name = data.get('payment_name', 'DP / Pembayaran')
        amount = int(data.get('amount', 0))
        payment_date = data.get('payment_date') or datetime.date.today().strftime("%Y-%m-%d")
        notes = data.get('notes', '')

        if not booking_id or amount <= 0:
            conn.close()
            return jsonify({"status": "error", "message": "Mohon isi jumlah pembayaran dengan benar"}), 400

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (booking_id, payment_name, amount, payment_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (booking_id, payment_name, amount, payment_date, notes))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Pembayaran berhasil dicatat!"})

    elif request.method == 'DELETE':
        payment_id = request.args.get('id')
        if payment_id:
            conn.execute("DELETE FROM payments WHERE id=?", (payment_id,))
            conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Catatan pembayaran dihapus"})

@app.route('/api/expenses', methods=['GET', 'POST', 'DELETE'])
def handle_expenses():
    if request.method == 'GET':
        month = request.args.get('month', 'all')
        expenses = db.get_expenses(month)
        total_expenses = sum(e['amount'] for e in expenses)
        return jsonify({
            "status": "success",
            "expenses": expenses,
            "total_expenses": total_expenses
        })

    elif request.method == 'POST':
        data = request.json or {}
        title = data.get('title')
        category = data.get('category', 'Operasional')
        amount = int(data.get('amount', 0))
        expense_date = data.get('expense_date') or datetime.date.today().strftime("%Y-%m-%d")
        notes = data.get('notes', '')

        if not title or amount <= 0:
            return jsonify({"status": "error", "message": "Mohon isi nama pengeluaran & jumlah biaya dengan benar"}), 400

        expense_id = db.add_expense(title, category, amount, expense_date, notes)
        return jsonify({
            "status": "success",
            "expense_id": expense_id,
            "message": "Pengeluaran berhasil dicatat!"
        })

    elif request.method == 'DELETE':
        expense_id = request.args.get('id')
        if expense_id:
            db.delete_expense(expense_id)
        return jsonify({"status": "success", "message": "Pengeluaran dihapus"})

@app.route('/api/reports/export')
def export_csv_report():
    month = request.args.get('month', 'all')
    conn = db.get_db_connection()
    bookings = conn.execute("SELECT * FROM bookings ORDER BY check_in DESC").fetchall()
    expenses = db.get_expenses(month)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header & Income Section
    writer.writerow([f"LAPORAN KEUANGAN VILLA - PERIODE: {month}"])
    writer.writerow([])
    writer.writerow(["--- 1. RINCIAN PEMASUKAN RESERVASI ---"])
    writer.writerow([
        "No. Invoice", "Nama Tamu", "No. WhatsApp", "Tanggal Check-In", 
        "Tanggal Check-Out", "Total Biaya (Rp)", "Kas Masuk / DP (Rp)", 
        "Sisa Tagihan (Rp)", "Status Pembayaran", "Catatan"
    ])

    total_omset = 0
    total_kas_masuk = 0
    total_sisa = 0

    for b in bookings:
        b_dict = dict(b)
        if month != 'all' and not b_dict['check_in'].startswith(month):
            continue

        payments = conn.execute("SELECT amount FROM payments WHERE booking_id=?", (b_dict['id'],)).fetchall()
        total_paid = sum(p['amount'] for p in payments)
        remaining = max(0, b_dict['total_price'] - total_paid)
        
        if remaining <= 0 and total_paid > 0:
            p_status = "LUNAS"
        elif total_paid > 0:
            p_status = "DP TERBAYAR"
        else:
            p_status = "BELUM BAYAR"

        inv_no = f"INV/VB/{b_dict['check_in'].replace('-', '')[:6]}/{str(b_dict['id']).zfill(3)}"
        writer.writerow([
            inv_no, b_dict['guest_name'], b_dict['guest_phone'], 
            b_dict['check_in'], b_dict['check_out'], b_dict['total_price'],
            total_paid, remaining, p_status, b_dict['notes'] or ''
        ])

        total_omset += b_dict['total_price']
        total_kas_masuk += total_paid
        total_sisa += remaining

    conn.close()

    writer.writerow([])
    writer.writerow(["TOTAL OMSET SEWA", total_omset])
    writer.writerow(["TOTAL KAS MASUK", total_kas_masuk])
    writer.writerow(["TOTAL SISA PIUTANG", total_sisa])
    writer.writerow([])

    # Expenses Section
    writer.writerow(["--- 2. RINCIAN PENGELUARAN VILLA ---"])
    writer.writerow(["ID", "Pengeluaran", "Kategori", "Jumlah Biaya (Rp)", "Tanggal Pengeluaran", "Catatan"])
    
    total_pengeluaran = 0
    for e in expenses:
        writer.writerow([e['id'], e['title'], e['category'], e['amount'], e['expense_date'], e['notes'] or ''])
        total_pengeluaran += e['amount']

    writer.writerow([])
    writer.writerow(["TOTAL PENGELUARAN VILLA", total_pengeluaran])
    writer.writerow([])

    # Summary Section
    net_profit = total_kas_masuk - total_pengeluaran
    writer.writerow(["--- 3. RINGKASAN LABA BERSIH (NET PROFIT) ---"])
    writer.writerow(["TOTAL KAS MASUK (PEMASUKAN)", total_kas_masuk])
    writer.writerow(["TOTAL BEBAN PENGELUARAN", total_pengeluaran])
    writer.writerow(["KEUNTUNGAN BERSIH (NET PROFIT)", net_profit])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=Laporan_Keuangan_Lengkap_Villa_{month}.csv"
    return response

if __name__ == '__main__':
    print("Starting Villa Babeh Server at http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)

