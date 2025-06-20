from flask import Flask, render_template, session, redirect, url_for, abort, request, flash
from flask_login import LoginManager, UserMixin, login_required, current_user
from models import db, User

from datetime import datetime

app = Flask(__name__)
application = app

app.config.from_object('config.Config')

db.init_app(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'auth'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('База данных создана')

def calculate_nights(check_in, check_out):
    fmt = '%Y-%m-%d'
    nights = (datetime.strptime(check_out, fmt) - datetime.strptime(check_in, fmt)).days
    return nights

def calculate_price(room_type, check_in, check_out):
    prices = {
        'standard': 2500,
        'comfort': 3800,
        'luxury': 6200
    }
    nights = calculate_nights(check_in, check_out)
    return prices.get(room_type, 2500) * nights

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    if 'next' in session:
        next_page = session['next']
        session.pop('next', None)
        return redirect(next_page)
    return render_template('auth.html')

@app.route('/about-hotel')
def about_hotel():
    return render_template('about-hotel.html')


@app.route('/rooms')
def rooms():
    return render_template('rooms.html')

@app.route('/confirmation')
# @login_required
def confirmation():
    booking_data = {
        'room_type': session.get('selected_room', 'Люкс'),
        'check_in': session.get('check_in', '2023-12-01'),
        'check_out': session.get('check_out', '2023-12-07'),
        'nights': calculate_nights(session['check_in'], session['check_out']),
        'total_price': calculate_price(session['selected_room'], session['check_in'], session['check_out'])
    }
    return render_template('confirmation.html', booking=booking_data)

@app.route('/save-room-choice', methods=['POST'])
def save_room_choice():
    room_type = request.form.get('room-type')
    session['selected_room'] = room_type
    return redirect(url_for('calendar'))

@app.route('/calendar')
def calendar():
    if 'selected_room' not in session:
        flash('Сначала выберите тип номера', 'warning')
        return redirect(url_for('room'))
    return render_template('calendar.html')

@app.route('/process-booking', methods=['POST'])
def process_booking():
    from models import Booking, Room
    from datetime import datetime
    
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    room_type = session.get('selected_room')
    
    room = Room.query.filter(Room.name.contains([room_type])).first()
    
    if not room:
        flash('Номер не найден', 'error')
        return redirect(url_for('rooms'))

    new_booking = Booking(
        check_in_date=datetime.strptime(check_in, '%Y-%m-%d').date(),
        check_out_date=datetime.strptime(check_out, '%Y-%m-%d').date(),
        guests_count=2,
        total_price=calculate_price(room_type, check_in, check_out),
        user_id=current_user.id_user if current_user.is_authenticated else None,
        room_id=room.id_room
    )
    
    db.session.add(new_booking)
    db.session.commit()
    
    session['booking_id'] = new_booking.id_booking
    return redirect(url_for('confirmation'))

@app.route('/back-auth')
def back_auth():
    session['next'] = url_for('confirmation')
    return render_template('back-auth.html')

if __name__ == "__main__":
    app.run(debug=True)
