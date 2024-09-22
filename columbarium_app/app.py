from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_type = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)  # Store in UTC
    time = db.Column(db.Time, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('homepage'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
        else:
            new_user = User(email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/')
def home():
    return render_template('LandingPage.html')

@app.route('/homepage')
@login_required
def homepage():
    return render_template('homepage.html')

@app.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if request.method == 'POST':
        appointment_type = request.form.get('appointment_type')
        date = request.form.get('selected_date')
        time = request.form.get('selected_time')

        # Convert to UTC before storing in the database
        local_tz = pytz.timezone('Asia/Singapore')  # User's local timezone
        naive_datetime = datetime.strptime(f"{date} {time}", '%Y-%m-%d %I:%M %p')
        local_datetime = local_tz.localize(naive_datetime)  # Make it timezone-aware
        utc_datetime = local_datetime.astimezone(pytz.utc)  # Convert to UTC

        new_appointment = Appointment(
            user_id=current_user.id,
            appointment_type=appointment_type,
            date=utc_datetime,  # Store as UTC in the database
            time=utc_datetime.time()  # Store time component in UTC
        )
        db.session.add(new_appointment)
        db.session.commit()

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('view_appointments'))

    return render_template('book_appointment.html')

@app.route('/view-appointments')
@login_required
def view_appointments():
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
    
    # Assume you want to display the appointment time in a specific timezone (e.g., Asia/Singapore)
    tz = pytz.timezone('Asia/Singapore')
    
    # Convert all appointment times from UTC to the local timezone
    for appointment in appointments:
        # Assuming appointment.date is stored in UTC
        utc_datetime = pytz.utc.localize(appointment.date)
        local_datetime = utc_datetime.astimezone(tz)  # Convert to local timezone
        
        # Update the appointment object with the adjusted timezone for display
        appointment.date = local_datetime.date()
        appointment.time = local_datetime.time()

    return render_template('view_appointments.html', appointments=appointments)

@app.route('/locate_niche')
@login_required
def locate_niche():
    niche_info = {
        'name': 'Sample Niche',
        'location': '123 Cemetery Lane, Section A, Row 5',
        'details': 'This is a sample niche location.',
        'directions': [
            'Enter through the main gate',
            'Turn right at the first intersection',
            'Continue straight for 100 meters',
            'The niche is located on your left in Section A, Row 5'
        ]
    }
    return render_template('map_directions.html', niche_info=niche_info)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Password reset instructions have been sent to your email.')
        else:
            flash('No account found with that email address.')
    return render_template('forgot_password.html')

@app.route('/appointment', methods=['GET', 'POST'])
@login_required
def appointment():
    if request.method == 'POST':
        appointment_type = request.form.get('appointment_type')
        date = request.form.get('selected_date')
        time = request.form.get('selected_time')
        
        # Convert string to datetime objects
        appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time, '%I:%M %p').time()
        
        new_appointment = Appointment(
            user_id=current_user.id,
            appointment_type=appointment_type,
            date=appointment_date,
            time=appointment_time
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Appointment booked successfully!"})
    
    return render_template('appointment.html')

def reset_appointment_table():
    with app.app_context():
        db.session.execute(text('DROP TABLE IF EXISTS appointment'))
        db.session.commit()
        db.create_all()
        print("Appointment table has been reset with the new schema.")

if __name__ == '__main__':
    reset_appointment_table()
    app.run(debug=True)
