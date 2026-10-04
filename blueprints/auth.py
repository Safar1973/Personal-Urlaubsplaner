"""
Auth Blueprint – Login, Logout, Passwort ändern
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Benutzer
from forms import LoginForm, PasswortAendernForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        benutzer = Benutzer.query.filter_by(
            benutzername=form.benutzername.data).first()
        if benutzer and benutzer.aktiv and \
                benutzer.passwort_pruefen(form.passwort.data):
            login_user(benutzer, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Willkommen zurück, {benutzer.mitarbeiter.vorname}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Ungültige Anmeldedaten oder Konto gesperrt.', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/passwort-aendern', methods=['GET', 'POST'])
@login_required
def passwort_aendern():
    form = PasswortAendernForm()
    if form.validate_on_submit():
        if current_user.passwort_pruefen(form.altes_passwort.data):
            current_user.passwort_setzen(form.neues_passwort.data)
            db.session.commit()
            flash('Passwort wurde erfolgreich geändert.', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Das alte Passwort ist nicht korrekt.', 'danger')
    return render_template('auth/passwort_aendern.html', form=form)
