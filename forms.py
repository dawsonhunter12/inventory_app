from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, FloatField, SelectField, FileField
from wtforms.validators import DataRequired, EqualTo, Email, Length, NumberRange, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()], render_kw={"autofocus": True})
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)], render_kw={"autofocus": True})
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class InventoryForm(FlaskForm):
    part_name = StringField('Part Name', validators=[DataRequired()], render_kw={"autofocus": True})
    description = TextAreaField('Description', validators=[Optional()])
    origin_partnumber = StringField('Origin Part Number', validators=[Optional()])
    mcmaster_carr_partnumber = StringField('McMaster-Carr Part Number', validators=[Optional()])
    cost = FloatField('Cost', validators=[Optional(), NumberRange(min=0)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=0)])
    min_on_hand = IntegerField('Min on Hand', validators=[DataRequired(), NumberRange(min=0)])
    location = StringField('Location', validators=[Optional()])
    manufacturer = StringField('Manufacturer', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Submit')

class SearchForm(FlaskForm):
    search_term = StringField('Search', validators=[Optional()], render_kw={"placeholder": "Search"})
    field = SelectField('Field', choices=[
        ('all', 'All Fields'),
        ('part_number', 'Part Number'),
        ('part_name', 'Part Name'),
        ('description', 'Description'),
        ('manufacturer', 'Manufacturer'),
    ], validators=[Optional()])
    submit = SubmitField('Search')

class ImportForm(FlaskForm):
    file = FileField('CSV File', validators=[DataRequired()])
    submit = SubmitField('Import')

class ScanForm(FlaskForm):
    part_number = IntegerField('Part Number', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit')
