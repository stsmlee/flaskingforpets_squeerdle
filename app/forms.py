import sqlite3
import requests
from argon2 import PasswordHasher
from flask import Flask, Markup
from flask_wtf import FlaskForm, Form
from wtforms import (BooleanField, IntegerField, PasswordField, RadioField,
                     SelectField, StringField,
                     SubmitField, HiddenField)
from wtforms.validators import (InputRequired, Length, NoneOf,
                                NumberRange, StopValidation, ValidationError, Optional, Regexp)
from app.pet_helper.squeerdle import valid_word, build_word
import re

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def username_check(form,field):
    username = form.username.data.lower()
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?',
                        (username,)).fetchone()
    conn.close()
    if user:
        raise StopValidation('This username is already in use. If it is yours, perhaps try to log in with it, or else use a unique username.')

def verify_user(form,field):
    username = form.username.data.lower()
    conn = get_db_connection()
    res = conn.execute('SELECT username FROM users WHERE username = ?', (username,)).fetchone()
    if res is None:
        raise StopValidation(Markup('Username does not exist, please double check your entry or <a href="/register">register a new account</a>.'))

def verify_friend(form,field):
    username = form.username.data.lower()
    conn = get_db_connection()
    res = conn.execute('SELECT username FROM users WHERE username = ?', (username,)).fetchone()
    if res is None:
        raise StopValidation(Markup('Username does not exist, please double check your entry or ask your buddy to <a href="/register">register a new account</a>.'))

def verify_password(form,field):
    ph = PasswordHasher()
    username = form.username.data.lower()
    password = form.password.data
    conn = get_db_connection()
    res = conn.execute('SELECT password FROM users WHERE username = ?', (username,)).fetchone()
    try:
        ph.verify(res['password'], password)
    except:
        raise ValidationError('Password does not match username entered.')

def update_something(form,field):
    a = form.nickname.data
    b = form.new_password.data
    if a or b:
        form.nickname.validators.append(Optional())
        form.new_password.validators.append(Optional())
    else:
        raise StopValidation('You have changed neither password nor nickname.')

def check_valid_word(form,field):
    word = field.data.upper()
    valid = valid_word(word)
    if not valid:
        raise StopValidation('Invalid word.')

def check_puzzle_exists(form, field):
    conn = get_db_connection()
    res = conn.execute("SELECT word, id FROM puzzles WHERE word = ?", (field.data.upper(),)).fetchone()
    conn.close()
    if res:
        raise StopValidation(f'{res["word"]}, puzzle id #{res["id"]}, already exists in our puzzle database.')

def custom_az_regexp(form, field):
    pattern = re.compile(r"^[A-Za-z]+$")
    good = pattern.match(field.data)
    if not good:
        raise StopValidation("No numbers, special characters, or accents allowed.")

def custom_savename_regexp(form, field):
    pattern = re.compile(r"^[A-Za-z0-9-_]*$")
    good = pattern.match(field.data)
    if not good:
        raise StopValidation("Only basic alphabet, numbers, hyphen, and underscore allowed.")

class ChangePasswordForm(FlaskForm):
    username = StringField('Username', validators= [InputRequired(), verify_user], render_kw= {'class': 'form_font'})
    nickname = StringField('New Nickname', validators= [update_something, Length(min=3, max=20)], render_kw= {'class': 'form_font'})
    password = PasswordField('Current Password', validators= [InputRequired(), verify_password], render_kw= {'class': 'form_font'})
    new_password =  PasswordField('New Password', validators= [update_something, Length(min=8, max=20)], render_kw= {'class': 'form_font'})
    submit = SubmitField('Save Changes',render_kw= {'class': 'submit_button'})

class ResultsPerPage(FlaskForm):
    limit = SelectField('Number of Results per Page', )

class LoginForm(FlaskForm):
    username = StringField('Username', validators= [InputRequired(), custom_savename_regexp,verify_user], render_kw= {'class': 'form_font', 'placeholder': 'Username'})
    password = PasswordField('Password', validators= [InputRequired(), verify_password], render_kw= {'class': 'form_font', 'placeholder': 'Password'})
    submit = SubmitField('Login',render_kw= {'class': 'submit_button'})

