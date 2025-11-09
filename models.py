
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(300))
    rent = db.Column(db.Float, default=0.0)

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    house = db.relationship('House', backref=db.backref('tenants', lazy=True))

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    type = db.Column(db.String(50))  # water, electricity, rent, other
    amount = db.Column(db.Float, default=0.0)
    note = db.Column(db.String(300))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    house = db.relationship('House', backref=db.backref('bills', lazy=True))

class Agreement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    content = db.Column(db.Text)
    start_date = db.Column(db.String(30))
    end_date = db.Column(db.String(30))
    house = db.relationship('House', backref=db.backref('agreement', uselist=False))

def init_db(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()
