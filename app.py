from flask import Flask, render_template, session, redirect, url_for, abort, request, flash
from flask_login import LoginManager, UserMixin, login_required, current_user

from datetime import datetime

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'

class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    user = User()
    user.id = user_id
    return user

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
    session['check_in'] = request.form.get('check_in')
    session['check_out'] = request.form.get('check_out')
    
    return redirect(url_for('confirmation'))
    # if current_user.is_authenticated:
    #     return redirect(url_for('confirmation'))
    # else:
    #     return redirect(url_for('back_auth'))

@app.route('/back-auth')
def back_auth():
    session['next'] = url_for('confirmation')
    return render_template('back-auth.html')

if __name__ == "__main__":
    app.run(debug=True)
