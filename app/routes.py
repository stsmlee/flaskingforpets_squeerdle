import json
import sqlite3
from argon2 import PasswordHasher
from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from wtforms.validators import Length, NoneOf, ValidationError, StopValidation
from app import app, forms
from app.pet_helper import pet_info
from flask_session import Session

pet_types_dict = pet_info.get_types_dict()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            # flash(f"Error in {field} field - {error}", 'error')
            flash(f"Error: {error}", 'error')

def register_user_db(username, password):
    username = username.lower()
    ph = PasswordHasher()
    hash = ph.hash(password)
    conn = get_db_connection()
    conn.execute('INSERT INTO users (username, password) VALUES (?,?)', (username,hash))
    flash(f'Successfully registered. Welcome {username}!', 'notice')
    conn.commit()
    conn.close()

def logged_in():
    if 'username' in session:
        return True
    return False

def get_user_id(username):
    username = username.lower()
    conn = get_db_connection()
    userid = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return userid['id']

def save_search(savename,params):
    conn = get_db_connection()
    conn.execute('INSERT INTO saves (savename, params, user_id) VALUES (?,?,?)', (savename, params, session['user id']))
    conn.commit()
    conn.close()

def save_results_db(results, savename):
    conn = get_db_connection()
    conn.execute('UPDATE saves SET results = ? WHERE savename = ? AND user_id = ?', (results, savename, session['user id']))
    conn.commit()
    conn.close()

def get_savenames():
    conn = get_db_connection()
    res = conn.execute('SELECT savename FROM saves WHERE user_id = ?', (session['user id'],)).fetchall()
    conn.close()
    results = [row['savename'] for row in res]
    return results

def get_params(savename):
    conn = get_db_connection()
    res = conn.execute('SELECT params FROM saves WHERE savename = ? AND user_id = ?', (savename, session['user id'])).fetchone()
    conn.close()
    return res[0]

def get_savenames_params():
    conn = get_db_connection()
    res = conn.execute('SELECT savename,params FROM saves WHERE user_id = ?', (session['user id'],)).fetchall()
    conn.close()
    names_params = {}
    for row in res:
        param_list = []
        savename = row['savename']
        params = json.loads(row['params'])
        for k, v in params.items():
            k = k.replace('_', ' ')
            if isinstance(v, str):
                v = v.replace(',', ', ')
            if v == 1 and k != 'distance':
                v = 'yes'            
            param_list.append(k + ': ' + str(v))
        names_params[savename] = ' | '.join(param_list).lower()
    return names_params

def clean_up_req_dels(formdata):
    req_dels = []
    for selected in formdata:
        name = ''
        for l in selected:
            if l == ':':
                break
            else:
                name += l
        req_dels.append(name)
    return req_dels

def delete_save(req_list):
    conn = get_db_connection()
    for savename in req_list:
        conn.execute('DELETE FROM saves WHERE user_id = ? AND savename = ?', (session['user id'], savename))
    conn.commit()
    conn.close()
    flash('Selected saved searches successfully cleared.', 'notice')

def check_savecount(form,field):
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT (*) FROM saves WHERE user_id = ?', (session['user id'],)).fetchone()
    conn.close()
    count = count[0]
    print(count)
    if count >= 20:
        raise StopValidation('You have reached the maximum number of saved searches (20), please go to \'Manage Your Account\' to make space for more.')

def refresh_token():
    pet_info.token = pet_info.get_token()
    pet_info.auth = "Bearer " + pet_info.token
    pet_info.header = {"Authorization": pet_info.auth}
    flash('Sorry for the delay, we had to refresh your session with Petfinder!', 'notice')
        
@app.route('/', methods=["GET", "POST"])
@app.route('/index', methods=["GET", "POST"])
def index():
    login_form = forms.LoginForm()
    reuse_form = forms.ReuseForm()
    if logged_in():  
        try:
            session['user id'] = get_user_id(session['username'])
        except:
            session.clear()
            return redirect(url_for('index'))
        res = get_savenames()
        reuse_form.savename.choices = res
        if reuse_form.validate_on_submit():
            payload = get_params(reuse_form.savename.data)
            payload = json.loads(payload)
            type = payload['type']
            return redirect(url_for('search_saved', payload=json.dumps(payload), type = type, page=1, savename = reuse_form.savename.data))   
        return render_template('index.html', pet_types_dict = pet_types_dict, re_form = reuse_form)
    if login_form.validate_on_submit():
        session['username'] = login_form.username.data
        flash("Login successful. Welcome back.", 'notice')
        return redirect(url_for('index'))
    else:
        flash_errors(login_form)  
    return render_template('index.html', pet_types_dict = pet_types_dict, form=login_form)

