from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ================= DATABASE =================

def connect():
    return sqlite3.connect("hotel.db")

def create_tables():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms(
        room_no INTEGER PRIMARY KEY,
        room_type TEXT,
        price INTEGER,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        room_no INTEGER,
        checkin_date TEXT
    )
    """)

    cursor.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES('admin','admin123','admin')")
    cursor.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES('staff','staff123','staff')")

    conn.commit()
    conn.close()

create_tables()

# ================= LOGIN =================

@app.route('/')
def login_page():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['role'] = user[0]
        return redirect('/dashboard')

    flash("Invalid Credentials", "danger")
    return redirect('/')

# ================= DASHBOARD =================

@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect('/')

    search = request.args.get("search")

    conn = connect()
    cursor = conn.cursor()

    if search:
        cursor.execute("SELECT * FROM rooms WHERE room_type LIKE ?", ('%'+search+'%',))
    else:
        cursor.execute("SELECT * FROM rooms")

    rooms = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM rooms")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rooms WHERE status='Available'")
    available = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rooms WHERE status='Booked'")
    booked = cursor.fetchone()[0]

    conn.close()

    return render_template("dashboard.html",
                           rooms=rooms,
                           total=total,
                           available=available,
                           booked=booked)

# ================= ADD ROOM =================

@app.route('/add_room', methods=['GET','POST'])
def add_room():
    if session.get('role') != 'admin':
        return redirect('/dashboard')

    if request.method == 'POST':
        room_no = request.form['room_no']
        room_type = request.form['room_type']
        price = request.form['price']

        conn = connect()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO rooms VALUES(?,?,?,?)",
                           (room_no, room_type, price, "Available"))
            conn.commit()
            flash("Room Added Successfully", "success")
        except:
            flash("Room Already Exists", "danger")

        conn.close()
        return redirect('/dashboard')

    return render_template("add_room.html")

# ================= BOOK ROOM =================

@app.route('/book_room', methods=['GET','POST'])
def book_room():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        room_no = request.form['room_no']

        if len(phone) < 10:
            flash("Phone number must be at least 10 digits", "danger")
            return redirect('/book_room')

        conn = connect()
        cursor = conn.cursor()

        cursor.execute("SELECT price,status FROM rooms WHERE room_no=?", (room_no,))
        room = cursor.fetchone()

        if room and room[1] == "Available":
            cursor.execute("INSERT INTO customers(name,phone,room_no,checkin_date) VALUES(?,?,?,date('now'))",
                           (name, phone, room_no))
            cursor.execute("UPDATE rooms SET status='Booked' WHERE room_no=?", (room_no,))
            conn.commit()
            flash("Room Booked Successfully", "success")
        else:
            flash("Room Not Available", "danger")

        conn.close()
        return redirect('/dashboard')

    return render_template("book_room.html")

# ================= CUSTOMERS =================

@app.route('/customers')
def customers():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT customers.name, customers.phone, customers.room_no, rooms.price
    FROM customers
    JOIN rooms ON customers.room_no = rooms.room_no
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template("customers.html", data=data)

# ================= BILL PDF =================

@app.route('/bill/<int:room_no>')
def bill(room_no):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT customers.name, customers.phone, rooms.price
    FROM customers
    JOIN rooms ON customers.room_no = rooms.room_no
    WHERE customers.room_no=?
    """, (room_no,))
    data = cursor.fetchone()
    conn.close()

    filename = f"bill_room_{room_no}.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Hotel Bill", styles['Heading1']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Customer: {data[0]}", styles['Normal']))
    elements.append(Paragraph(f"Phone: {data[1]}", styles['Normal']))
    elements.append(Paragraph(f"Total Amount: ₹{data[2]}", styles['Normal']))

    doc.build(elements)

    return send_file(filename, as_attachment=True)

# ================= DARK MODE =================

@app.route('/toggle_theme')
def toggle_theme():
    if session.get("theme") == "dark":
        session["theme"] = "light"
    else:
        session["theme"] = "dark"
    return redirect('/dashboard')

# ================= LOGOUT =================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run()