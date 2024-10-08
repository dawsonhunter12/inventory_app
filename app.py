from flask import Flask, render_template, request, redirect, url_for, flash, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User, Inventory
from forms import LoginForm, RegistrationForm, InventoryForm, SearchForm, ImportForm, ScanForm
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import os
import csv
import io
from io import StringIO
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/inventory_app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Inventory Application Startup')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize the database and create tables
with app.app_context():
    db.create_all()
    # Create an admin user if none exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('adminpass')  # Replace with a secure password
        db.session.add(admin)
        db.session.commit()
    app.logger.info('Database tables created and admin user initialized.')

# Context processor to inject 'now' into templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

# Error handlers
@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'500 Error: {error}')
    return render_template('500.html'), 500

# User authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            app.logger.info(f'User {user.username} logged in.')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            app.logger.warning(f'Failed login attempt for username {form.username.data}.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    app.logger.info(f'User {current_user.username} logged out.')
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if current_user.role != 'admin':
        abort(403)
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data, 
            email=form.email.data, 
            role='user'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User registered successfully!', 'success')
        app.logger.info(f'New user registered: {user.username}.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Home route
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# List Items with Pagination and Search
@app.route('/list_items', methods=['GET', 'POST'])
@login_required
def list_items():
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    items_query = Inventory.query

    if request.method == 'POST' and form.validate_on_submit():
        search_term = form.search_term.data
        field = form.field.data
        if search_term:
            if field == 'all':
                items_query = items_query.filter(
                    Inventory.part_name.ilike(f'%{search_term}%') |
                    Inventory.description.ilike(f'%{search_term}%') |
                    Inventory.manufacturer.ilike(f'%{search_term}%') |
                    Inventory.part_number.ilike(f'%{search_term}%')
                )
            else:
                items_query = items_query.filter(getattr(Inventory, field).ilike(f'%{search_term}%'))
    items = items_query.order_by(Inventory.part_number).paginate(
        page=page, per_page=10, error_out=False
    )
    next_url = url_for('list_items', page=items.next_num) if items.has_next else None
    prev_url = url_for('list_items', page=items.prev_num) if items.has_prev else None
    return render_template('list_items.html', items=items.items, next_url=next_url, prev_url=prev_url, form=form)

# Add New Item
@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if current_user.role != 'admin':
        abort(403)
    form = InventoryForm()
    if form.validate_on_submit():
        item = Inventory(
            part_name=form.part_name.data,
            description=form.description.data,
            origin_partnumber=form.origin_partnumber.data,
            mcmaster_carr_partnumber=form.mcmaster_carr_partnumber.data,
            cost=form.cost.data,
            quantity=form.quantity.data,
            min_on_hand=form.min_on_hand.data,
            location=form.location.data,
            manufacturer=form.manufacturer.data,
            notes=form.notes.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        app.logger.info(f'Item added by {current_user.username}: {item.part_number}')
        return redirect(url_for('list_items'))
    return render_template('add_item.html', form=form)

# Update Item
@app.route('/update_item/<int:part_number>', methods=['GET', 'POST'])
@login_required
def update_item(part_number):
    if current_user.role != 'admin':
        abort(403)
    item = Inventory.query.get_or_404(part_number)
    form = InventoryForm(obj=item)
    if form.validate_on_submit():
        form.populate_obj(item)
        db.session.commit()
        flash('Item updated successfully!', 'success')
        app.logger.info(f'Item updated by {current_user.username}: {item.part_number}')
        return redirect(url_for('list_items'))
    return render_template('update_item.html', form=form, item=item)

# Delete Item
@app.route('/delete_item/<int:part_number>', methods=['POST'])
@login_required
def delete_item(part_number):
    if current_user.role != 'admin':
        abort(403)
    item = Inventory.query.get_or_404(part_number)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    app.logger.info(f'Item deleted by {current_user.username}: {part_number}')
    return redirect(url_for('list_items'))

# Check Inventory Levels
@app.route('/check_inventory')
@login_required
def check_inventory():
    items = Inventory.query.filter(Inventory.quantity < Inventory.min_on_hand).all()
    return render_template('check_inventory.html', items=items)

# Scan In Parts
@app.route('/scan_in', methods=['GET', 'POST'])
@login_required
def scan_in():
    form = ScanForm()
    if form.validate_on_submit():
        part_number = form.part_number.data
        quantity = form.quantity.data

        item = Inventory.query.get(part_number)
        if item:
            item.quantity += quantity
            db.session.commit()
            flash(f'Added {quantity} units to part number {part_number}.', 'success')
            app.logger.info(f'{quantity} units added to {part_number} by {current_user.username}.')
        else:
            flash('Part number not found.', 'danger')
        return redirect(url_for('scan_in'))
    return render_template('scan_in.html', form=form)

# Scan Out Parts
@app.route('/scan_out', methods=['GET', 'POST'])
@login_required
def scan_out():
    form = ScanForm()
    if form.validate_on_submit():
        part_number = form.part_number.data
        quantity = form.quantity.data

        item = Inventory.query.get(part_number)
        if item:
            if item.quantity >= quantity:
                item.quantity -= quantity
                db.session.commit()
                flash(f'Removed {quantity} units from part number {part_number}.', 'success')
                app.logger.info(f'{quantity} units removed from {part_number} by {current_user.username}.')
            else:
                flash(f'Insufficient stock. Available quantity: {item.quantity}.', 'danger')
        else:
            flash('Part number not found.', 'danger')
        return redirect(url_for('scan_out'))
    return render_template('scan_out.html', form=form)

# Export Data as CSV
@app.route('/export_data')
@login_required
def export_data():
    if current_user.role != 'admin':
        abort(403)
    items = Inventory.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Part Number', 'Part Name', 'Description', 'Origin Part Number', 'McMaster-Carr Part Number',
                 'Cost', 'Quantity', 'Min on Hand', 'Location', 'Manufacturer', 'Notes'])
    for item in items:
        cw.writerow([item.part_number, item.part_name, item.description, item.origin_partnumber,
                     item.mcmaster_carr_partnumber, item.cost, item.quantity, item.min_on_hand,
                     item.location, item.manufacturer, item.notes])
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inventory_data.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

