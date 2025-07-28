from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, qrcode
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key'

BOOKING_FILE = 'data/bookings.json'
USER_FILE = 'data/users.json'

os.makedirs('data', exist_ok=True)
os.makedirs('static/qr_codes', exist_ok=True)

# Metro Stations
STATIONS = [
    "Dakshineswar", "Baranagar", "Belgachia", "Shyambazar", "Girish Park", "MG Road", "Central",
    "Chandni Chowk", "Esplanade", "Park Street", "Maidan", "Rabindra Sadan", "Netaji Bhavan",
    "Jatin Das Park", "Kalighat", "Rabindra Sarobar", "Jadavpur", "Netaji", "Kavi Nazrul",
    "Gitanjali", "Masterda Surya Sen", "Shahid Khudiram", "Kavi Subhash"
]

# Load/Save Functions
def calculate_fare(from_station, to_station):
    try:
        i1 = STATIONS.index(from_station)
        i2 = STATIONS.index(to_station)
        distance = abs(i2 - i1)
        if distance <= 4:
            return "Rs. 5"
        elif distance <= 10:
            return "Rs. 10"
        elif distance <= 16:
            return "Rs. 20"
        else:
            return "Rs. 30"
    except ValueError:
        return "Rs. 30"

def load_bookings():
    if os.path.exists(BOOKING_FILE):
        with open(BOOKING_FILE, 'r') as f:
            return json.load(f)
    return []

def save_bookings(bookings):
    with open(BOOKING_FILE, 'w') as f:
        json.dump(bookings, f, indent=2)

# USER AUTHENTICATION
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r') as f:
                users = json.load(f)
        else:
            users = {}

        if username in users:
            return render_template('register.html', error="Username already exists.")

        users[username] = password
        with open(USER_FILE, 'w') as f:
            json.dump(users, f, indent=2)

        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r') as f:
                users = json.load(f)
        else:
            users = {}

        if username in users and users[username] == password:
            session['user'] = username
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# MAIN HOME
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template('index.html', user=session['user'])

# BOOKING
@app.route('/book-form')
def book_form():
    if 'user' not in session:
        return redirect('/login')
    
    if 'last_ticket_id' in session:
        ticket_id = session.pop('last_ticket_id')
        return redirect(f'/ticket/{ticket_id}')

    return render_template('book.html', user=session['user'], stations=STATIONS)

@app.route('/payment', methods=['POST'])
def payment_page():
    if 'user' not in session:
        return redirect('/login')
    from_station = request.form.get('from')
    to_station = request.form.get('to')
    fare = calculate_fare(from_station, to_station)
    return render_template('payment.html', user=session['user'], from_station=from_station, to_station=to_station, fare=fare)

@app.route('/payment-success', methods=['POST'])
def payment_success():
    if 'user' not in session:
        return redirect('/login')

    data = {
        'username': session['user'],
        'from': request.form.get('from_station'),
        'to': request.form.get('to_station'),
        'payment_method': request.form.get('payment_method')
    }

    bookings = load_bookings()
    ticket_id = str(int(datetime.now().timestamp()))
    data['ticket_id'] = ticket_id
    data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['fare'] = calculate_fare(data['from'], data['to'])
    data['status'] = 'confirmed'

    qr = qrcode.QRCode(version=1, box_size=3, border=2)
    qr_data = (
        f"Kolkata Metro Ticket\n"
        f"Ticket ID: {ticket_id}\n"
        f"Passenger: {data['username']}\n"
        f"From: {data['from']}\n"
        f"To: {data['to']}\n"
        f"Fare: {data['fare']}\n"
        f"Paid via: {data['payment_method']}\n"
        f"Date: {data['date']}"
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_path = f'static/qr_codes/{ticket_id}.png'
    qr_img.save(qr_path)
    data['qr_path'] = '/' + qr_path

    bookings.append(data)
    save_bookings(bookings)

    session['last_ticket_id'] = ticket_id
    return redirect(f'/ticket/{ticket_id}')

# VIEW TICKET
@app.route('/ticket/<ticket_id>')
def view_ticket(ticket_id):
    bookings = load_bookings()
    for b in bookings:
        if b.get('ticket_id') == ticket_id:
            return render_template('ticket.html', ticket=b)
    return 'Ticket not found', 404

# MY BOOKINGS
@app.route('/my-bookings')
def my_bookings():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
    bookings = load_bookings()
    user_tickets = [b for b in bookings if b.get('username') == username]
    return render_template('my_bookings.html', bookings=user_tickets, user=username)

# CANCEL TICKET
@app.route('/cancel-ticket')
def cancel_ticket_page():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
    bookings = load_bookings()
    user_tickets = [b for b in bookings if b.get('username') == username]
    return render_template('cancel_ticket.html', bookings=user_tickets, user=username)

@app.route('/cancel-ticket/<ticket_id>', methods=['POST'])
def cancel_ticket_action(ticket_id):
    bookings = load_bookings()
    updated = [b for b in bookings if b.get('ticket_id') != ticket_id]
    save_bookings(updated)
    return redirect('/cancel-ticket')

# STATIC PAGES
@app.route('/schedule')
def metro_schedule():
    return render_template('schedule.html')

@app.route('/track')
def track_metro():
    return render_template('track.html')

@app.route('/route-map')
def route_map():
    return render_template('route_map.html')

@app.route('/support')
def customer_support():
    return render_template('support.html')

@app.route('/rules')
def metro_rules():
    return render_template('rules.html')

if __name__ == '__main__':
    app.run(debug=True)
