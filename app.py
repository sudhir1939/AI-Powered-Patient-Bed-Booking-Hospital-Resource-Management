# app.py 
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_file, make_response, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import json
import razorpay
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import requests
from flask import jsonify
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['RAZORPAY_KEY_ID'] = 'rzp_test_RPURGWwDtViv9P'
app.config['RAZORPAY_KEY_SECRET'] = 'gHB7AScqU12PUikgM7Fibsu3' 
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SENDER_EMAIL'] = 'harshvardhandhane13@gmail.com'
app.config['SENDER_PASSWORD'] = 'ipde veha zmzs hhlb'

app.config['OPENROUTER_API_KEY'] = "OPENROUTER_API_KEY"
app.config['OPENROUTER_URL'] = "https://openrouter.ai/api/v1/chat/completions"
app.config['MODEL'] = "openai/gpt-oss-20b:free"
db = SQLAlchemy(app)
razorpay_client = razorpay.Client(auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET']))
def send_email(to_email, subject, body, pdf_buffer=None):
    msg = MIMEMultipart()
    msg['From'] = app.config['SENDER_EMAIL']
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    if pdf_buffer:
        pdf_buffer.seek(0)
        attach = MIMEApplication(pdf_buffer.getvalue(), _subtype='pdf')
        attach.add_header('Content-Disposition', 'attachment', filename='bill.pdf')
        msg.attach(attach)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(app.config['SENDER_EMAIL'], app.config['SENDER_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['SENDER_EMAIL'], to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False
def generate_booking_bill_pdf(booking, bed, room):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Hospital Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {booking.patient_name}")
    y -= 20
    p.drawString(100, y, f"Age: {booking.age}")
    y -= 20
    p.drawString(100, y, f"Contact: {booking.contact_number}")
    y -= 20
    p.drawString(100, y, f"Check-in Date: {booking.check_in_date}")
    y -= 20
    p.drawString(100, y, f"Estimated Stay: {booking.estimated_stay} days")
    y -= 20
    p.drawString(100, y, f"Room: {room.name}")
    y -= 20
    p.drawString(100, y, f"Bed: {bed.bed_number}")
    y -= 20
    p.drawString(100, y, f"Price per day: ₹{room.price_per_bed}")
    y -= 20
    p.drawString(100, y, f"Total Amount: ₹{room.price_per_bed * booking.estimated_stay}")
    p.save()
    return buffer
def generate_appointment_bill_pdf(appointment, time_slot):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Appointment Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {appointment.patient.name}")
    y -= 20
    p.drawString(100, y, f"Doctor Name: {appointment.doctor.name}")
    y -= 20
    p.drawString(100, y, f"Appointment Date: {appointment.appointment_date}")
    y -= 20
    p.drawString(100, y, f"Time Slot: {time_slot.start_time} - {time_slot.end_time}")
    y -= 20
    p.drawString(100, y, f"Amount: ₹{time_slot.price}")
    p.save()
    return buffer
def generate_ambulance_bill_pdf(booking, vehicle):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Ambulance Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {booking.patient.name}")
    y -= 20
    p.drawString(100, y, f"Vehicle: {vehicle.name}")
    y -= 20
    p.drawString(100, y, f"Numberplate: {vehicle.numberplate}")
    y -= 20
    p.drawString(100, y, f"Use Type: {booking.use_type}")
    if booking.location_link:
        y -= 20
        p.drawString(100, y, f"Location Link: {booking.location_link}")
    y -= 20
    p.drawString(100, y, f"Amount: ₹{booking.amount}")
    p.save()
    return buffer
def generate_nurse_bill_pdf(booking, nurse):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Nurse Booking Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {booking.patient.name}")
    y -= 20
    p.drawString(100, y, f"Nurse Name: {nurse.name}")
    y -= 20
    p.drawString(100, y, f"Duration Type: {booking.duration_type}")
    y -= 20
    p.drawString(100, y, f"Location: {booking.location}")
    y -= 20
    p.drawString(100, y, f"Amount: ₹{booking.amount}")
    p.save()
    return buffer
def generate_canteen_bill_pdf(order):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Canteen Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {order.patient.name}")
    y -= 20
    p.drawString(100, y, f"Order ID: {order.id}")
    y -= 20
    p.drawString(100, y, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    if order.room_id:
        room = Room.query.get(order.room_id)
        y -= 20
        p.drawString(100, y, f"Delivery Room: {room.name}")
    if order.bed_id:
        bed = Bed.query.get(order.bed_id)
        y -= 20
        p.drawString(100, y, f"Delivery Bed: {bed.bed_number}")
    y -= 20
    total = 0
    for item in order.items:
        p.drawString(100, y, f"{item.item.name} x {item.quantity}: ₹{item.item.price * item.quantity}")
        y -= 20
        total += item.item.price * item.quantity
    p.drawString(100, y, f"Total Amount: ₹{total}")
    p.save()
    return buffer
   
    # Add this function after the generate_canteen_bill_pdf function
def call_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {app.config['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": url_for('index', _external=True), # Optional, for OpenRouter
        "X-Title": "Hospital AI Bot" # Optional
    }
    data = {
        "model": app.config['MODEL'],
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.7
    }
    try:
        response = requests.post(app.config['OPENROUTER_URL'], headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"OpenRouter error: {response.text}")
            return "Sorry, I'm having trouble responding right now. Please try again."
    except Exception as e:
        print(f"OpenRouter call failed: {e}")
        return "Sorry, I'm having trouble connecting. Please try again."
   
# Models (unchanged from provided)
class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info= db.Column(db.Text, nullable=True)
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True) # Professional Information
    qualifications = db.Column(db.Text, nullable=True)
    specializations = db.Column(db.Text, nullable=True)
    practice_years = db.Column(db.Integer, nullable=True)
    additional_links = db.Column(db.Text, nullable=True)
    practice_location = db.Column(db.String(255), nullable=True)
    time_slots = db.relationship('TimeSlot', backref='doctor', lazy=True, cascade="all, delete-orphan")
    medical_records = db.relationship('MedicalRecord', backref='doctor', lazy=True, cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', backref='doctor', lazy=True, cascade="all, delete-orphan")
    doctor_reviews = db.relationship('DoctorReview', backref='doctor', lazy=True, cascade="all, delete-orphan")
class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    start_time = db.Column(db.String(5), nullable=False) # e.g., '09:00'
    end_time = db.Column(db.String(5), nullable=False) # e.g., '10:00'
    price = db.Column(db.Float, nullable=False)
    appointments = db.relationship('Appointment', backref='time_slot', lazy=True)
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    medical_condition = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Ambulance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='available') # available, on duty, under maintenance
    vehicles = db.relationship('AmbulanceVehicle', backref='ambulance', lazy=True, cascade="all, delete-orphan")
    bookings = db.relationship('AmbulanceBooking', backref='ambulance', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('AmbulanceReview', backref='ambulance', lazy=True, cascade="all, delete-orphan")
class AmbulanceVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    numberplate = db.Column(db.String(50), nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    medical_support = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    bookings = db.relationship('AmbulanceBooking', backref='vehicle', lazy=True)
class AmbulanceBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('ambulance_vehicle.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='unpaid')
    use_type = db.Column(db.String(20), nullable=False) # emergency or normal
    location_link = db.Column(db.Text, nullable=True) # patient's for emergency, ambulance's for normal
    live_location_link = db.Column(db.Text, nullable=True) # ambulance's live link for normal
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class AmbulanceReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Nurse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)
    availability_locations = db.Column(db.String(50), nullable=True) # e.g., 'home,hospital'
    status = db.Column(db.String(20), default='available') # available, booked
    bookings = db.relationship('NurseBooking', backref='nurse', lazy=True, cascade="all, delete-orphan")
    nurse_reviews = db.relationship('NurseReview', backref='nurse', lazy=True, cascade="all, delete-orphan")
    rates = db.relationship('NurseRate', backref='nurse', lazy=True, cascade="all, delete-orphan")
class NurseRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurse.id'), nullable=False)
    rate_type = db.Column(db.String(50), nullable=False) # 'per_hour_home', 'per_hour_hospital', 'per_day_home', 'per_day_hospital'
    price = db.Column(db.Float, nullable=False)
class NurseBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurse.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, accepted, paid, rejected
    duration_type = db.Column(db.String(20), nullable=False) # 'per_hour', 'per_day'
    location = db.Column(db.String(20), nullable=False) # 'home', 'hospital'
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class NurseReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurse.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Canteen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)
    categories = db.relationship('CanteenCategory', backref='canteen', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('CanteenOrder', backref='canteen', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('CanteenReview', backref='canteen', lazy=True, cascade="all, delete-orphan")
class CanteenCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    canteen_id = db.Column(db.Integer, db.ForeignKey('canteen.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    items = db.relationship('CanteenItem', backref='category', lazy=True, cascade="all, delete-orphan")
class CanteenItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('canteen_category.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
class CanteenOrder(db.Model):
    __tablename__ = 'canteen_order'
    id = db.Column(db.Integer, primary_key=True)
    canteen_id = db.Column(db.Integer, db.ForeignKey('canteen.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True) # New field
    bed_id = db.Column(db.Integer, db.ForeignKey('bed.id'), nullable=True) # New field
    status = db.Column(db.String(20), default='pending') # pending, accepted, paid, preparing, out_for_delivery, delivered
    payment_status = db.Column(db.String(20), default='unpaid')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('CanteenOrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
class CanteenOrderItem(db.Model):
    __tablename__ = 'canteen_order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('canteen_order.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('canteen_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    item = db.relationship('CanteenItem')
class CanteenReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    canteen_id = db.Column(db.Integer, db.ForeignKey('canteen.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)
    appointments = db.relationship('Appointment', backref='patient', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='patient', lazy=True, cascade="all, delete-orphan")
    doctor_reviews = db.relationship('DoctorReview', backref='patient', lazy=True, cascade="all, delete-orphan")
    ambulance_bookings = db.relationship('AmbulanceBooking', backref='patient', lazy=True, cascade="all, delete-orphan")
    ambulance_reviews = db.relationship('AmbulanceReview', backref='patient', lazy=True, cascade="all, delete-orphan")
    nurse_bookings = db.relationship('NurseBooking', backref='patient', lazy=True, cascade="all, delete-orphan")
    nurse_reviews = db.relationship('NurseReview', backref='patient', lazy=True, cascade="all, delete-orphan")
    canteen_orders = db.relationship('CanteenOrder', backref='patient', lazy=True, cascade="all, delete-orphan")
    canteen_reviews = db.relationship('CanteenReview', backref='patient', lazy=True, cascade="all, delete-orphan")
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    num_beds = db.Column(db.Integer, nullable=False)
    price_per_bed = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    beds = db.relationship('Bed', backref='room', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='room', lazy=True, cascade="all, delete-orphan")
class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    bed_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='available')
    position = db.Column(db.String(50), nullable=True)
    bookings = db.relationship('Booking', backref='bed', lazy=True, cascade="all, delete-orphan")
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bed_id = db.Column(db.Integer, db.ForeignKey('bed.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    patient_name = db.Column(db.String(100))
    contact_number = db.Column(db.String(20))
    age = db.Column(db.Integer)
    medical_condition = db.Column(db.Text)
    estimated_stay = db.Column(db.Integer)
    check_in_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class DoctorReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# Create database
with app.app_context():
    db.create_all()
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# Routes (all existing + updated for canteen)
@app.route('/')
def index():
    return render_template('index.html')
# Hospital Admin Routes (unchanged)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hospital = Hospital.query.filter_by(username=username).first()
        if hospital and check_password_hash(hospital.password, password):
            session['admin_user_id'] = hospital.id
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password')
    return render_template('admin_login.html')
@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_register.html')
        if Hospital.query.filter_by(username=username).first() or Hospital.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_register.html')
        hashed_password = generate_password_hash(password)
        new_hospital = Hospital(name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_hospital)
        db.session.commit()
        return redirect(url_for('admin_login'))
    return render_template('admin_register.html')
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    hospital = Hospital.query.get(session['admin_user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        hospital.name = request.form['name']
        hospital.mobile = request.form['mobile']
        hospital.email = request.form['email']
        hospital.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    return render_template('admin_dashboard.html', hospital=hospital)
@app.route('/admin/doctors', methods=['GET', 'POST'])
def admin_doctors():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    hospital_id = session['admin_user_id']
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_doctors.html', doctors=doctors)
        if Doctor.query.filter_by(username=username).first() or Doctor.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_doctors.html', doctors=doctors)
        hashed_password = generate_password_hash(password)
        new_doctor = Doctor(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added')
        return redirect(url_for('admin_doctors'))
    return render_template('admin_doctors.html', doctors=doctors)
@app.route('/admin/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])
def admin_edit_doctor(doctor_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    if doctor.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_doctors'))
    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.mobile = request.form['mobile']
        doctor.email = request.form['email']
        db.session.commit()
        flash('Doctor updated')
        return redirect(url_for('admin_doctors'))
    return render_template('admin_edit_doctor.html', doctor=doctor)
@app.route('/admin/doctors/remove/<int:doctor_id>')
def admin_remove_doctor(doctor_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    if doctor.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_doctors'))
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor removed')
    return redirect(url_for('admin_doctors'))
# Ambulance Admin Routes (unchanged)
@app.route('/admin/ambulances', methods=['GET', 'POST'])
def admin_ambulances():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    hospital_id = session['admin_user_id']
    ambulances = Ambulance.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_ambulances.html', ambulances=ambulances)
        if Ambulance.query.filter_by(username=username).first() or Ambulance.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_ambulances.html', ambulances=ambulances)
        hashed_password = generate_password_hash(password)
        new_ambulance = Ambulance(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_ambulance)
        db.session.commit()
        flash('Ambulance added')
        return redirect(url_for('admin_ambulances'))
    return render_template('admin_ambulances.html', ambulances=ambulances)
@app.route('/admin/ambulances/edit/<int:ambulance_id>', methods=['GET', 'POST'])
def admin_edit_ambulance(ambulance_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    if ambulance.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_ambulances'))
    if request.method == 'POST':
        ambulance.name = request.form['name']
        ambulance.mobile = request.form['mobile']
        ambulance.email = request.form['email']
        db.session.commit()
        flash('Ambulance updated')
        return redirect(url_for('admin_ambulances'))
    return render_template('admin_edit_ambulance.html', ambulance=ambulance)
@app.route('/admin/ambulances/remove/<int:ambulance_id>')
def admin_remove_ambulance(ambulance_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    if ambulance.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_ambulances'))
    db.session.delete(ambulance)
    db.session.commit()
    flash('Ambulance removed')
    return redirect(url_for('admin_ambulances'))
# Nurse (unchanged)
@app.route('/admin/nurses', methods=['GET', 'POST'])
def admin_nurses():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    hospital_id = session['admin_user_id']
    nurses = Nurse.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_nurses.html', nurses=nurses)
        if Nurse.query.filter_by(username=username).first() or Nurse.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_nurses.html', nurses=nurses)
        hashed_password = generate_password_hash(password)
        new_nurse = Nurse(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_nurse)
        db.session.commit()
        flash('Nurse added')
        return redirect(url_for('admin_nurses'))
    return render_template('admin_nurses.html', nurses=nurses)
@app.route('/admin/nurses/edit/<int:nurse_id>', methods=['GET', 'POST'])
def admin_edit_nurse(nurse_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    if nurse.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_nurses'))
    if request.method == 'POST':
        nurse.name = request.form['name']
        nurse.mobile = request.form['mobile']
        nurse.email = request.form['email']
        db.session.commit()
        flash('Nurse updated')
        return redirect(url_for('admin_nurses'))
    return render_template('admin_edit_nurse.html', nurse=nurse)
@app.route('/admin/nurses/remove/<int:nurse_id>')
def admin_remove_nurse(nurse_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    if nurse.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_nurses'))
    db.session.delete(nurse)
    db.session.commit()
    flash('Nurse removed')
    return redirect(url_for('admin_nurses'))
# Canteen (updated)
@app.route('/admin/canteens', methods=['GET', 'POST'])
def admin_canteens():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    hospital_id = session['admin_user_id']
    canteens = Canteen.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_canteens.html', canteens=canteens)
        if Canteen.query.filter_by(username=username).first() or Canteen.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_canteens.html', canteens=canteens)
        hashed_password = generate_password_hash(password)
        new_canteen = Canteen(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_canteen)
        db.session.commit()
        flash('Canteen added')
        return redirect(url_for('admin_canteens'))
    return render_template('admin_canteens.html', canteens=canteens)
@app.route('/admin/canteens/edit/<int:canteen_id>', methods=['GET', 'POST'])
def admin_edit_canteen(canteen_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    canteen = Canteen.query.get_or_404(canteen_id)
    if canteen.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_canteens'))
    if request.method == 'POST':
        canteen.name = request.form['name']
        canteen.mobile = request.form['mobile']
        canteen.email = request.form['email']
        db.session.commit()
        flash('Canteen updated')
        return redirect(url_for('admin_canteens'))
    return render_template('admin_edit_canteen.html', canteen=canteen)
@app.route('/admin/canteens/remove/<int:canteen_id>')
def admin_remove_canteen(canteen_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    canteen = Canteen.query.get_or_404(canteen_id)
    if canteen.hospital_id != session['admin_user_id']:
        return redirect(url_for('admin_canteens'))
    db.session.delete(canteen)
    db.session.commit()
    flash('Canteen removed')
    return redirect(url_for('admin_canteens'))
# Admin Rooms Management (unchanged)
@app.route('/admin/rooms', methods=['GET', 'POST'])
def admin_rooms():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    hospital_id = session['admin_user_id']
    rooms = Room.query.filter_by(hospital_id=hospital_id).all()
    bookings = Booking.query.join(Bed).join(Room).filter(Room.hospital_id == hospital_id).all()
    active_bookings = [b for b in bookings if b.status == 'pending']
    history_bookings = [b for b in bookings if b.status in ['accepted', 'rejected', 'cancelled']]
    confirmed_bookings = [b for b in bookings if b.status == 'paid']
    if request.method == 'POST' and 'create_room' in request.form:
        name = request.form['name']
        num_beds = int(request.form['num_beds'])
        price_per_bed = float(request.form['price_per_bed'])
        description = request.form.get('description')
        layout_json = request.form['layout']
        layout = json.loads(layout_json)
        new_room = Room(hospital_id=hospital_id, name=name, num_beds=num_beds, price_per_bed=price_per_bed, description=description)
        db.session.add(new_room)
        db.session.commit()
        for item in layout:
            bed = Bed(room_id=new_room.id, bed_number=item['number'], position=f"{item['left']},{item['top']}")
            db.session.add(bed)
        db.session.commit()
        flash('Room created')
        return redirect(url_for('admin_rooms'))
    return render_template('admin_rooms.html', rooms=rooms, active_bookings=active_bookings, history_bookings=history_bookings, confirmed_bookings=confirmed_bookings)
@app.route('/admin/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
def admin_edit_room(room_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    room = Room.query.get_or_404(room_id)
    if room.hospital_id != session['admin_user_id']:
        abort(403)
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    if request.method == 'POST':
        room.name = request.form['name']
        room.price_per_bed = float(request.form['price_per_bed'])
        room.description = request.form.get('description')
        layout_json = request.form['layout']
        layout = json.loads(layout_json)
        beds = Bed.query.filter_by(room_id=room_id).order_by(Bed.bed_number).all()
        for i, item in enumerate(layout):
            beds[i].position = f"{item['left']},{item['top']}"
        db.session.commit()
        flash('Room updated')
        return redirect(url_for('admin_rooms'))
    beds = Bed.query.filter_by(room_id=room_id).order_by(Bed.bed_number).all()
    initial_layout = []
    for bed in beds:
        left, top = bed.position.split(',') if bed.position else ('0px', '0px')
        initial_layout.append({'id': bed.id, 'number': bed.bed_number, 'status': bed.status, 'left': left, 'top': top})
    return render_template('admin_edit_room.html', room=room, initial_layout=json.dumps(initial_layout), reviews=reviews)
@app.route('/admin/rooms/delete/<int:room_id>')
def admin_delete_room(room_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    room = Room.query.get_or_404(room_id)
    if room.hospital_id != session['admin_user_id']:
        abort(403)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted')
    return redirect(url_for('admin_rooms'))
@app.route('/admin/accept_booking/<int:booking_id>')
def admin_accept_booking(booking_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    booking = Booking.query.get_or_404(booking_id)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    if room.hospital_id != session['admin_user_id']:
        abort(403)
    booking.status = 'accepted'
    db.session.commit()
    flash('Booking accepted')
    # Send email to patient
    patient = Patient.query.get(booking.patient_id)
    if patient and patient.email:
        subject = "Bed Booking Request Accepted"
        body = f"Dear {patient.name},\n\nYour bed booking request has been accepted. Please pay the bill to confirm.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body)
    return redirect(url_for('admin_rooms'))
@app.route('/admin/reject_booking/<int:booking_id>')
def admin_reject_booking(booking_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    booking = Booking.query.get_or_404(booking_id)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    if room.hospital_id != session['admin_user_id']:
        abort(403)
    booking.status = 'rejected'
    db.session.commit()
    flash('Booking rejected')
    # Send email to patient
    patient = Patient.query.get(booking.patient_id)
    if patient and patient.email:
        subject = "Bed Booking Request Rejected"
        body = f"Dear {patient.name},\n\nYour bed booking request has been rejected.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body)
    return redirect(url_for('admin_rooms'))
@app.route('/admin/room/<int:room_id>/unbook_bed/<int:bed_id>')
def admin_unbook_bed(room_id, bed_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    bed = Bed.query.get_or_404(bed_id)
    if bed.room_id != room_id:
        abort(404)
    room = Room.query.get(room_id)
    if room.hospital_id != session['admin_user_id']:
        abort(403)
    if bed.status == 'booked':
        booking = Booking.query.filter_by(bed_id=bed_id, status='paid').first()
        if booking:
            booking.status = 'cancelled'
            # Send email to patient for cancellation
            patient = Patient.query.get(booking.patient_id)
            if patient and patient.email:
                subject = "Bed Booking Cancelled"
                body = f"Dear {patient.name},\n\nYour bed booking has been cancelled by admin.\n\nBest regards,\nHospital Team"
                send_email(patient.email, subject, body)
        bed.status = 'available'
        db.session.commit()
        flash('Bed unbooked')
    return redirect(url_for('admin_edit_room', room_id=room_id))
@app.route('/admin/delete_review/<int:review_id>')
def admin_delete_review(review_id):
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    review = Review.query.get_or_404(review_id)
    room = review.room
    if room.hospital_id != session['admin_user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('admin_edit_room', room_id=room.id))
# Doctor Routes (unchanged)
@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        doctor = Doctor.query.filter_by(username=username).first()
        if doctor and check_password_hash(doctor.password, password):
            session['doctor_user_id'] = doctor.id
            return redirect(url_for('doctor_dashboard'))
        flash('Invalid username or password')
    return render_template('doctor_login.html')
@app.route('/doctor/dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    doctor = db.session.get(Doctor, session['doctor_user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        doctor.name = request.form['name']
        doctor.mobile = request.form['mobile']
        doctor.email = request.form['email']
        doctor.info = request.form['info']
        doctor.qualifications = request.form['qualifications']
        doctor.specializations = request.form['specializations']
        doctor.practice_years = int(request.form['practice_years'])
        doctor.additional_links = request.form['additional_links']
        doctor.practice_location = request.form['practice_location']
        db.session.commit()
        flash('Details updated')
    return render_template('doctor_dashboard.html', doctor=doctor)
@app.route('/doctor/manage_appointments', methods=['GET', 'POST'])
def doctor_manage_appointments():
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    doctor_id = session['doctor_user_id']
    time_slots = TimeSlot.query.filter_by(doctor_id=doctor_id).all()
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        price = float(request.form['price'])
        new_slot = TimeSlot(doctor_id=doctor_id, start_time=start_time, end_time=end_time, price=price)
        db.session.add(new_slot)
        db.session.commit()
        flash('Time slot added')
        return redirect(url_for('doctor_manage_appointments'))
    return render_template('manage_appointments.html', time_slots=time_slots)
@app.route('/doctor/delete_slot/<int:slot_id>')
def doctor_delete_slot(slot_id):
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    slot = TimeSlot.query.get_or_404(slot_id)
    if slot.doctor_id != session['doctor_user_id']:
        abort(403)
    db.session.delete(slot)
    db.session.commit()
    flash('Time slot deleted')
    return redirect(url_for('doctor_manage_appointments'))
@app.route('/doctor/appointments')
def doctor_appointments():
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    doctor_id = session['doctor_user_id']
    today = date.today()
    # Join with TimeSlot to access time_slot information
    appointments = db.session.query(Appointment).join(TimeSlot).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == today,
        Appointment.status == 'paid'
    ).all()
    return render_template('doctor_appointments.html', appointments=appointments, today_date=today)
@app.route('/doctor/medical_records', methods=['GET', 'POST'])
def doctor_medical_records():
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    doctor_id = session['doctor_user_id']
    search = request.args.get('search', '')
    if search:
        records = MedicalRecord.query.filter_by(doctor_id=doctor_id).filter(MedicalRecord.patient_name.like(f'%{search}%')).all()
    else:
        records = MedicalRecord.query.filter_by(doctor_id=doctor_id).all()
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        age = int(request.form['age'])
        mobile = request.form['mobile']
        medical_condition = request.form.get('medical_condition')
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            folder = os.path.join(app.config['UPLOAD_FOLDER'], f'doctor_{doctor_id}')
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(file.filename)
            file_path = os.path.join(folder, filename)
            file.save(file_path)
            new_record = MedicalRecord(doctor_id=doctor_id, patient_name=patient_name, age=age, mobile=mobile, medical_condition=medical_condition, file_path=file_path)
            db.session.add(new_record)
            db.session.commit()
            flash('Medical record added')
        else:
            flash('Invalid file')
        return redirect(url_for('doctor_medical_records'))
    return render_template('medical_records.html', records=records, search=search)
@app.route('/doctor/delete_record/<int:record_id>')
def doctor_delete_record(record_id):
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    record = MedicalRecord.query.get_or_404(record_id)
    if record.doctor_id != session['doctor_user_id']:
        abort(403)
    if os.path.exists(record.file_path):
        os.remove(record.file_path)
    db.session.delete(record)
    db.session.commit()
    flash('Medical record deleted')
    return redirect(url_for('doctor_medical_records'))
@app.route('/doctor/download_record/<int:record_id>')
def doctor_download_record(record_id):
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    record = MedicalRecord.query.get_or_404(record_id)
    if record.doctor_id != session['doctor_user_id']:
        abort(403)
    return send_file(record.file_path, as_attachment=False)
@app.route('/doctor/manage_reviews')
def doctor_manage_reviews():
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    doctor_id = session['doctor_user_id']
    reviews = DoctorReview.query.filter_by(doctor_id=doctor_id).order_by(DoctorReview.created_at.desc()).all()
    return render_template('doctor_manage_reviews.html', reviews=reviews)
@app.route('/doctor/delete_review/<int:review_id>')
def doctor_delete_review(review_id):
    if 'doctor_user_id' not in session:
        return redirect(url_for('doctor_login'))
    review = DoctorReview.query.get_or_404(review_id)
    if review.doctor_id != session['doctor_user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('doctor_manage_reviews'))
# Ambulance Routes (unchanged)
@app.route('/ambulance/login', methods=['GET', 'POST'])
def ambulance_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        ambulance = Ambulance.query.filter_by(username=username).first()
        if ambulance and check_password_hash(ambulance.password, password):
            session['ambulance_user_id'] = ambulance.id
            return redirect(url_for('ambulance_dashboard'))
        flash('Invalid username or password')
    return render_template('ambulance_login.html')
@app.route('/ambulance/dashboard', methods=['GET', 'POST'])
def ambulance_dashboard():
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    ambulance = Ambulance.query.get(session['ambulance_user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        ambulance.name = request.form['name']
        ambulance.mobile = request.form['mobile']
        ambulance.email = request.form['email']
        ambulance.info = request.form['info']
        ambulance.status = request.form['status']
        db.session.commit()
        flash('Details updated')
    return render_template('ambulance_dashboard.html', ambulance=ambulance)
@app.route('/ambulance/vehicles', methods=['GET', 'POST'])
def ambulance_vehicles():
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    ambulance_id = session['ambulance_user_id']
    vehicles = AmbulanceVehicle.query.filter_by(ambulance_id=ambulance_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        numberplate = request.form['numberplate']
        cost_price = float(request.form['cost_price'])
        medical_support = request.form.get('medical_support')
        file = request.files['image']
        image_path = None
        if file and file.filename != '':
            folder = os.path.join(app.config['UPLOAD_FOLDER'], f'ambulance_{ambulance_id}/vehicles')
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(file.filename)
            image_path = os.path.join(folder, filename)
            file.save(image_path)
        new_vehicle = AmbulanceVehicle(ambulance_id=ambulance_id, name=name, numberplate=numberplate, cost_price=cost_price, medical_support=medical_support, image_path=image_path)
        db.session.add(new_vehicle)
        db.session.commit()
        flash('Vehicle added')
        return redirect(url_for('ambulance_vehicles'))
    return render_template('ambulance_vehicles.html', vehicles=vehicles)
@app.route('/ambulance/edit_vehicle/<int:vehicle_id>', methods=['GET', 'POST'])
def ambulance_edit_vehicle(vehicle_id):
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    if vehicle.ambulance_id != session['ambulance_user_id']:
        abort(403)
    if request.method == 'POST':
        vehicle.name = request.form['name']
        vehicle.numberplate = request.form['numberplate']
        vehicle.cost_price = float(request.form['cost_price'])
        vehicle.medical_support = request.form.get('medical_support')
        file = request.files['image']
        if file and file.filename != '':
            if vehicle.image_path and os.path.exists(vehicle.image_path):
                os.remove(vehicle.image_path)
            folder = os.path.join(app.config['UPLOAD_FOLDER'], f'ambulance_{session["ambulance_user_id"]}/vehicles')
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(file.filename)
            vehicle.image_path = os.path.join(folder, filename)
            file.save(vehicle.image_path)
        db.session.commit()
        flash('Vehicle updated')
        return redirect(url_for('ambulance_vehicles'))
    return render_template('ambulance_edit_vehicle.html', vehicle=vehicle)
@app.route('/ambulance/delete_vehicle/<int:vehicle_id>')
def ambulance_delete_vehicle(vehicle_id):
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    if vehicle.ambulance_id != session['ambulance_user_id']:
        abort(403)
    if vehicle.image_path and os.path.exists(vehicle.image_path):
        os.remove(vehicle.image_path)
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle deleted')
    return redirect(url_for('ambulance_vehicles'))
@app.route('/ambulance/bookings')
def ambulance_bookings():
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    ambulance_id = session['ambulance_user_id']
    bookings = AmbulanceBooking.query.filter_by(ambulance_id=ambulance_id).all()
    pending_bookings = [b for b in bookings if b.status == 'pending']
    accepted_bookings = [b for b in bookings if b.status == 'accepted']
    paid_bookings = [b for b in bookings if b.status == 'paid']
    return render_template('ambulance_bookings.html', pending_bookings=pending_bookings, accepted_bookings=accepted_bookings, paid_bookings=paid_bookings)
@app.route('/ambulance/accept_booking/<int:booking_id>', methods=['GET', 'POST'])
def ambulance_accept_booking(booking_id):
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.ambulance_id != session['ambulance_user_id']:
        abort(403)
    if request.method == 'POST':
        live_location_link = request.form['live_location_link']
        booking.live_location_link = live_location_link
        patient = booking.patient
        vehicle = booking.vehicle
        if booking.use_type == 'emergency':
            booking.status = 'paid'
            subject = "Ambulance is on the Way"
            body = f"Dear {patient.name},\n\nAmbulance is on the way. Here is the live location: {live_location_link}\n\nBest regards,\nAmbulance Team"
            send_email(patient.email, subject, body)
        else:
            booking.status = 'accepted'
            pdf_buffer = generate_ambulance_bill_pdf(booking, vehicle)
            subject = "Ambulance Booking Accepted"
            body = f"Dear {patient.name},\n\nYour ambulance booking request has been accepted. Please pay the bill to confirm.\nLive Location Link: {live_location_link}\n\nBest regards,\nAmbulance Team"
            send_email(patient.email, subject, body, pdf_buffer)
        db.session.commit()
        flash('Booking accepted and email sent')
        return redirect(url_for('ambulance_bookings'))
    return render_template('ambulance_accept_booking.html', booking=booking)
@app.route('/ambulance/share_live_location/<int:booking_id>', methods=['GET', 'POST'])
def ambulance_share_live_location(booking_id):
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.ambulance_id != session['ambulance_user_id'] or booking.status not in ['accepted', 'paid']:
        abort(403)
    if request.method == 'POST':
        live_location_link = request.form['live_location_link']
        booking.live_location_link = live_location_link
        patient = booking.patient
        subject = "Ambulance Live Location Updated"
        body = f"Dear {patient.name},\n\nThe live location for your ambulance booking has been updated. Live Location Link: {live_location_link}\n\nBest regards,\nAmbulance Team"
        send_email(patient.email, subject, body)
        db.session.commit()
        flash('Live location shared and email sent')
        return redirect(url_for('ambulance_bookings'))
    return render_template('ambulance_share_live_location.html', booking=booking)
@app.route('/ambulance/reject_booking/<int:booking_id>')
def ambulance_reject_booking(booking_id):
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.ambulance_id != session['ambulance_user_id']:
        abort(403)
    patient = booking.patient
    booking.status = 'rejected'
    if booking.payment_status == 'paid':
        body = f"Dear {patient.name},\n\nYour ambulance booking request has been rejected. Refund will be sent soon.\n\nBest regards,\nAmbulance Team"
    else:
        body = f"Dear {patient.name},\n\nYour ambulance booking request has been rejected.\n\nBest regards,\nAmbulance Team"
    send_email(patient.email, "Ambulance Booking Rejected", body)
    db.session.commit()
    flash('Booking rejected')
    return redirect(url_for('ambulance_bookings'))
@app.route('/ambulance/reviews')
def ambulance_reviews():
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    ambulance_id = session['ambulance_user_id']
    reviews = AmbulanceReview.query.filter_by(ambulance_id=ambulance_id).order_by(AmbulanceReview.created_at.desc()).all()
    return render_template('ambulance_reviews.html', reviews=reviews)
@app.route('/ambulance/delete_review/<int:review_id>')
def ambulance_delete_review(review_id):
    if 'ambulance_user_id' not in session:
        return redirect(url_for('ambulance_login'))
    review = AmbulanceReview.query.get_or_404(review_id)
    if review.ambulance_id != session['ambulance_user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('ambulance_reviews'))
# Nurse Routes (unchanged)
@app.route('/nurse/login', methods=['GET', 'POST'])
def nurse_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nurse = Nurse.query.filter_by(username=username).first()
        if nurse and check_password_hash(nurse.password, password):
            session['nurse_user_id'] = nurse.id
            return redirect(url_for('nurse_dashboard'))
        flash('Invalid username or password')
    return render_template('nurse_login.html')
@app.route('/nurse/dashboard', methods=['GET', 'POST'])
def nurse_dashboard():
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    nurse = Nurse.query.get(session['nurse_user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        nurse.name = request.form['name']
        nurse.mobile = request.form['mobile']
        nurse.email = request.form['email']
        nurse.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    elif request.method == 'POST' and 'update_status' in request.form:
        nurse.status = request.form['status']
        db.session.commit()
        flash('Status updated')
    return render_template('nurse_dashboard.html', nurse=nurse)
@app.route('/nurse/set_price', methods=['GET', 'POST'])
def nurse_set_price():
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    nurse = Nurse.query.get(session['nurse_user_id'])
    rates = NurseRate.query.filter_by(nurse_id=session['nurse_user_id']).all()
    if request.method == 'POST':
        if 'add_rate' in request.form:
            rate_type = request.form['rate_type']
            price = float(request.form['price'])
            existing = NurseRate.query.filter_by(nurse_id=session['nurse_user_id'], rate_type=rate_type).first()
            if existing:
                existing.price = price
            else:
                new_rate = NurseRate(nurse_id=session['nurse_user_id'], rate_type=rate_type, price=price)
                db.session.add(new_rate)
            db.session.commit()
            flash('Rate added/updated')
        elif 'edit_rate' in request.form:
            rate_id = int(request.form['rate_id'])
            price = float(request.form['price'])
            rate = NurseRate.query.get_or_404(rate_id)
            if rate.nurse_id != session['nurse_user_id']:
                abort(403)
            rate.price = price
            db.session.commit()
            flash('Rate updated')
        elif 'delete_rate' in request.form:
            rate_id = int(request.form['rate_id'])
            rate = NurseRate.query.get_or_404(rate_id)
            if rate.nurse_id != session['nurse_user_id']:
                abort(403)
            db.session.delete(rate)
            db.session.commit()
            flash('Rate deleted')
        elif 'update_availability' in request.form:
            availability = ','.join(request.form.getlist('availability'))
            nurse.availability_locations = availability
            db.session.commit()
            flash('Availability updated')
        return redirect(url_for('nurse_set_price'))
    return render_template('nurse_set_price.html', nurse=nurse, rates=rates)
@app.route('/nurse/patient_requests')
def nurse_patient_requests():
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    nurse_id = session['nurse_user_id']
    bookings = NurseBooking.query.filter_by(nurse_id=nurse_id).all()
    pending_bookings = [b for b in bookings if b.status == 'pending']
    accepted_bookings = [b for b in bookings if b.status == 'accepted']
    paid_bookings = [b for b in bookings if b.status == 'paid']
    return render_template('nurse_patient_requests.html', pending_bookings=pending_bookings, accepted_bookings=accepted_bookings, paid_bookings=paid_bookings)
@app.route('/nurse/accept_booking/<int:booking_id>')
def nurse_accept_booking(booking_id):
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    booking = NurseBooking.query.get_or_404(booking_id)
    if booking.nurse_id != session['nurse_user_id']:
        abort(403)
    booking.status = 'accepted'
    nurse = booking.nurse
    patient = booking.patient
    nurse.status = 'booked'
    db.session.commit()
    flash('Booking accepted')
    # Send email to patient
    if patient and patient.email:
        subject = "Nurse Booking Request Accepted"
        body = f"Dear {patient.name},\n\nYour request for Nurse {nurse.name} ({booking.duration_type} at {booking.location}) has been accepted. Please pay the bill to confirm.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body)
    return redirect(url_for('nurse_patient_requests'))
@app.route('/nurse/reject_booking/<int:booking_id>')
def nurse_reject_booking(booking_id):
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    booking = NurseBooking.query.get_or_404(booking_id)
    if booking.nurse_id != session['nurse_user_id']:
        abort(403)
    patient = booking.patient
    nurse = booking.nurse
    booking.status = 'rejected'
    db.session.commit()
    flash('Booking rejected')
    # Send email to patient
    if patient and patient.email:
        subject = "Nurse Booking Request Rejected"
        body = f"Dear {patient.name},\n\nYour request for Nurse {nurse.name} ({booking.duration_type} at {booking.location}) has been rejected.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body)
    return redirect(url_for('nurse_patient_requests'))
@app.route('/nurse/manage_reviews')
def nurse_manage_reviews():
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    nurse_id = session['nurse_user_id']
    reviews = NurseReview.query.filter_by(nurse_id=nurse_id).order_by(NurseReview.created_at.desc()).all()
    return render_template('nurse_manage_reviews.html', reviews=reviews)
@app.route('/nurse/delete_review/<int:review_id>')
def nurse_delete_review(review_id):
    if 'nurse_user_id' not in session:
        return redirect(url_for('nurse_login'))
    review = NurseReview.query.get_or_404(review_id)
    if review.nurse_id != session['nurse_user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('nurse_manage_reviews'))
# Add these routes after the existing patient_edit_nurse_review and patient_delete_nurse_review routes
# (around line 1400-1500, after the nurse review routes and before canteen routes)
@app.route('/patient/add_doctor_review/<int:doctor_id>', methods=['POST'])
def patient_add_doctor_review(doctor_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    rating = int(request.form['rating'])
    text = request.form.get('text')
    new_review = DoctorReview(doctor_id=doctor_id, patient_id=session['patient_user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_doctor', doctor_id=doctor_id))
@app.route('/patient/edit_doctor_review/<int:review_id>', methods=['POST'])
def patient_edit_doctor_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = DoctorReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    review.rating = int(request.form['rating'])
    review.text = request.form.get('text')
    db.session.commit()
    flash('Review updated')
    return redirect(url_for('patient_doctor', doctor_id=review.doctor_id))
@app.route('/patient/delete_doctor_review/<int:review_id>')
def patient_delete_doctor_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = DoctorReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    doctor_id = review.doctor_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_doctor', doctor_id=doctor_id))
# Canteen Routes (updated with new features and status emails)
@app.route('/canteen/login', methods=['GET', 'POST'])
def canteen_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        canteen = Canteen.query.filter_by(username=username).first()
        if canteen and check_password_hash(canteen.password, password):
            session['canteen_user_id'] = canteen.id
            return redirect(url_for('canteen_dashboard'))
        flash('Invalid username or password')
    return render_template('canteen_login.html')
@app.route('/canteen/dashboard', methods=['GET', 'POST'])
def canteen_dashboard():
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    canteen = Canteen.query.get(session['canteen_user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        canteen.name = request.form['name']
        canteen.mobile = request.form['mobile']
        canteen.email = request.form['email']
        canteen.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    # Get preparing orders for dashboard
    preparing_orders = CanteenOrder.query.filter_by(canteen_id=session['canteen_user_id'], status='preparing').all()
    return render_template('canteen_dashboard.html', canteen=canteen, preparing_orders=preparing_orders)
@app.route('/canteen/menu_management', methods=['GET', 'POST'])
def canteen_menu_management():
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    canteen_id = session['canteen_user_id']
    categories = CanteenCategory.query.filter_by(canteen_id=canteen_id).all()
    if request.method == 'POST':
        if 'add_category' in request.form:
            name = request.form['name']
            new_category = CanteenCategory(canteen_id=canteen_id, name=name)
            db.session.add(new_category)
            db.session.commit()
            flash('Category added')
        elif 'edit_category' in request.form:
            category_id = int(request.form['category_id'])
            name = request.form['name']
            category = CanteenCategory.query.get_or_404(category_id)
            if category.canteen_id != canteen_id:
                abort(403)
            category.name = name
            db.session.commit()
            flash('Category updated')
        elif 'delete_category' in request.form:
            category_id = int(request.form['category_id'])
            category = CanteenCategory.query.get_or_404(category_id)
            if category.canteen_id != canteen_id:
                abort(403)
            db.session.delete(category)
            db.session.commit()
            flash('Category deleted')
        elif 'add_item' in request.form:
            category_id = int(request.form['category_id'])
            name = request.form['name']
            price = float(request.form['price'])
            new_item = CanteenItem(category_id=category_id, name=name, price=price)
            db.session.add(new_item)
            db.session.commit()
            flash('Item added')
        elif 'edit_item' in request.form:
            item_id = int(request.form['item_id'])
            name = request.form['name']
            price = float(request.form['price'])
            item = CanteenItem.query.get_or_404(item_id)
            item.name = name
            item.price = price
            db.session.commit()
            flash('Item updated')
        elif 'delete_item' in request.form:
            item_id = int(request.form['item_id'])
            item = CanteenItem.query.get_or_404(item_id)
            db.session.delete(item)
            db.session.commit()
            flash('Item deleted')
        return redirect(url_for('canteen_menu_management'))
    return render_template('canteen_menu_management.html', categories=categories)
@app.route('/canteen/orders')
def canteen_orders():
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    canteen_id = session['canteen_user_id']
    orders = CanteenOrder.query.filter_by(canteen_id=canteen_id).all()
   
    # Pre-load room and bed data for all orders
    orders_with_details = []
    for order in orders:
        order_dict = {
            'order': order,
            'room': None,
            'bed': None
        }
        if order.room_id:
            order_dict['room'] = Room.query.get(order.room_id)
        if order.bed_id:
            order_dict['bed'] = Bed.query.get(order.bed_id)
        orders_with_details.append(order_dict)
   
    # Filter orders by status with their details
    pending_orders = [od for od in orders_with_details if od['order'].status == 'pending']
    accepted_orders = [od for od in orders_with_details if od['order'].status == 'accepted']
    paid_orders = [od for od in orders_with_details if od['order'].status == 'paid']
    delivered_orders = [od for od in orders_with_details if od['order'].status == 'delivered']
    preparing_orders = [od for od in orders_with_details if od['order'].status == 'preparing']
    out_for_delivery_orders = [od for od in orders_with_details if od['order'].status == 'out_for_delivery']
   
    return render_template('canteen_orders.html',
                         pending_orders=pending_orders,
                         accepted_orders=accepted_orders,
                         paid_orders=paid_orders,
                         delivered_orders=delivered_orders,
                         preparing_orders=preparing_orders,
                         out_for_delivery_orders=out_for_delivery_orders)
                        
@app.route('/canteen/accept_order/<int:order_id>')
def canteen_accept_order(order_id):
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    order = CanteenOrder.query.get_or_404(order_id)
    if order.canteen_id != session['canteen_user_id']:
        abort(403)
    order.status = 'accepted'
    db.session.commit()
    patient = order.patient
    total_amount = sum(item.item.price * item.quantity for item in order.items)
    subject = "Your Canteen Order is Accepted"
    body = f"Dear {patient.name},\n\nYour canteen order has been accepted. Total: ₹{total_amount}\nItems:\n"
    for item in order.items:
        body += f"- {item.item.name} x {item.quantity} = ₹{item.item.price * item.quantity}\n"
    body += "\nPlease pay the bill to confirm.\n\nBest regards,\nCanteen Team"
    send_email(patient.email, subject, body)
    flash('Order accepted')
    return redirect(url_for('canteen_orders'))
@app.route('/canteen/reject_order/<int:order_id>')
def canteen_reject_order(order_id):
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    order = CanteenOrder.query.get_or_404(order_id)
    if order.canteen_id != session['canteen_user_id']:
        abort(403)
    order.status = 'rejected'
    db.session.commit()
    patient = order.patient
    subject = "Your Canteen Order is Rejected"
    body = f"Dear {patient.name},\n\nYour canteen order has been rejected. Please place another order or call.\n\nBest regards,\nCanteen Team"
    send_email(patient.email, subject, body)
    flash('Order rejected')
    return redirect(url_for('canteen_orders'))
@app.route('/canteen/update_status/<int:order_id>', methods=['GET', 'POST'])
def canteen_update_status(order_id):
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    order = CanteenOrder.query.get_or_404(order_id)
    if order.canteen_id != session['canteen_user_id']:
        abort(403)
   
    # Pre-load room and bed data for this order
    room = None
    bed = None
    if order.room_id:
        room = Room.query.get(order.room_id)
    if order.bed_id:
        bed = Bed.query.get(order.bed_id)
   
    if request.method == 'POST':
        new_status = request.form['status']
        patient = order.patient
        total_amount = sum(item.item.price * item.quantity for item in order.items)
        if new_status == 'preparing':
            order.status = 'preparing'
            subject = "Your Order is Being Prepared"
            body = f"Dear {patient.name},\n\nYour order is being prepared. Total: ₹{total_amount}\n\nBest regards,\nCanteen Team"
            send_email(patient.email, subject, body)
        elif new_status == 'out_for_delivery':
            order.status = 'out_for_delivery'
            subject = "Your Food is Out for Delivery"
            body = f"Dear {patient.name},\n\nYour food order is out for delivery. Total: ₹{total_amount}\n\nBest regards,\nCanteen Team"
            send_email(patient.email, subject, body)
        elif new_status == 'delivered':
            order.status = 'delivered'
            subject = "Your Order is Delivered Successfully"
            body = f"Dear {patient.name},\n\nYour order is delivered successfully. Total: ₹{total_amount}\n\nBest regards,\nCanteen Team"
            send_email(patient.email, subject, body)
        db.session.commit()
        flash('Status updated')
        return redirect(url_for('canteen_orders'))
   
    return render_template('canteen_update_status.html', order=order, room=room, bed=bed)
   
   
@app.route('/canteen/update_statuses')
def canteen_update_statuses():
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    canteen_id = session['canteen_user_id']
    orders = CanteenOrder.query.filter_by(canteen_id=canteen_id).filter(
        CanteenOrder.status.in_(['accepted', 'paid', 'preparing', 'out_for_delivery'])
    ).order_by(CanteenOrder.created_at.desc()).all()
   
    # Pre-load room and bed data for all orders
    orders_with_details = []
    for order in orders:
        order_dict = {
            'order': order,
            'room': None,
            'bed': None
        }
        if order.room_id:
            order_dict['room'] = Room.query.get(order.room_id)
        if order.bed_id:
            order_dict['bed'] = Bed.query.get(order.bed_id)
        orders_with_details.append(order_dict)
   
    return render_template('canteen_update_statuses.html', orders=orders_with_details)
   
@app.route('/canteen/manage_reviews')
def canteen_manage_reviews():
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    canteen_id = session['canteen_user_id']
    reviews = CanteenReview.query.filter_by(canteen_id=canteen_id).order_by(CanteenReview.created_at.desc()).all()
    return render_template('canteen_manage_reviews.html', reviews=reviews)
@app.route('/canteen/delete_review/<int:review_id>', methods=['POST'])
def canteen_delete_review(review_id):
    if 'canteen_user_id' not in session:
        return redirect(url_for('canteen_login'))
    review = CanteenReview.query.get_or_404(review_id)
    if review.canteen_id != session['canteen_user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('canteen_manage_reviews'))
   
# Patient Routes (updated with canteen features)
@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        patient = Patient.query.filter_by(username=username).first()
        if patient and check_password_hash(patient.password, password):
            session['patient_user_id'] = patient.id
            return redirect(url_for('patient_dashboard'))
        flash('Invalid username or password')
    return render_template('patient_login.html')
@app.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('patient_register.html')
        if Patient.query.filter_by(username=username).first() or Patient.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('patient_register.html')
        hashed_password = generate_password_hash(password)
        new_patient = Patient(name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_patient)
        db.session.commit()
        return redirect(url_for('patient_login'))
    return render_template('patient_register.html')
@app.route('/patient/dashboard', methods=['GET', 'POST'])
def patient_dashboard():
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    patient = Patient.query.get(session['patient_user_id'])
    hospitals = Hospital.query.all()
    bookings = Booking.query.filter_by(patient_id=session['patient_user_id']).all()
    pending_requests = [b for b in bookings if b.status == 'pending']
    accepted_unpaid = [b for b in bookings if b.status == 'accepted']
    history_bookings = [b for b in bookings if b.status in ['paid', 'rejected']]
    # Join appointments with time_slots to access time_slot information
    appointments = db.session.query(Appointment).join(TimeSlot).filter(
        Appointment.patient_id == session['patient_user_id']
    ).all()
    history_appointments = [a for a in appointments if a.status == 'paid']
    # Ambulance
    ambulance_pending = AmbulanceBooking.query.filter_by(patient_id=session['patient_user_id'], status='pending').all()
    ambulance_notifications = AmbulanceBooking.query.filter_by(patient_id=session['patient_user_id'], status='accepted').all()
    ambulance_history = AmbulanceBooking.query.filter_by(patient_id=session['patient_user_id'], status='paid').all()
    # Nurse
    nurse_pending = NurseBooking.query.filter_by(patient_id=session['patient_user_id'], status='pending').all()
    nurse_notifications = NurseBooking.query.filter_by(patient_id=session['patient_user_id'], status='accepted').all()
    nurse_history = NurseBooking.query.filter_by(patient_id=session['patient_user_id'], status='paid').all()
    # Canteen
    canteen_orders = CanteenOrder.query.filter_by(patient_id=session['patient_user_id']).all()
    canteen_pending = [o for o in canteen_orders if o.status == 'pending']
    canteen_notifications = [o for o in canteen_orders if o.status == 'accepted']
    canteen_history = [o for o in canteen_orders if o.status in ['paid', 'delivered', 'preparing', 'out_for_delivery']]
    if request.method == 'POST' and 'edit' in request.form:
        patient.name = request.form['name']
        patient.mobile = request.form['mobile']
        patient.email = request.form['email']
        patient.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    return render_template('patient_dashboard.html', patient=patient, hospitals=hospitals, pending_requests=pending_requests, accepted_unpaid=accepted_unpaid, history_bookings=history_bookings, history_appointments=history_appointments, ambulance_pending=ambulance_pending, ambulance_notifications=ambulance_notifications, ambulance_history=ambulance_history, nurse_pending=nurse_pending, nurse_notifications=nurse_notifications, nurse_history=nurse_history, canteen_pending=canteen_pending, canteen_notifications=canteen_notifications, canteen_history=canteen_history)
@app.route('/patient/hospital/<int:hospital_id>')
def patient_hospital(hospital_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    hospital = Hospital.query.get_or_404(hospital_id)
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).all()
    ambulances = Ambulance.query.filter_by(hospital_id=hospital_id).all()
    nurses = Nurse.query.filter_by(hospital_id=hospital_id).all()
    canteens = Canteen.query.filter_by(hospital_id=hospital_id).all()
    rooms = Room.query.filter_by(hospital_id=hospital_id).all()
    return render_template('patient_hospital.html', hospital=hospital, doctors=doctors, ambulances=ambulances, nurses=nurses, canteens=canteens, rooms=rooms)
@app.route('/patient/canteen/<int:canteen_id>')
def patient_canteen(canteen_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    canteen = Canteen.query.get_or_404(canteen_id)
    categories = CanteenCategory.query.filter_by(canteen_id=canteen_id).all()
    reviews = CanteenReview.query.filter_by(canteen_id=canteen_id).order_by(CanteenReview.created_at.desc()).all()
    # Get rooms and beds for the canteen's hospital
    hospital_id = canteen.hospital_id
    rooms = Room.query.filter_by(hospital_id=hospital_id).all()
    # Build a JSON-serializable map: keys as strings -> list of simple dicts
    beds_by_room = {}
    for room in rooms:
        beds = Bed.query.filter_by(room_id=room.id).all()
        beds_by_room[str(room.id)] = [
            {
                "id": b.id,
                "bed_number": b.bed_number,
                "status": b.status
            }
            for b in beds
        ]
    return render_template('patient_canteen.html', canteen=canteen, categories=categories, reviews=reviews, rooms=rooms, beds_by_room=beds_by_room)
@app.route('/patient/submit_canteen_order/<int:canteen_id>', methods=['POST'])
def patient_submit_canteen_order(canteen_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    # selected_items may be an empty string; ensure it becomes a dict
    selected_items_raw = request.form.get('selected_items', '')
    try:
        selected_items = json.loads(selected_items_raw) if selected_items_raw else {}
    except Exception:
        selected_items = {}
    # room_id/bed_id come from <select>; convert to int only if provided
    room_id_raw = request.form.get('room_id') or None
    bed_id_raw = request.form.get('bed_id') or None
    room_id = int(room_id_raw) if room_id_raw else None
    bed_id = int(bed_id_raw) if bed_id_raw else None
    new_order = CanteenOrder(
        canteen_id=canteen_id,
        patient_id=session['patient_user_id'],
        status='pending',
        payment_status='unpaid',
        room_id=room_id,
        bed_id=bed_id
    )
    db.session.add(new_order)
    db.session.commit()
    for item_id, quantity in selected_items.items():
        order_item = CanteenOrderItem(
            order_id=new_order.id,
            item_id=item_id,
            quantity=quantity
        )
        db.session.add(order_item)
    db.session.commit()
    flash('Order request sent')
    return redirect(url_for('patient_dashboard'))
@app.route('/patient/canteen_bill/<int:order_id>')
def patient_canteen_bill(order_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    order = CanteenOrder.query.get_or_404(order_id)
    if order.patient_id != session['patient_user_id'] or order.status != 'accepted':
        abort(403)
   
    # Pre-load room and bed data
    room = None
    bed = None
    if order.room_id:
        room = Room.query.get(order.room_id)
    if order.bed_id:
        bed = Bed.query.get(order.bed_id)
   
    total_amount = sum(item.item.price * item.quantity for item in order.items)
    return render_template('canteen_bill.html', order=order, total_amount=total_amount, room=room, bed=bed)
   
   
@app.route('/patient/canteen_pay/<int:order_id>')
def patient_canteen_pay(order_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    order = CanteenOrder.query.get_or_404(order_id)
    if order.patient_id != session['patient_user_id'] or order.status != 'accepted':
        abort(403)
    total_amount = sum(item.item.price * item.quantity for item in order.items)
    razorpay_order = razorpay_client.order.create({
        "amount": int(total_amount * 100),
        "currency": "INR",
        "receipt": f"canteen_{order_id}"
    })
    return render_template('canteen_payment.html', order=razorpay_order, key=app.config['RAZORPAY_KEY_ID'], amount=total_amount, order_id=order_id)
@app.route('/canteen_payment_success/<int:order_id>', methods=['POST'])
def canteen_payment_success(order_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        order = CanteenOrder.query.get_or_404(order_id)
        if order.patient_id != session['patient_user_id']:
            abort(403)
        order.status = 'paid'
        order.payment_status = 'paid'
        db.session.commit()
        flash('Payment successful! Order confirmed.')
        patient = Patient.query.get(order.patient_id)
        pdf_buffer = generate_canteen_bill_pdf(order)
        subject = "Canteen Order Confirmed - Thank You!"
        body = f"Dear {patient.name},\n\nThank you for your order. Please find the bill attached.\n\nBest regards,\nCanteen Team"
        send_email(patient.email, subject, body, pdf_buffer)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))
@app.route('/patient/download_canteen_bill/<int:order_id>')
def patient_download_canteen_bill(order_id):
    order = CanteenOrder.query.get_or_404(order_id)
    if order.status != 'paid':
        abort(403)
    if 'patient_user_id' in session and order.patient_id != session['patient_user_id']:
        abort(403)
    buffer = generate_canteen_bill_pdf(order)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"canteen_bill_{order_id}.pdf", mimetype='application/pdf')
@app.route('/patient/add_canteen_review/<int:canteen_id>', methods=['POST'])
def patient_add_canteen_review(canteen_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    rating = int(request.form['rating'])
    text = request.form.get('text')
    new_review = CanteenReview(canteen_id=canteen_id, patient_id=session['patient_user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_canteen', canteen_id=canteen_id))
@app.route('/patient/edit_canteen_review/<int:review_id>', methods=['GET', 'POST'])
def patient_edit_canteen_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = CanteenReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    if request.method == 'POST':
        review.rating = int(request.form['rating'])
        review.text = request.form.get('text')
        db.session.commit()
        flash('Review updated')
        return redirect(url_for('patient_canteen', canteen_id=review.canteen_id))
    return render_template('patient_edit_canteen_review.html', review=review)
@app.route('/patient/delete_canteen_review/<int:review_id>')
def patient_delete_canteen_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = CanteenReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    canteen_id = review.canteen_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_canteen', canteen_id=canteen_id))
@app.route('/patient/nurse/<int:nurse_id>')
def patient_nurse(nurse_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    reviews = NurseReview.query.filter_by(nurse_id=nurse_id).order_by(NurseReview.created_at.desc()).all()
    rates = NurseRate.query.filter_by(nurse_id=nurse_id).all()
    return render_template('patient_nurse.html', nurse=nurse, reviews=reviews, rates=rates)
@app.route('/patient/book_nurse/<int:nurse_id>', methods=['GET', 'POST'])
def patient_book_nurse(nurse_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    if nurse.status != 'available':
        flash('Nurse is already booked')
        return redirect(url_for('patient_nurse', nurse_id=nurse_id))
    if request.method == 'POST':
        duration_type = request.form['duration_type']
        location = request.form['location']
        if location not in nurse.availability_locations.split(','):
            flash('Invalid location')
            return redirect(url_for('patient_book_nurse', nurse_id=nurse_id))
        rate_type = duration_type + '_' + location
        rate = NurseRate.query.filter_by(nurse_id=nurse_id, rate_type=rate_type).first()
        if not rate:
            flash('No rate for this combination')
            return redirect(url_for('patient_book_nurse', nurse_id=nurse_id))
        amount = rate.price
        new_booking = NurseBooking(nurse_id=nurse_id, patient_id=session['patient_user_id'], duration_type=duration_type, location=location, amount=amount)
        db.session.add(new_booking)
        db.session.commit()
        flash('Booking request sent')
        return redirect(url_for('patient_dashboard'))
    return render_template('book_nurse.html', nurse=nurse)
@app.route('/patient/add_nurse_review/<int:nurse_id>', methods=['POST'])
def patient_add_nurse_review(nurse_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    rating = int(request.form['rating'])
    text = request.form.get('text')
    new_review = NurseReview(nurse_id=nurse_id, patient_id=session['patient_user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_nurse', nurse_id=nurse_id))
@app.route('/patient/edit_nurse_review/<int:review_id>', methods=['GET', 'POST'])
def patient_edit_nurse_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = NurseReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    if request.method == 'POST':
        review.rating = int(request.form['rating'])
        review.text = request.form.get('text')
        db.session.commit()
        flash('Review updated')
        return redirect(url_for('patient_nurse', nurse_id=review.nurse_id))
    return render_template('patient_edit_nurse_review.html', review=review)
@app.route('/patient/delete_nurse_review/<int:review_id>')
def patient_delete_nurse_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = NurseReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    nurse_id = review.nurse_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_nurse', nurse_id=nurse_id))
@app.route('/patient/nurse_bill/<int:booking_id>')
def patient_nurse_bill(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    booking = NurseBooking.query.get_or_404(booking_id)
    if booking.patient_id != session['patient_user_id'] or booking.status != 'accepted':
        abort(403)
    nurse = booking.nurse
    amount = booking.amount
    return render_template('nurse_bill.html', booking=booking, amount=amount, nurse=nurse)
@app.route('/patient/nurse_pay/<int:booking_id>')
def patient_nurse_pay(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    booking = NurseBooking.query.get_or_404(booking_id)
    if booking.patient_id != session['patient_user_id'] or booking.status != 'accepted':
        abort(403)
    amount = booking.amount
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"nurse_{booking_id}"
    })
    return render_template('nurse_payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, booking_id=booking_id, success_url=url_for('nurse_payment_success', booking_id=booking_id))
@app.route('/nurse_payment_success/<int:booking_id>', methods=['POST'])
def nurse_payment_success(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        booking = NurseBooking.query.get_or_404(booking_id)
        if booking.patient_id != session['patient_user_id']:
            abort(403)
        booking.status = 'paid'
        db.session.commit()
        flash('Payment successful! Nurse booked.')
        patient = Patient.query.get(booking.patient_id)
        nurse = booking.nurse
        pdf_buffer = generate_nurse_bill_pdf(booking, nurse)
        subject = "Nurse Booking Confirmed - Thank You!"
        body = f"Dear {patient.name},\n\nThank you for booking the nurse. Please find the bill attached.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body, pdf_buffer)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))
@app.route('/patient/download_nurse_bill/<int:booking_id>')
def patient_download_nurse_bill(booking_id):
    booking = NurseBooking.query.get_or_404(booking_id)
    if booking.status != 'paid':
        abort(403)
    if 'patient_user_id' in session and booking.patient_id != session['patient_user_id']:
        abort(403)
    nurse = booking.nurse
    buffer = generate_nurse_bill_pdf(booking, nurse)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"nurse_bill_{booking_id}.pdf", mimetype='application/pdf')
@app.route('/patient/ambulance/<int:ambulance_id>', methods=['GET', 'POST'])
def patient_ambulance(ambulance_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    vehicles = AmbulanceVehicle.query.filter_by(ambulance_id=ambulance_id).all()
    reviews = AmbulanceReview.query.filter_by(ambulance_id=ambulance_id).order_by(AmbulanceReview.created_at.desc()).all()
    return render_template('patient_ambulance.html', ambulance=ambulance, vehicles=vehicles, reviews=reviews)
@app.route('/patient/book_ambulance_normal/<int:vehicle_id>')
def patient_book_ambulance_normal(vehicle_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    new_booking = AmbulanceBooking(
        ambulance_id=vehicle.ambulance_id,
        vehicle_id=vehicle_id,
        patient_id=session['patient_user_id'],
        use_type='normal',
        amount=vehicle.cost_price,
        status='pending',
        payment_status='unpaid'
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Ambulance booking request sent')
    return redirect(url_for('patient_dashboard'))
@app.route('/patient/emergency_ambulance/<int:vehicle_id>', methods=['GET', 'POST'])
def patient_emergency_ambulance(vehicle_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    if request.method == 'POST':
        location_link = request.form['location_link']
        new_booking = AmbulanceBooking(
            ambulance_id=vehicle.ambulance_id,
            vehicle_id=vehicle_id,
            patient_id=session['patient_user_id'],
            use_type='emergency',
            location_link=location_link,
            amount=vehicle.cost_price * 2,
            status='pending',
            payment_status='unpaid'
        )
        db.session.add(new_booking)
        db.session.commit()
        return redirect(url_for('patient_ambulance_bill', booking_id=new_booking.id))
    return render_template('emergency_book.html', vehicle=vehicle)
@app.route('/patient/ambulance_bill/<int:booking_id>')
def patient_ambulance_bill(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.patient_id != session['patient_user_id'] or booking.payment_status != 'unpaid':
        abort(403)
    vehicle = booking.vehicle
    return render_template('ambulance_bill.html', booking=booking, amount=booking.amount, vehicle=vehicle)
@app.route('/patient/ambulance_pay/<int:booking_id>')
def patient_ambulance_pay(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.patient_id != session['patient_user_id'] or booking.payment_status != 'unpaid':
        abort(403)
    amount = booking.amount
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"ambulance_{booking_id}"
    })
    return render_template('payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, booking_id=booking_id, success_url=url_for('ambulance_payment_success', booking_id=booking_id))
@app.route('/ambulance_payment_success/<int:booking_id>', methods=['POST'])
def ambulance_payment_success(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        booking = AmbulanceBooking.query.get_or_404(booking_id)
        if booking.patient_id != session['patient_user_id']:
            abort(403)
        booking.payment_status = 'paid'
        db.session.commit()
        flash('Payment successful! Ambulance booked.')
        patient = Patient.query.get(booking.patient_id)
        vehicle = booking.vehicle
        pdf_buffer = generate_ambulance_bill_pdf(booking, vehicle)
        subject = "Ambulance Booking Confirmed - Thank You!"
        body = f"Dear {patient.name},\n\nThank you for booking the ambulance. Please find the bill attached.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body, pdf_buffer)
        if booking.use_type == 'emergency':
            ambulance = Ambulance.query.get(booking.ambulance_id)
            emergency_subject = "Emergency Paid Booking Request"
            emergency_body = f"Emergency paid request from {patient.name}. Location: {booking.location_link}. Please accept and share live location."
            send_email(ambulance.email, emergency_subject, emergency_body)
            patient_subject = "Emergency Booking Paid - Waiting for Dispatch"
            patient_body = f"Your emergency ambulance booking is paid. Waiting for the ambulance team to accept and dispatch."
            send_email(patient.email, patient_subject, patient_body)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))
@app.route('/patient/add_ambulance_review/<int:ambulance_id>', methods=['POST'])
def patient_add_ambulance_review(ambulance_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    rating = int(request.form['rating'])
    text = request.form.get('text')
    new_review = AmbulanceReview(ambulance_id=ambulance_id, patient_id=session['patient_user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_ambulance', ambulance_id=ambulance_id))
@app.route('/patient/edit_ambulance_review/<int:review_id>', methods=['GET', 'POST'])
def patient_edit_ambulance_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = AmbulanceReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    if request.method == 'POST':
        review.rating = int(request.form['rating'])
        review.text = request.form.get('text')
        db.session.commit()
        flash('Review updated')
        return redirect(url_for('patient_ambulance', ambulance_id=review.ambulance_id))
    return render_template('patient_edit_ambulance_review.html', review=review)
@app.route('/patient/delete_ambulance_review/<int:review_id>')
def patient_delete_ambulance_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = AmbulanceReview.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    ambulance_id = review.ambulance_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_ambulance', ambulance_id=ambulance_id))
@app.route('/patient/doctor/<int:doctor_id>')
def patient_doctor(doctor_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    reviews = DoctorReview.query.filter_by(doctor_id=doctor_id).order_by(DoctorReview.created_at.desc()).all()
    return render_template('patient_doctor.html', doctor=doctor, reviews=reviews)
@app.route('/patient/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def patient_book_appointment(doctor_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    time_slots = TimeSlot.query.filter_by(doctor_id=doctor_id).all()
    if request.method == 'POST':
        appointment_date = datetime.strptime(request.form['appointment_date'], '%Y-%m-%d').date()
        time_slot_id = int(request.form['time_slot_id'])
        # Check if slot is available
        existing = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=appointment_date, time_slot_id=time_slot_id, status='paid').first()
        if existing:
            flash('Slot not available')
            return redirect(url_for('patient_book_appointment', doctor_id=doctor_id))
        new_appointment = Appointment(doctor_id=doctor_id, patient_id=session['patient_user_id'], appointment_date=appointment_date, time_slot_id=time_slot_id, status='accepted') # Directly accepted for simplicity
        db.session.add(new_appointment)
        db.session.commit()
        return redirect(url_for('patient_appointment_bill', appointment_id=new_appointment.id))
    return render_template('book_appointment.html', doctor=doctor, time_slots=time_slots)
@app.route('/patient/appointment_bill/<int:appointment_id>')
def patient_appointment_bill(appointment_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != session['patient_user_id'] or appointment.status != 'accepted':
        abort(403)
    time_slot = TimeSlot.query.get(appointment.time_slot_id)
    amount = time_slot.price
    return render_template('appointment_bill.html', appointment=appointment, amount=amount, time_slot=time_slot, doctor=appointment.doctor)
@app.route('/patient/appointment_pay/<int:appointment_id>')
def patient_appoinment_pay(appointment_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != session['patient_user_id'] or appointment.status != 'accepted':
        abort(403)
    time_slot = TimeSlot.query.get(appointment.time_slot_id)
    amount = time_slot.price
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"appointment_{appointment_id}"
    })
    return render_template('appointment_payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, appointment_id=appointment_id, success_url=url_for('payment_success_appointment', appointment_id=appointment_id))
@app.route('/payment_success_appointment/<int:appointment_id>', methods=['POST'])
def payment_success_appointment(appointment_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        appointment = Appointment.query.get_or_404(appointment_id)
        if appointment.patient_id != session['patient_user_id']:
            abort(403)
        appointment.status = 'paid'
        db.session.commit()
        flash('Payment successful! Appointment booked.')
        # Send email to patient with bill
        patient = Patient.query.get(appointment.patient_id)
        if patient and patient.email:
            time_slot = TimeSlot.query.get(appointment.time_slot_id)
            pdf_buffer = generate_appointment_bill_pdf(appointment, time_slot)
            subject = "Appointment Booked - Thank You!"
            body = f"Dear {patient.name},\n\nThank you for booking the appointment. Please find the bill attached.\n\nBest regards,\nHospital Team"
            send_email(patient.email, subject, body, pdf_buffer)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))
@app.route('/download_appointment_bill/<int:appointment_id>')
def download_appointment_bill(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.status != 'paid':
        abort(403)
    if 'patient_user_id' in session:
        if appointment.patient_id != session['patient_user_id']:
            abort(403)
    elif 'doctor_user_id' in session:
        if appointment.doctor_id != session['doctor_user_id']:
            abort(403)
    else:
        abort(403)
    time_slot = TimeSlot.query.get(appointment.time_slot_id)
    buffer = generate_appointment_bill_pdf(appointment, time_slot)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"appointment_bill_{appointment_id}.pdf", mimetype='application/pdf')
@app.route('/patient/download_ambulance_bill/<int:booking_id>')
def patient_download_ambulance_bill(booking_id):
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.status != 'paid':
        abort(403)
    if 'patient_user_id' in session and booking.patient_id != session['patient_user_id']:
        abort(403)
    vehicle = booking.vehicle
    buffer = generate_ambulance_bill_pdf(booking, vehicle)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"ambulance_bill_{booking_id}.pdf", mimetype='application/pdf')
@app.route('/patient/hospital/<int:hospital_id>/room/<int:room_id>')
def patient_room(hospital_id, room_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    room = Room.query.get_or_404(room_id)
    if room.hospital_id != hospital_id:
        abort(404)
    beds = Bed.query.filter_by(room_id=room_id).all()
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    return render_template('patient_room.html', room=room, beds=beds, hospital_id=hospital_id, reviews=reviews)
@app.route('/patient/book_bed', methods=['POST'])
def patient_book_bed():
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    bed_id = int(request.form['bed_id'])
    bed = Bed.query.get_or_404(bed_id)
    if bed.status != 'available':
        flash('Bed not available')
        return redirect(url_for('patient_room', hospital_id=bed.room.hospital_id, room_id=bed.room_id))
    room = Room.query.get(bed.room_id)
    hospital_id = room.hospital_id
    check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
    new_booking = Booking(
        bed_id=bed_id,
        patient_id=session['patient_user_id'],
        patient_name=request.form['patient_name'],
        contact_number=request.form['contact_number'],
        age=int(request.form['age']),
        medical_condition=request.form.get('medical_condition'),
        estimated_stay=int(request.form['estimated_stay']),
        check_in_date=check_in_date
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Booking request sent')
    return redirect(url_for('patient_hospital', hospital_id=hospital_id))
@app.route('/patient/add_review/<int:room_id>', methods=['POST'])
def patient_add_review(room_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    room = Room.query.get_or_404(room_id)
    rating = int(request.form['rating'])
    text = request.form['text']
    new_review = Review(room_id=room_id, patient_id=session['patient_user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_room', hospital_id=room.hospital_id, room_id=room_id))
@app.route('/patient/edit_review/<int:review_id>', methods=['POST'])
def patient_edit_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = Review.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    review.rating = int(request.form['rating'])
    review.text = request.form['text']
    db.session.commit()
    flash('Review updated')
    return redirect(url_for('patient_room', hospital_id=review.room.hospital_id, room_id=review.room_id))
@app.route('/patient/delete_review/<int:review_id>')
def patient_delete_review(review_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    review = Review.query.get_or_404(review_id)
    if review.patient_id != session['patient_user_id']:
        abort(403)
    room_id = review.room_id
    hospital_id = review.room.hospital_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_room', hospital_id=hospital_id, room_id=room_id))
@app.route('/patient/bill/<int:booking_id>')
def patient_bill(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.patient_id != session['patient_user_id'] or booking.status != 'accepted':
        abort(403)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    amount = room.price_per_bed * booking.estimated_stay
    return render_template('bill.html', booking=booking, amount=amount, room=room, bed=bed)
@app.route('/patient/pay/<int:booking_id>')
def patient_pay(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.patient_id != session['patient_user_id'] or booking.status != 'accepted':
        abort(403)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    amount = room.price_per_bed * booking.estimated_stay
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"booking_{booking_id}"
    })
    return render_template('payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, booking_id=booking_id, success_url=url_for('payment_success', booking_id=booking_id))
@app.route('/payment_success/<int:booking_id>', methods=['POST'])
def payment_success(booking_id):
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        booking = Booking.query.get_or_404(booking_id)
        if booking.patient_id != session['patient_user_id']:
            abort(403)
        booking.status = 'paid'
        bed = Bed.query.get(booking.bed_id)
        bed.status = 'booked'
        db.session.commit()
        flash('Payment successful! Bed booked.')
        # Send email to patient with bill
        patient = Patient.query.get(booking.patient_id)
        if patient and patient.email:
            bed_obj = Bed.query.get(booking.bed_id)
            room = Room.query.get(bed_obj.room_id)
            pdf_buffer = generate_booking_bill_pdf(booking, bed_obj, room)
            subject = "Bed Booking Confirmed - Here are the Details and Bill"
            body = f"Dear {patient.name},\n\nYour bed booking is confirmed. Please find all details and the bill attached.\n\nBest regards,\nHospital Team"
            send_email(patient.email, subject, body, pdf_buffer)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))
@app.route('/download_bill/<int:booking_id>')
def download_bill(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'paid':
        abort(403)
    if 'patient_user_id' in session:
        if booking.patient_id != session['patient_user_id']:
            abort(403)
    elif 'admin_user_id' in session:
        bed = Bed.query.get(booking.bed_id)
        room = Room.query.get(bed.room_id)
        if room.hospital_id != session['admin_user_id']:
            abort(403)
    else:
        abort(403)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    buffer = generate_booking_bill_pdf(booking, bed, room)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"bill_{booking_id}.pdf", mimetype='application/pdf')
# Add these routes before the @app.route('/logout')
@app.route('/patient/ai_chat')
def patient_ai_chat():
    if 'patient_user_id' not in session:
        return redirect(url_for('patient_login'))
    if 'chat_history' not in session:
        session['chat_history'] = []
    if 'bot_state' not in session:
        session['bot_state'] = {'context': 'start', 'current_entity': None, 'current_list': []}
    return render_template('ai_chat.html', history=session['chat_history'])
@app.route('/patient/send_ai_message', methods=['POST'])
def send_ai_message():
    if 'patient_user_id' not in session:
        return jsonify({'error': 'Unauthorized'})
    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'message': 'Please enter a message.', 'buttons': []})
    # Append user message to history
    session['chat_history'].append({'role': 'user', 'content': user_message})
   
    state = session['bot_state']
    message_lower = user_message.lower()
    response_data = {'message': '', 'buttons': []}
    processed = False
    # Handle clear chat
    if message_lower == 'clear':
        session['chat_history'] = []
        session['bot_state'] = {'context': 'start', 'current_entity': None, 'current_list': []}
        session.modified = True
        response_data['message'] = "Chat cleared! How can I help you today, as Harsh your hospital assistant?"
        processed = True
    # Start context
    elif state['context'] == 'start':
        if any(phrase in message_lower for phrase in ['hospitals', 'hospital available', 'list hospitals']):
            hospitals = Hospital.query.all()
            if hospitals:
                numbered = '\n'.join([f"{i+1}. {h.name}" for i, h in enumerate(hospitals)])
                response_data['message'] = f"Hi! I'm Harsh, your hospital assistant. Here are the available hospitals:\n{numbered}\nPlease type the number (or hospital name) to select one."
                state['context'] = 'waiting_hospital_selection'
                state['current_list'] = [(h.id, h.name) for h in hospitals]
            else:
                response_data['message'] = "No hospitals are available right now. Please check back later."
            processed = True
        elif any(phrase in message_lower for phrase in ['appointment', 'book doctor', 'see doctor']):
            response_data['message'] = "To book an appointment, first select a hospital by saying 'hospitals available', then choose doctors."
            response_data['buttons'] = [
                {'text': 'Available Hospitals', 'type': 'action', 'action': 'give me hospitals available'}
            ]
            processed = True
        elif 'ambulance' in message_lower:
            response_data['message'] = "To book an ambulance, first select a hospital by saying 'hospitals available', then choose ambulances."
            response_data['buttons'] = [
                {'text': 'Available Hospitals', 'type': 'action', 'action': 'give me hospitals available'}
            ]
            processed = True
        elif 'nurse' in message_lower:
            response_data['message'] = "To book a nurse, first select a hospital by saying 'hospitals available', then choose nurses."
            response_data['buttons'] = [
                {'text': 'Available Hospitals', 'type': 'action', 'action': 'give me hospitals available'}
            ]
            processed = True
        elif 'canteen' in message_lower or 'food' in message_lower or 'menu' in message_lower:
            response_data['message'] = "To view canteen menu, first select a hospital by saying 'hospitals available', then choose canteen."
            response_data['buttons'] = [
                {'text': 'Available Hospitals', 'type': 'action', 'action': 'give me hospitals available'}
            ]
            processed = True
        elif 'medical advice' in message_lower or 'help' in message_lower or 'hi' in message_lower:
            system_prompt = """You are Harsh, a friendly and knowledgeable hospital assistant.
            You only answer questions related to medical topics, hospital features, services, and general health advice.
            Be concise, empathetic, and professional. If the question is off-topic, politely redirect to hospital services.
            Start with a greeting if appropriate."""
            messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_message}]
            ai_response = call_openrouter(messages)
            response_data['message'] = ai_response
            processed = True
        else:
            # General AI response
            system_prompt = """You are Harsh, a friendly and knowledgeable hospital assistant.
            You only answer questions related to medical topics, hospital features, services, and general health advice.
            Be concise, empathetic, and professional. If the question is off-topic, say: "I'm here to help with hospital services and medical queries. Try asking about hospitals, doctors, or health tips!"
            Suggest using 'hospitals available' to start."""
            messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_message}]
            ai_response = call_openrouter(messages)
            response_data['message'] = ai_response
            processed = True
    # Hospital selection
    elif state['context'] == 'waiting_hospital_selection':
        selected = None
        try:
            num = int(message_lower)
            if 1 <= num <= len(state['current_list']):
                h_id, h_name = state['current_list'][num - 1]
                selected = (h_id, h_name)
        except ValueError:
            pass
        if not selected:
            for h_id, h_name in state['current_list']:
                if h_name.lower() in message_lower:
                    selected = (h_id, h_name)
                    break
        if selected:
            h_id, h_name = selected
            state['current_entity'] = {'type': 'hospital', 'id': h_id, 'name': h_name}
            state['context'] = 'hospital_menu'
            response_data['message'] = f"Great choice! You selected {h_name}. What would you like to explore?"
            response_data['buttons'] = [
                {'text': 'Contact Information', 'type': 'action', 'action': 'show_hospital_contact'},
                {'text': 'View Doctors', 'type': 'action', 'action': 'list_doctors'},
                {'text': 'View Ambulances', 'type': 'action', 'action': 'list_ambulances'},
                {'text': 'View Nurses', 'type': 'action', 'action': 'list_nurses'},
                {'text': 'View Canteen Menu', 'type': 'action', 'action': 'view_canteen'},
                {'text': 'Back to Hospitals', 'type': 'action', 'action': 'list_hospitals'},
                {'text': 'Main Menu', 'type': 'action', 'action': 'start'}
            ]
            processed = True
        else:
            response_data['message'] = "I didn't catch that. Please type a number (1, 2, etc.) or part of the hospital name."
            processed = True
    # Hospital menu
    elif state['context'] == 'hospital_menu':
        hospital = Hospital.query.get(state['current_entity']['id'])
        if message_lower == 'show_hospital_contact':
            info = f"Contact for {hospital.name}:\nEmail: {hospital.email}\nMobile: {hospital.mobile}\nInfo: {hospital.info or 'N/A'}"
            response_data['message'] = info
            response_data['buttons'] = [
                {'text': 'Back to Hospital Options', 'type': 'action', 'action': 'hospital_menu'},
                {'text': 'Main Menu', 'type': 'action', 'action': 'start'}
            ]
            processed = True
        elif message_lower == 'list_doctors':
            doctors = Doctor.query.filter_by(hospital_id=state['current_entity']['id']).all()
            if doctors:
                numbered = '\n'.join([f"{i+1}. Dr. {d.name}" for i, d in enumerate(doctors)])
                response_data['message'] = f"Doctors available at {hospital.name}:\n{numbered}\nType the number to select."
                state['context'] = 'waiting_doctor_selection'
                state['current_list'] = [(d.id, d.name) for d in doctors]
            else:
                response_data['message'] = "No doctors are currently listed for this hospital."
                response_data['buttons'] = [
                    {'text': 'Back to Hospital Options', 'type': 'action', 'action': 'hospital_menu'}
                ]
            processed = True
        elif message_lower == 'list_ambulances':
            ambulances = Ambulance.query.filter_by(hospital_id=state['current_entity']['id']).all()
            if ambulances:
                numbered = '\n'.join([f"{i+1}. {a.name}" for i, a in enumerate(ambulances)])
                response_data['message'] = f"Ambulances at {hospital.name}:\n{numbered}\nType the number to select."
                state['context'] = 'waiting_ambulance_selection'
                state['current_list'] = [(a.id, a.name) for a in ambulances]
            else:
                response_data['message'] = "No ambulances are currently listed for this hospital."
                response_data['buttons'] = [
                    {'text': 'Back to Hospital Options', 'type': 'action', 'action': 'hospital_menu'}
                ]
            processed = True
        elif message_lower == 'list_nurses':
            nurses = Nurse.query.filter_by(hospital_id=state['current_entity']['id']).all()
            if nurses:
                numbered = '\n'.join([f"{i+1}. {n.name}" for i, n in enumerate(nurses)])
                response_data['message'] = f"Nurses at {hospital.name}:\n{numbered}\nType the number to select."
                state['context'] = 'waiting_nurse_selection'
                state['current_list'] = [(n.id, n.name) for n in nurses]
            else:
                response_data['message'] = "No nurses are currently listed for this hospital."
                response_data['buttons'] = [
                    {'text': 'Back to Hospital Options', 'type': 'action', 'action': 'hospital_menu'}
                ]
            processed = True
        elif message_lower == 'view_canteen':
            canteens = Canteen.query.filter_by(hospital_id=state['current_entity']['id']).all()
            if canteens:
                # Assume first canteen or list if multiple; here take first
                c = canteens[0]
                url = url_for('patient_canteen', canteen_id=c.id)
                response_data['message'] = f"Redirecting to the canteen menu for {c.name}."
                response_data['buttons'] = [
                    {'text': 'View Canteen Menu', 'type': 'redirect', 'url': url},
                    {'text': 'Back to Hospital Options', 'type': 'action', 'action': 'hospital_menu'}
                ]
            else:
                response_data['message'] = "No canteen is currently available for this hospital."
                response_data['buttons'] = [
                    {'text': 'Back to Hospital Options', 'type': 'action', 'action': 'hospital_menu'}
                ]
            processed = True
        elif message_lower in ['list_hospitals', 'start']:
            state['context'] = 'start'
            state['current_entity'] = None
            response_data['message'] = "Back to main. Say 'hospitals available' or ask about health."
            processed = True
        else:
            # AI fallback
            system_prompt = f"You are Harsh... Current context: Hospital {state['current_entity']['name']}. Keep responses relevant to this hospital's features."
            messages = [{'role': 'system', 'content': system_prompt}]
            for h in session['chat_history'][-6:]: # Last 3 exchanges
                messages.append({'role': h['role'], 'content': h['content']})
            ai_response = call_openrouter(messages)
            response_data['message'] = ai_response
            processed = True
    # Doctor selection
    elif state['context'] == 'waiting_doctor_selection':
        selected = None
        try:
            num = int(message_lower)
            if 1 <= num <= len(state['current_list']):
                d_id, d_name = state['current_list'][num - 1]
                selected = (d_id, d_name)
        except ValueError:
            pass
        if not selected:
            for d_id, d_name in state['current_list']:
                if d_name.lower() in message_lower:
                    selected = (d_id, d_name)
                    break
        if selected:
            d_id, d_name = selected
            state['current_entity'] = {'type': 'doctor', 'id': d_id, 'name': d_name, 'hospital_id': state['current_entity']['id']}
            state['context'] = 'doctor_menu'
            book_url = url_for('patient_book_appointment', doctor_id=d_id)
            response_data['message'] = f"You selected Dr. {d_name}. Here's what you can do:"
            response_data['buttons'] = [
                {'text': 'Contact Information', 'type': 'action', 'action': 'show_doctor_contact'},
                {'text': 'Book Appointment', 'type': 'redirect', 'url': book_url},
                {'text': 'Back to Doctors List', 'type': 'action', 'action': 'list_doctors'},
                {'text': 'Back to Hospital', 'type': 'action', 'action': 'hospital_menu'}
            ]
            processed = True
        else:
            response_data['message'] = "Please enter a valid number or doctor name."
            processed = True
    # Doctor menu
    elif state['context'] == 'doctor_menu':
        doctor = Doctor.query.get(state['current_entity']['id'])
        if message_lower == 'show_doctor_contact':
            info = f"Contact for Dr. {doctor.name}:\nEmail: {doctor.email}\nMobile: {doctor.mobile}\nSpecializations: {doctor.specializations or 'N/A'}\nExperience: {doctor.practice_years} years"
            response_data['message'] = info
            response_data['buttons'] = [
                {'text': 'Back to Doctor Options', 'type': 'action', 'action': 'doctor_menu'},
                {'text': 'Back to Hospital', 'type': 'action', 'action': 'hospital_menu'}
            ]
            processed = True
        elif message_lower == 'list_doctors':
            state['context'] = 'waiting_doctor_selection'
            hospital = Hospital.query.get(state['current_entity']['hospital_id'])
            doctors = Doctor.query.filter_by(hospital_id=state['current_entity']['hospital_id']).all()
            numbered = '\n'.join([f"{i+1}. Dr. {d.name}" for i, d in enumerate(doctors)])
            response_data['message'] = f"Doctors at {hospital.name}:\n{numbered}\nType the number."
            state['current_list'] = [(d.id, d.name) for d in doctors]
            processed = True
        elif message_lower in ['hospital_menu', 'list_hospitals', 'start']:
            state['context'] = 'hospital_menu'
            response_data['message'] = f"Back to {state['current_entity']['name']} options."
            # Re-add hospital buttons
            response_data['buttons'] = [
                {'text': 'Contact Information', 'type': 'action', 'action': 'show_hospital_contact'},
                {'text': 'View Doctors', 'type': 'action', 'action': 'list_doctors'},
                # ... other hospital buttons
            ]
            processed = True
        else:
            # AI fallback for doctor context
            system_prompt = f"You are Harsh... Current doctor: Dr. {state['current_entity']['name']}. Answer medical questions related to this doctor or general."
            messages = [{'role': 'system', 'content': system_prompt}]
            for h in session['chat_history'][-6:]:
                messages.append({'role': h['role'], 'content': h['content']})
            ai_response = call_openrouter(messages)
            response_data['message'] = ai_response
            processed = True
    # Ambulance selection
    elif state['context'] == 'waiting_ambulance_selection':
        selected = None
        try:
            num = int(message_lower)
            if 1 <= num <= len(state['current_list']):
                a_id, a_name = state['current_list'][num - 1]
                selected = (a_id, a_name)
        except ValueError:
            pass
        if not selected:
            for a_id, a_name in state['current_list']:
                if a_name.lower() in message_lower:
                    selected = (a_id, a_name)
                    break
        if selected:
            a_id, a_name = selected
            state['current_entity'] = {'type': 'ambulance', 'id': a_id, 'name': a_name, 'hospital_id': state['current_entity']['id']}
            state['context'] = 'ambulance_menu'
            amb_url = url_for('patient_ambulance', ambulance_id=a_id)
            response_data['message'] = f"You selected {a_name}. Ready to book?"
            response_data['buttons'] = [
                {'text': 'Contact Information', 'type': 'action', 'action': 'show_ambulance_contact'},
                {'text': 'Book Normal Ambulance', 'type': 'redirect', 'url': amb_url},
                {'text': 'Book Emergency Ambulance', 'type': 'redirect', 'url': amb_url}, # Same page for selection
                {'text': 'Back to Ambulances List', 'type': 'action', 'action': 'list_ambulances'},
                {'text': 'Back to Hospital', 'type': 'action', 'action': 'hospital_menu'}
            ]
            processed = True
        else:
            response_data['message'] = "Please enter a valid number or ambulance name."
            processed = True
    # Ambulance menu
    elif state['context'] == 'ambulance_menu':
        ambulance = Ambulance.query.get(state['current_entity']['id'])
        if message_lower == 'show_ambulance_contact':
            info = f"Contact for {ambulance.name}:\nEmail: {ambulance.email}\nMobile: {ambulance.mobile}\nStatus: {ambulance.status}"
            response_data['message'] = info
            response_data['buttons'] = [
                {'text': 'Back to Ambulance Options', 'type': 'action', 'action': 'ambulance_menu'},
                {'text': 'Back to Hospital', 'type': 'action', 'action': 'hospital_menu'}
            ]
            processed = True
        elif message_lower == 'list_ambulances':
            state['context'] = 'waiting_ambulance_selection'
            hospital = Hospital.query.get(state['current_entity']['hospital_id'])
            ambulances = Ambulance.query.filter_by(hospital_id=state['current_entity']['hospital_id']).all()
            numbered = '\n'.join([f"{i+1}. {a.name}" for i, a in enumerate(ambulances)])
            response_data['message'] = f"Ambulances at {hospital.name}:\n{numbered}\nType the number."
            state['current_list'] = [(a.id, a.name) for a in ambulances]
            processed = True
        else:
            # AI fallback
            system_prompt = f"You are Harsh... Current ambulance: {state['current_entity']['name']}. Answer about ambulance services."
            messages = [{'role': 'system', 'content': system_prompt}]
            for h in session['chat_history'][-6:]:
                messages.append({'role': h['role'], 'content': h['content']})
            ai_response = call_openrouter(messages)
            response_data['message'] = ai_response
            processed = True
    # Nurse selection
    elif state['context'] == 'waiting_nurse_selection':
        selected = None
        try:
            num = int(message_lower)
            if 1 <= num <= len(state['current_list']):
                n_id, n_name = state['current_list'][num - 1]
                selected = (n_id, n_name)
        except ValueError:
            pass
        if not selected:
            for n_id, n_name in state['current_list']:
                if n_name.lower() in message_lower:
                    selected = (n_id, n_name)
                    break
        if selected:
            n_id, n_name = selected
            state['current_entity'] = {'type': 'nurse', 'id': n_id, 'name': n_name, 'hospital_id': state['current_entity']['id']}
            state['context'] = 'nurse_menu'
            book_url = url_for('patient_book_nurse', nurse_id=n_id)
            response_data['message'] = f"You selected {n_name}. Ready to book?"
            response_data['buttons'] = [
                {'text': 'Contact Information', 'type': 'action', 'action': 'show_nurse_contact'},
                {'text': 'Book Nurse', 'type': 'redirect', 'url': book_url},
                {'text': 'Back to Nurses List', 'type': 'action', 'action': 'list_nurses'},
                {'text': 'Back to Hospital', 'type': 'action', 'action': 'hospital_menu'}
            ]
            processed = True
        else:
            response_data['message'] = "Please enter a valid number or nurse name."
            processed = True
    # Nurse menu
    elif state['context'] == 'nurse_menu':
        nurse = Nurse.query.get(state['current_entity']['id'])
        if message_lower == 'show_nurse_contact':
            info = f"Contact for {nurse.name}:\nEmail: {nurse.email}\nMobile: {nurse.mobile}\nAvailability: {nurse.availability_locations or 'N/A'}\nStatus: {nurse.status}"
            response_data['message'] = info
            response_data['buttons'] = [
                {'text': 'Back to Nurse Options', 'type': 'action', 'action': 'nurse_menu'},
                {'text': 'Back to Hospital', 'type': 'action', 'action': 'hospital_menu'}
            ]
            processed = True
        elif message_lower == 'list_nurses':
            state['context'] = 'waiting_nurse_selection'
            hospital = Hospital.query.get(state['current_entity']['hospital_id'])
            nurses = Nurse.query.filter_by(hospital_id=state['current_entity']['hospital_id']).all()
            numbered = '\n'.join([f"{i+1}. {n.name}" for i, n in enumerate(nurses)])
            response_data['message'] = f"Nurses at {hospital.name}:\n{numbered}\nType the number."
            state['current_list'] = [(n.id, n.name) for n in nurses]
            processed = True
        else:
            # AI fallback
            system_prompt = f"You are Harsh... Current nurse: {state['current_entity']['name']}. Answer about nursing services."
            messages = [{'role': 'system', 'content': system_prompt}]
            for h in session['chat_history'][-6:]:
                messages.append({'role': h['role'], 'content': h['content']})
            ai_response = call_openrouter(messages)
            response_data['message'] = ai_response
            processed = True
    # Fallback for unmatched states
    else:
        # Reset to start if invalid state
        state['context'] = 'start'
        response_data['message'] = "Let's start over. How can I help? Say 'hospitals available' for hospital info."
        processed = True
    if processed:
        # Append assistant response to history
        session['chat_history'].append({
            'role': 'assistant',
            'content': response_data['message'],
            'buttons': response_data['buttons']
        })
        session.modified = True
    return jsonify(response_data)
# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
if __name__ == '__main__':
    app.run(debug=True)