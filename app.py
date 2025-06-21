from flask import Flask, render_template, session, redirect, url_for, abort, request, flash
from flask_login import LoginManager, UserMixin, login_required, current_user, logout_user, login_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, validators
from models import db, User, Booking, Room

from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
application = app

app.config.from_object('config.Config')

db.init_app(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'auth'

csrf = CSRFProtect(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('База данных создана')

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[validators.InputRequired()])
    password = PasswordField('Пароль', validators=[validators.InputRequired()])
    remember = BooleanField('Запомнить меня')

class RegistrationForm(FlaskForm):
    username = StringField('Логин', [
        validators.Length(min=4, max=25),
        validators.InputRequired()
    ])
    email = StringField('Email', [
        validators.Email(),
        validators.InputRequired()
    ])
    full_name = StringField('ФИО', [
        validators.Length(min=5, max=50),
        validators.InputRequired()
    ])
    phone = StringField('Телефон', [
        validators.Length(min=11, max=15),
        validators.InputRequired(),
        validators.Regexp(r'^\+?[0-9]+$', message="Только цифры и знак +")
    ])
    password = PasswordField('Пароль', [
        validators.InputRequired(),
        validators.EqualTo('confirm_password', message='Пароли должны совпадать')
    ])
    confirm_password = PasswordField('Повторите пароль')

def calculate_nights(check_in, check_out):
    try:
        fmt = '%Y-%m-%d'
        nights = (datetime.strptime(check_out, fmt) - datetime.strptime(check_in, fmt)).days
        return max(nights, 1)
    except (ValueError, TypeError):
        return 0

def calculate_price(check_in, check_out):
    if 'room_price' not in session:
        return 0
    
    nights = calculate_nights(check_in, check_out)
    return session['room_price'] * nights

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(login=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Добро пожаловать, {user.login}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('auth.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        if User.query.filter_by(login=form.username.data).first():
            flash('Этот логин уже занят', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(phone=form.phone.data).first():
            flash('Этот телефон уже зарегистрирован', 'error')
            return redirect(url_for('register'))
        
        new_user = User(
            login=form.username.data,
            email=[form.email.data],
            fuo=form.full_name.data,
            phone=form.phone.data
        )
        new_user.set_password(form.password.data)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('auth'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('index'))

@app.route('/about-hotel')
def about_hotel():
    return render_template('about-hotel.html')

@app.route('/rooms')
def rooms():
    return render_template('rooms.html')

@app.route('/confirmation')
@login_required
def confirmation():
    required_keys = ['selected_room', 'selected_room_id', 'check_in', 'check_out']
    if not all(key in session for key in required_keys):
        flash('Пожалуйста, завершите процесс бронирования', 'warning')
        return redirect(url_for('rooms'))
    
    try:
        room = Room.query.get(session['selected_room_id'])
        if not room:
            flash('Выбранный номер не найден', 'error')
            return redirect(url_for('rooms'))
        
        booking_data = {
            'room_type': session['selected_room'],
            'room_name': room.name,
            'check_in': session['check_in'],
            'check_out': session['check_out'],
            'nights': calculate_nights(session['check_in'], session['check_out']),
            'total_price': calculate_price(session['check_in'], session['check_out']),
            'guests': session.get('guests', 1)
        }
        
        return render_template('confirmation.html', booking=booking_data)
    except Exception as e:
        app.logger.error(f'Ошибка при подготовке подтверждения: {str(e)}', exc_info=True)
        flash('Ошибка при подготовке данных бронирования', 'error')
        return redirect(url_for('rooms'))

@app.route('/confirm-booking', methods=['POST'])
@login_required
def confirm_booking():
    try:
        required_session_keys = ['selected_room', 'selected_room_id', 'check_in', 'check_out']
        if not all(key in session for key in required_session_keys):
            missing = [key for key in required_session_keys if key not in session]
            app.logger.error(f'Не хватает данных в сессии: {missing}')
            flash('Не все данные бронирования заполнены', 'error')
            return redirect(url_for('rooms'))

        check_in_date = datetime.strptime(session['check_in'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(session['check_out'], '%Y-%m-%d').date()

        if check_out_date <= check_in_date:
            flash('Дата выезда должна быть после даты заезда', 'error')
            return redirect(url_for('confirmation'))

        new_booking = Booking(
            user_id=current_user.id_user,
            room_id=session['selected_room_id'],
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests_count=session.get('guests', 1),
            total_price=calculate_price(session['check_in'], session['check_out']),
            is_active=True
        )

        db.session.add(new_booking)
        db.session.commit()

        for key in ['selected_room', 'selected_room_id', 'check_in', 'check_out', 'guests', 'room_price']:
            session.pop(key, None)

        flash('Бронирование успешно подтверждено! Подробности отправлены на email', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Ошибка при подтверждении бронирования: {str(e)}', exc_info=True)
        flash(f'Ошибка при подтверждении бронирования: {str(e)}', 'error')
        return redirect(url_for('confirmation'))

@app.route('/save-room-choice', methods=['POST'])
def save_room_choice():
    room_type = request.form.get('room-type')
    if not room_type:
        flash('Не выбран тип номера', 'error')
        return redirect(url_for('rooms'))
    
    try:
        room = Room.query.filter(Room.room_type.ilike(room_type)).first()
        
        if not room:
            flash(f'Номер типа "{room_type}" не найден в базе данных', 'error')
            return redirect(url_for('rooms'))
        
        session['selected_room'] = room.room_type
        session['selected_room_id'] = room.id_room
        session['room_price'] = room.price_per_night
        return redirect(url_for('calendar'))
    
    except Exception as e:
        app.logger.error(f'Ошибка при выборе номера: {str(e)}', exc_info=True)
        flash('Произошла ошибка при обработке вашего выбора', 'error')
        return redirect(url_for('rooms'))

@app.route('/calendar')
def calendar():
    if 'selected_room' not in session:
        flash('Сначала выберите тип номера', 'warning')
        return redirect(url_for('rooms'))
    return render_template('calendar.html')

@app.route('/process-booking', methods=['POST'])
def process_booking():
    try:
        from flask_wtf.csrf import validate_csrf
        validate_csrf(request.form.get('csrf_token'))
        
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests', 1)
        
        if not check_in or not check_out:
            flash('Укажите даты заезда и выезда', 'error')
            return redirect(url_for('calendar'))
        
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            if check_out_date <= check_in_date:
                flash('Дата выезда должна быть после даты заезда', 'error')
                return redirect(url_for('calendar'))
        except ValueError:
            flash('Некорректный формат даты', 'error')
            return redirect(url_for('calendar'))
        
        session['check_in'] = check_in
        session['check_out'] = check_out
        session['guests'] = int(guests)
        return redirect(url_for('confirmation'))
        
    except Exception as e:
        app.logger.error(f'Ошибка при обработке бронирования: {str(e)}', exc_info=True)
        flash('Ошибка при обработке данных. Пожалуйста, попробуйте снова.', 'error')
        return redirect(url_for('calendar'))

if __name__ == "__main__":
    app.run(debug=True)