@app.route('/register', methods=["GET", "POST"])
def register():
    form = forms.RegisterForm()
    flash_errors(form)
    if form.validate_on_submit():
        register_user_db(form.username.data,form.password.data)
        session['username'] = form.username.data
        return redirect(url_for('index'))
    else:
        flash_errors(form)
    return render_template('register.html', form = form)

@app.route('/animals/<type>', methods=["GET", "POST"])
def animals(type):
    my_form = forms.FilterForm()
    my_form.breed1.choices = ['N/A'] + pet_types_dict[type]['Breeds']
    my_form.breed2.choices = my_form.breed1.choices
    my_form.color.choices = ['N/A'] + pet_types_dict[type]['Colors']
    my_form.coat.choices = ['N/A'] + pet_types_dict[type]['Coats']
    if logged_in():
        savenames = get_savenames()
        savestring = ', '.join(savenames)
        err_msg = 'Please make sure to use a unique savename, not any of these: ' + savestring
        my_form.savename.validators = [check_savecount, NoneOf(savenames, message=err_msg), Length(min=1, max=20)]
    if my_form.validate_on_submit():
        payload = pet_info.build_params(my_form.data, type)
        if my_form.savename.data:
            save_search(my_form.savename.data, json.dumps(payload))
            return redirect(url_for('search_saved', type=type, payload=json.dumps(payload), page=1, savename=my_form.savename.data))
        return redirect(url_for('search', type=type, payload=json.dumps(payload), page=1))
    elif logged_in() and my_form.savename.errors:
        flash_errors(my_form)
    return render_template('animal.html', form = my_form, type=type, login = logged_in())

@app.route('/animals/<type>/page<int:page>/<payload>/<savename>')
def search_saved(type,payload,page,savename):
    payload = json.loads(payload)
    payload = pet_info.return_the_slash(payload)
    payload['page'] = page
    res_json = pet_info.get_request(payload)
    if isinstance(res_json, int):
        if res_json == 401:
            refresh_token()
            return redirect(url_for('search_saved', type = type, payload = json.dumps(payload), page = page, savename = savename))
        flash(f'There was an issue with Petfinder, please try again later. Status code {str(res_json)}.', 'response error')
        return redirect(url_for('index'))
    if not res_json:
        return render_template('no_results.html', type=type)
    results = pet_info.save_results(res_json, saved_dict={})
    print(len(results))
    save_results_db(json.dumps(results), savename)
    return render_template('result.html', payload=json.dumps(payload),res= pet_info.parse_res_animals(res_json['animals']), type=type, pag = pet_info.parse_res_pag(res_json['pagination']))

@app.route('/animals/<type>/page<int:page>/<payload>')
def search(type,payload,page):
    payload = json.loads(payload)
    payload = pet_info.return_the_slash(payload)
    payload['page'] = page
    res_json = pet_info.get_request(payload)
    if isinstance(res_json, int):
        if res_json == 401:
            refresh_token()
            return redirect(url_for('search_saved', type = type, payload = json.dumps(payload), page = page))
        flash(f'There was an issue with Petfinder, please try again later. Status code {str(res_json)}.', 'response error')
        return redirect(url_for('index'))
    if not res_json:
        return render_template('no_results.html', type=type)
    return render_template('result.html', payload=json.dumps(payload),res= pet_info.parse_res_animals(res_json['animals']), type=type, pag = pet_info.parse_res_pag(res_json['pagination']))

@app.route('/whatsnews')
def check_updates():
    if get_savenames():
        results = pet_info.check_for_new_results(session['user id'])
        new_stuff = []
        for savename, result in results.items():
            if isinstance(result, int):
                flash(f'There was an issue with Petfinder, please try again later. Status code {str(result)}.', 'response error')
                return redirect(url_for('index'))
            else:
                new_stuff.append(savename)
        if new_stuff:
            for search in new_stuff:
                flash(f'{search} has new results!', 'notice')
        else:
            flash("Nothing new for you, I'm afraid. Maybe try a new search!", 'notice')
    else:
        flash('You actually don\'t have any saved searches right now.', 'notice')
    return redirect(request.referrer)   

@app.route('/deleteaccount')
def delete_account():
    return render_template('delete.html')

@app.route('/deleteaccount/confirm')
def confirm_delete():
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (session['user id'],))
    conn.commit()
    conn.close()
    session.clear()
    flash('Account successfully deleted.', 'notice')
    return redirect(url_for('index'))

@app.route('/manageaccount', methods=["GET", "POST"])
def manage_account():
    saved = get_savenames_params()
    if request.method == 'POST':
        req_list = request.form.getlist('savenames')
        delete_save(req_list)
        return redirect(url_for('manage_account'))
    else:
        return render_template('manage.html', saves=saved)

@app.route('/logout')
def logout():
    # session.pop('username', None)
    session.clear()
    flash('Successfully logged out.', 'notice')
    return redirect(url_for('index'))