class RegisterForm(FlaskForm):
    username = StringField('Username', validators= [InputRequired(), Length(min=3, max=20), custom_savename_regexp, username_check], render_kw= {'class': 'form_font'})
    password = PasswordField('Password', validators= [InputRequired(), Length(min=8, max=20)], render_kw= {'class': 'form_font'})
    confirm_password = PasswordField('Confirm Password', validators= [InputRequired(), Length(min=8, max=20)], render_kw= {'class': 'form_font'})
    nickname = StringField('Nickname (Optional)', validators= [Length(min=3, max=20), Optional()], render_kw= {'class': 'form_font'})
    submit = SubmitField('Register', render_kw= {'class': 'submit_button'})
    
    def validate_on_submit(self):
        good = FlaskForm.validate(self)
        if not good:
            return False
        if self.password.data != self.confirm_password.data:
            self.confirm_password.errors.append('Password and confirm password fields must match.')
            return False
        return True


class ReuseForm(FlaskForm):
    savename = SelectField('Saved Searches', render_kw= {'class': 'form_font'})
    submit = SubmitField('Let\'s Go!', render_kw= {'class': 'submit_button'})

class FilterForm(FlaskForm):
    breed1 = SelectField('Breed #1', render_kw= {'class': 'form_font'})
    breed2 = SelectField('Breed #2', render_kw= {'class': 'form_font'})
    color = SelectField('Color', render_kw= {'class': 'form_font'})
    coat = SelectField('Coat', render_kw= {'class': 'form_font'})
    gender = SelectField('Gender', choices = ['N/A', 'Male', 'Female'], render_kw= {'class': 'form_font'})
    baby = BooleanField('Baby')   
    young = BooleanField('Young')
    adult = BooleanField('Adult')
    senior = BooleanField('Senior')
    small = BooleanField('Small')
    medium = BooleanField('Medium')
    large = BooleanField('Large')
    xlarge = BooleanField('X-Large')
    children = BooleanField('Good with Children')
    dogs = BooleanField('Good with Dogs')
    cats = BooleanField('Good with Cats')
    housetrained = BooleanField('Housetrained')
    # zipcode = StringField('Zipcode (Required)', default = '11101', validators = [InputRequired(), Length(min=5, max=5)], render_kw= {'class': 'form_font'})
    zipcode = StringField('Zipcode (Required)', validators = [InputRequired(), Length(min=5, max=5)], render_kw= {'class': 'form_font'})
    distance = IntegerField('Distance (Miles)', default = 30, validators = [NumberRange(min=0, max=500), InputRequired()], render_kw= {'class': 'form_font'})
    savename = StringField('Save Name', render_kw= {'class': 'form_font'})
    submit = SubmitField('Submit', render_kw= {'class': 'submit_button'})

class PuzzleForm(FlaskForm):
    l0 = StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row", 'autofocus':'true', 'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})
    l1 = StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row", 'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})
    l2 = StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row",  'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})
    l3= StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row", 'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})
    l4 = StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row", 'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})
    l5 = StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row", 'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})
    l6 = StringField(validators=[InputRequired(), Length(max=1), Regexp("[A-Za-z]", message="No special characters or accents allowed!")], render_kw = {'class':"guess_row", 'autocomplete':"off", 'onkeydown': "return /[a-z]/i.test(event.key)", 'oninvalid':"this.setCustomValidity('Must fill out every letter.')", 'onchange':"this.setCustomValidity('')"})

    def validate_on_submit(self):
        good = FlaskForm.validate(self)
        if not good:
            return False
        guess = build_word(self.data)
        if not valid_word(guess):
            self.l0.errors.append('Invalid word.')
            return False
        return True

class CreatePuzzleForm(FlaskForm):
    word = StringField('Your Word', validators = [InputRequired(), Length(min=5, max=7), custom_az_regexp, check_valid_word, check_puzzle_exists], render_kw= {'class': 'form_font', 'autocomplete':"off", 'placeholder': '5-7 characters'})
    submit = SubmitField('Submit', render_kw= {'class': 'submit_button'})

class SendPuzzleForm(FlaskForm):
    username = StringField('Username', validators = [InputRequired(), Length(min=3, max=20), verify_friend], render_kw= {'class': 'form_font', 'autocomplete':"off", 'placeholder': 'Username'})
    hidden_id = HiddenField()
    hidden_word = HiddenField()
    send = SubmitField('Send', render_kw= {'class': 'submit_button'})


