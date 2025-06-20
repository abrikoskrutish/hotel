from datetime import datetime
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id_user = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    user_photo = db.Column(db.LargeBinary)
    email = db.Column(db.ARRAY(db.String(50)))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='user', lazy=True)
    roles = db.relationship('Role', secondary='roles_users', backref='users')

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id_room = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.ARRAY(db.String(50)), nullable=False)
    description = db.Column(db.Text)
    capacity = db.Column(db.String)
    price_per_night = db.Column(db.Integer)
    
    bookings = db.relationship('Booking', backref='room', lazy=True)

class Booking(db.Model):
    __tablename__ = 'booking'
    
    id_booking = db.Column(db.Integer, primary_key=True)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    guests_count = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id_room'))

class Role(db.Model):
    __tablename__ = 'roles'
    
    id_roles = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.ARRAY(db.String(50)), nullable=False)
    description = db.Column(db.Text)

roles_users = db.Table('roles_users',
    db.Column('roles_id_roles', db.Integer, db.ForeignKey('roles.id_roles'), primary_key=True),
    db.Column('users_id_user', db.Integer, db.ForeignKey('users.id_user'), primary_key=True)
)