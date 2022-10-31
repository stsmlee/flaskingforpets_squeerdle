from email.mime import base
from app import forms, app
from flask import Flask, render_template, redirect, url_for, session
from flask_session import Session
import json
from app.pet_helper import pet_info
from app import forms

pet_types_dict = pet_info.get_types_dict()
param_dict = {}

def logged_in():
    if 'username' in session.keys():
        return True
    return False

def base_html():
    if logged_in():
        return 'base_logged_in.html'
    return 'base.html'

@app.route('/', methods=["GET", "POST"])
@app.route('/index', methods=["GET", "POST"])
def index():
    login_form = forms.LoginForm()
    if login_form.validate_on_submit():
        session['username'] = login_form.username.data
        return redirect(url_for('index'))
    if logged_in():
        return render_template('index.html', pet_types_dict = pet_types_dict, username=session['username'], base_html='base_logged_in.html')
    return render_template('index.html', pet_types_dict = pet_types_dict, form=login_form, base_html='base.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    # session.clear()
    return redirect(url_for('index'))

@app.route('/animals/<type>', methods=["GET", "POST"])
def animals(type):
    my_form = forms.FilterForm()
    my_form.breed1.choices = ['N/A'] + pet_types_dict[type]['Breeds']
    my_form.breed2.choices = my_form.breed1.choices
    my_form.color.choices = ['N/A'] + pet_types_dict[type]['Colors']
    my_form.coat.choices = ['N/A'] + pet_types_dict[type]['Coats']
    if my_form.validate_on_submit():
        payload = pet_info.build_params(my_form.data, type)
        if 'saved searches' not in session.keys():
            session['saved searches'] = {}
        if my_form.savename.data:
            session['saved searches'][my_form.savename.data] = [payload]
        return redirect(url_for('search', type=type, payload=json.dumps(payload), page=1))
    return render_template('animal.html', form = my_form, type=type, base_html = base_html(), login = logged_in())

@app.route('/animals/<type>/page<int:page>/<payload>')
def search(type,payload,page):
    payload = json.loads(payload)
    payload['page'] = page
    res_json = pet_info.get_request(payload)
    if not res_json:
        return render_template('no_results.html', type=type)
    return render_template('result.html', payload=json.dumps(payload),res= pet_info.parse_res_animals(res_json['animals']), type=type, pag = pet_info.parse_res_pag(res_json['pagination']), base_html=base_html())




