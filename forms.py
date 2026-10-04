"""
WTForms – alle Formulare der Anwendung
"""
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SelectField,
                     TextAreaField, DateField, FloatField, IntegerField,
                     SubmitField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo,
                                Optional, NumberRange, ValidationError)
from models import Benutzer, Rolle


# ─── Auth ─────────────────────────────────────────────────────────────────────
class LoginForm(FlaskForm):
    benutzername = StringField('Benutzername',
                               validators=[DataRequired(), Length(3, 80)])
    passwort = PasswordField('Passwort', validators=[DataRequired()])
    remember_me = BooleanField('Angemeldet bleiben')
    submit = SubmitField('Anmelden')


class PasswortAendernForm(FlaskForm):
    altes_passwort = PasswordField('Aktuelles Passwort',
                                   validators=[DataRequired()])
    neues_passwort = PasswordField('Neues Passwort',
                                   validators=[DataRequired(), Length(6, 128)])
    passwort_bestaetigen = PasswordField(
        'Neues Passwort bestätigen',
        validators=[DataRequired(),
                    EqualTo('neues_passwort', message='Passwörter stimmen nicht überein.')])
    submit = SubmitField('Passwort ändern')


# ─── Urlaubsantrag ────────────────────────────────────────────────────────────
class UrlaubsantragForm(FlaskForm):
    abwesenheitsart_id = SelectField('Abwesenheitsart', coerce=int,
                                     validators=[DataRequired()])
    datum_von = DateField('Von', validators=[DataRequired()])
    datum_bis = DateField('Bis', validators=[DataRequired()])
    kommentar = TextAreaField('Kommentar / Hinweis',
                              validators=[Optional(), Length(max=500)])
    submit = SubmitField('Antrag einreichen')


class AblehnenForm(FlaskForm):
    grund = TextAreaField('Ablehnungsgrund',
                          validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Antrag ablehnen')


# ─── Admin – Benutzer ─────────────────────────────────────────────────────────
class BenutzerForm(FlaskForm):
    benutzername = StringField('Benutzername',
                               validators=[DataRequired(), Length(3, 80)])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    vorname = StringField('Vorname', validators=[DataRequired(), Length(1, 80)])
    nachname = StringField('Nachname', validators=[DataRequired(), Length(1, 80)])
    personalnummer = StringField('Personalnummer', validators=[Optional(), Length(max=20)])
    eintrittsdatum = DateField('Eintrittsdatum', validators=[Optional()])
    telefon = StringField('Telefon', validators=[Optional(), Length(max=30)])
    position = StringField('Position', validators=[Optional(), Length(max=100)])
    abteilung_id = SelectField('Abteilung', coerce=int, validators=[Optional()])
    rolle = SelectField('Rolle', choices=Rolle.CHOICES, validators=[DataRequired()])
    aktiv = BooleanField('Konto aktiv', default=True)
    passwort = PasswordField('Passwort (leer lassen = nicht ändern)',
                             validators=[Optional(), Length(min=6, max=128)])
    submit = SubmitField('Speichern')

    def validate_benutzername(self, field):
        from flask import request as req
        benutzer_id = req.view_args.get('benutzer_id')
        b = Benutzer.query.filter_by(benutzername=field.data).first()
        if b and b.id != benutzer_id:
            raise ValidationError('Dieser Benutzername ist bereits vergeben.')

    def validate_email(self, field):
        from flask import request as req
        benutzer_id = req.view_args.get('benutzer_id')
        b = Benutzer.query.filter_by(email=field.data).first()
        if b and b.id != benutzer_id:
            raise ValidationError('Diese E-Mail-Adresse wird bereits verwendet.')


# ─── Admin – Stammdaten ───────────────────────────────────────────────────────
class AbteilungForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 100)])
    beschreibung = StringField('Beschreibung', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Speichern')


class MitarbeiterForm(FlaskForm):
    vorname = StringField('Vorname', validators=[DataRequired(), Length(1, 80)])
    nachname = StringField('Nachname', validators=[DataRequired(), Length(1, 80)])
    personalnummer = StringField('Personalnummer', validators=[Optional(), Length(max=20)])
    eintrittsdatum = DateField('Eintrittsdatum', validators=[Optional()])
    telefon = StringField('Telefon', validators=[Optional(), Length(max=30)])
    position = StringField('Position', validators=[Optional(), Length(max=100)])
    abteilung_id = SelectField('Abteilung', coerce=int, validators=[Optional()])
    submit = SubmitField('Speichern')


class AbwesenheitsartForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 80)])
    farbe = StringField('Farbe (Hex)', validators=[DataRequired(), Length(7, 7)],
                        default='#4A90D9')
    bezahlt = BooleanField('Bezahlt', default=True)
    zaehlt_als_urlaub = BooleanField('Zählt als Urlaub', default=True)
    submit = SubmitField('Speichern')


class FeiertagForm(FlaskForm):
    datum = DateField('Datum', validators=[DataRequired()])
    bezeichnung = StringField('Bezeichnung',
                              validators=[DataRequired(), Length(1, 100)])
    bundesland = StringField('Bundesland (leer = bundesweit)',
                             validators=[Optional(), Length(max=50)])
    submit = SubmitField('Speichern')


class KontingentForm(FlaskForm):
    gesamttage = FloatField('Gesamttage',
                            validators=[DataRequired(), NumberRange(0, 366)])
    uebertrag = FloatField('Übertrag aus Vorjahr',
                           validators=[Optional(), NumberRange(0, 366)],
                           default=0.0)
    submit = SubmitField('Speichern')
