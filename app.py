# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rental.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Change this secret key in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-please-change')

db = SQLAlchemy(app)

# -----------------
# Models
# -----------------
class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    name = db.Column(db.String(120), nullable=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(300))
    rent = db.Column(db.Float, default=0.0)
    tenants = db.relationship('Tenant', backref='house', lazy=True)
    bills = db.relationship('Bill', backref='house', lazy=True)
    agreements = db.relationship('Agreement', backref='house', lazy=True)

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(160))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))  # water, electricity, rent, other
    amount = db.Column(db.Float, default=0.0)
    note = db.Column(db.String(300))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))

class Agreement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    start_date = db.Column(db.String(30))
    end_date = db.Column(db.String(30))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))

# -----------------
# Helpers
# -----------------
def logged_in_owner():
    owner_id = session.get('owner_id')
    if not owner_id:
        return None
    return Owner.query.get(owner_id)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not logged_in_owner():
            flash("Please log in to access that page.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

# -----------------
# Routes - Public
# -----------------
@app.route('/')
def index():
    houses = House.query.all()
    return render_template('index.html', houses=houses, owner=logged_in_owner())

@app.route('/house/<int:house_id>')
def house_detail(house_id):
    h = House.query.get_or_404(house_id)
    agreement = Agreement.query.filter_by(house_id=house_id).first()
    tenant = Tenant.query.filter_by(house_id=house_id).first()
    bills = Bill.query.filter_by(house_id=house_id).order_by(Bill.date.desc()).all()
    return render_template('house_detail.html', house=h, agreement=agreement, tenant=tenant, bills=bills, owner=logged_in_owner())

# -----------------
# Routes - Auth
# -----------------
@app.route('/register', methods=['GET','POST'])
def register():
    # Allow registration only if no owner exists (simple safety)
    existing = Owner.query.first()
    if existing:
        flash("Registration disabled: owner already created. Use login.", "info")
        return redirect(url_for('login'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        name = request.form.get('name','').strip()
        pw = request.form['password']
        if not email or not pw:
            flash("Email and password required.", "danger")
            return render_template('register.html')
        owner = Owner(email=email, name=name)
        owner.set_password(pw)
        db.session.add(owner)
        db.session.commit()
        flash("Owner account created. Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email'].strip().lower()
        pw = request.form['password']
        owner = Owner.query.filter_by(email=email).first()
        if owner and owner.check_password(pw):
            session['owner_id'] = owner.id
            flash("Logged in successfully.", "success")
            next_url = request.args.get('next') or url_for('owner_dashboard')
            return redirect(next_url)
        flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('owner_id', None)
    flash("Logged out.", "info")
    return redirect(url_for('index'))

# -----------------
# Routes - Owner (Protected)
# -----------------
@app.route('/owner')
@login_required
def owner_dashboard():
    houses = House.query.all()
    summaries = []
    for h in houses:
        bills = Bill.query.filter_by(house_id=h.id).all()
        total = sum(b.amount for b in bills)
        water = sum(b.amount for b in bills if b.type=='water')
        electric = sum(b.amount for b in bills if b.type=='electricity')
        tenant = Tenant.query.filter_by(house_id=h.id).first()
        agreement = Agreement.query.filter_by(house_id=h.id).first()
        summaries.append({'house':h, 'total':total, 'water':water, 'electric':electric, 'tenant':tenant, 'agreement':agreement})
    return render_template('owner_dashboard.html', summaries=summaries, owner=logged_in_owner())

@app.route('/owner/house/add', methods=['GET','POST'])
@login_required
def add_house():
    if request.method=='POST':
        name = request.form['name']
        address = request.form.get('address','')
        rent = float(request.form.get('rent') or 0)
        h = House(name=name, address=address, rent=rent)
        db.session.add(h); db.session.commit()
        flash("House added.", "success")
        return redirect(url_for('owner_dashboard'))
    return render_template('add_house.html')

@app.route('/owner/house/<int:house_id>')
@login_required
def owner_house_detail(house_id):
    return redirect(url_for('house_detail', house_id=house_id))

@app.route('/owner/house/<int:house_id>/tenant/add', methods=['GET','POST'])
@login_required
def add_tenant(house_id):
    if request.method=='POST':
        name = request.form['name']
        phone = request.form.get('phone','')
        email = request.form.get('email','')
        t = Tenant(name=name, phone=phone, email=email, house_id=house_id)
        db.session.add(t); db.session.commit()
        flash("Tenant added.", "success")
        return redirect(url_for('house_detail', house_id=house_id))
    return render_template('add_tenant.html', house_id=house_id)

@app.route('/owner/house/<int:house_id>/bill/add', methods=['GET','POST'])
@login_required
def add_bill(house_id):
    if request.method=='POST':
        type_ = request.form['type']
        amount = float(request.form.get('amount') or 0)
        note = request.form.get('note','')
        date = request.form.get('date') or None
        if date:
            try:
                date = datetime.strptime(date, '%Y-%m-%d')
            except:
                date = datetime.utcnow()
        else:
            date = datetime.utcnow()
        b = Bill(type=type_, amount=amount, note=note, date=date, house_id=house_id)
        db.session.add(b); db.session.commit()
        flash("Bill added.", "success")
        return redirect(url_for('house_detail', house_id=house_id))
    return render_template('add_bill.html', house_id=house_id)

@app.route('/owner/house/<int:house_id>/agreement/add', methods=['GET','POST'])
@login_required
def add_agreement(house_id):
    if request.method=='POST':
        start = request.form.get('start_date','')
        end = request.form.get('end_date','')
        content = request.form.get('content','')
        a = Agreement(content=content, start_date=start, end_date=end, house_id=house_id)
        db.session.add(a); db.session.commit()
        flash("Agreement saved.", "success")
        return redirect(url_for('house_detail', house_id=house_id))
    return render_template('add_agreement.html', house_id=house_id)

# -----------------
# App start
# -----------------
if __name__ == "__main__":
    # create DB
    with app.app_context():
        db.create_all()
    # run dev server
    app.run(debug=True)
