from flask import Flask, render_template, request, redirect, send_from_directory, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime
import os
from flask_cors import CORS
from fuzzywuzzy import process
from flask import url_for

# import fuzzyLogicFunction from fuzzyLogic

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
CORS(app)

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

#sample data 
deceased_data = {
    "John Doe": {"terrace": "A", "column": "B", "row": 3, "floor": 1, "death": "Jan 29, 2000", "deceased_name": "John Doe", "map": "map.gif"},
    "Jane Smith": {"terrace": "C", "column": "F", "row": 5, "floor": 2, "death": "Oct 12, 2020", "deceased_name": "Jane Smith", "map": "mapzz.gif"},
    "James Brown": {"terrace": "B", "column": "A", "row": 1, "floor": 3, "death": "Dec 17, 2015", "deceased_name": "James Brown"}
    }

def get_directions(terrace, column, row, floor):
    # Step-by-step directions based on input
    directions = []
    directions.append("Enter through the main gate")

    # Directions to the floor
    if floor == 1:
        directions.append("Go up to Floor 1")
    elif floor == 2:
        directions.append("Go up to Floor 2")
    elif floor == 3:
        directions.append("Go up to Floor 3")

    # Directions to the Terrace
    if terrace == "A":
        directions.append("Turn right at the first intersection")
    elif terrace == "B":
        directions.append("Turn left at the second intersection")
    elif terrace == "C":
        directions.append("Go straight and take the third left")
    elif terrace == "D":
        directions.append("Turn left at the fourth intersection")

    # Add distance guidance
    directions.append(f"Continue straight for {row * 10} meters")  # Assuming row defines distance

    # Final directions to the column and row
    directions.append(f"The niche is located on your left in Terrace {terrace}, Column {column}, Row {row}")
    

    return directions

@app.route('/locate_niche', methods=['POST'])
# @login_required
def locate_niche():
    data = request.json
    
    name = data.get('name')
    terrace = data.get('terrace')
    column = data.get('column')
    row = data.get('row')
    floor = data.get('floor')

    # Check if the user is searching by name
    death_date = None
    deceased_name = None

    if name:
        # Use fuzzy matching to find the closest match
        match, score = process.extractOne(name, deceased_data.keys())
        if score > 80:  # Threshold for a good match
            location = deceased_data[match]
            terrace = location["terrace"]
            column = location["column"]
            row = location["row"]
            floor = location["floor"]
            death_date = location["death"]
            deceased_name = location["deceased_name"]
            mapDisplay = [f"/larawan/{location['map']}"]  # Dynamically set the map path
        else:
            return jsonify({"error": "Name not found"}), 404

    if not (terrace and column and row and floor):
        return jsonify({"error": "Incomplete location information"}), 400 
    
    directions = get_directions(terrace, column, row, floor)
    nicheLocation = [terrace, column, row, floor]
    
    response = {
        "directions": directions,
        "death_date": death_date if death_date else None,
        "deceased_name": deceased_name if deceased_name else None,
        "nicheLocation": nicheLocation,
        "mapDisplay": mapDisplay,
    }

    return jsonify(response)
# para sa image no choice na e
@app.route('/larawan/<path:filename>')
def serve_larawan(filename):
    return send_from_directory('larawan', filename)



# test route
@app.route('/locate', methods=['GET'])
def locate():
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