# Import Data from CSV
@app.route('/import_data', methods=['GET', 'POST'])
@login_required
def import_data():
    if current_user.role != 'admin':
        abort(403)
    form = ImportForm()
    if form.validate_on_submit():
        file = form.file.data
        if file and file.filename.endswith('.csv'):
            try:
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.reader(stream)
                next(csv_input)  # Skip header row
                for row in csv_input:
                    if len(row) != 11:
                        continue  # Skip rows with incorrect number of columns
                    item = Inventory(
                        part_number=int(row[0]) if row[0] else None,
                        part_name=row[1],
                        description=row[2],
                        origin_partnumber=row[3],
                        mcmaster_carr_partnumber=row[4],
                        cost=float(row[5]) if row[5] else None,
                        quantity=int(row[6]),
                        min_on_hand=int(row[7]),
                        location=row[8],
                        manufacturer=row[9],
                        notes=row[10]
                    )
                    existing_item = Inventory.query.get(item.part_number)
                    if existing_item:
                        # Update existing item
                        existing_item.part_name = item.part_name
                        existing_item.description = item.description
                        existing_item.origin_partnumber = item.origin_partnumber
                        existing_item.mcmaster_carr_partnumber = item.mcmaster_carr_partnumber
                        existing_item.cost = item.cost
                        existing_item.quantity = item.quantity
                        existing_item.min_on_hand = item.min_on_hand
                        existing_item.location = item.location
                        existing_item.manufacturer = item.manufacturer
                        existing_item.notes = item.notes
                    else:
                        # Add new item
                        db.session.add(item)
                db.session.commit()
                flash('Data imported successfully!', 'success')
                app.logger.info(f'Data imported by {current_user.username}.')
                return redirect(url_for('list_items'))
            except Exception as e:
                app.logger.error(f'Error importing data: {e}')
                flash('An error occurred while importing data.', 'danger')
                return redirect(url_for('import_data'))
        else:
            flash('Invalid file format. Please upload a CSV file.', 'danger')
    elif request.method == 'POST':
        flash('Invalid form submission.', 'danger')
    return render_template('import_data.html', form=form)

if __name__ == '__main__':
    app.run(debug=False)
