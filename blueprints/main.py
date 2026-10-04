"""
Main Blueprint – Dashboard, Teamkalender, eigenes Profil
"""
from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import (Urlaubsantrag, Mitarbeiter, Urlaubskontingent,
                    AntragStatus, Feiertag)
from utils import resturlaub_berechnen, kontingent_sicherstellen
from extensions import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    heute = date.today()
    jahr = heute.year
    mitarbeiter = current_user.mitarbeiter

    # Kontingent sicherstellen
    kontingent_sicherstellen(mitarbeiter.id, jahr)
    urlaub_info = resturlaub_berechnen(mitarbeiter.id, jahr)

    # Letzte eigene Anträge
    meine_antraege = Urlaubsantrag.query.filter_by(
        mitarbeiter_id=mitarbeiter.id
    ).order_by(Urlaubsantrag.erstellt_am.desc()).limit(5).all()

    # Ausstehende Anträge (nur für Manager/Admin)
    ausstehende = []
    if current_user.ist_manager:
        if current_user.ist_admin:
            ausstehende = Urlaubsantrag.query.filter_by(
                status=AntragStatus.AUSSTEHEND
            ).order_by(Urlaubsantrag.erstellt_am.asc()).all()
        else:
            # Manager sieht nur seine Abteilung
            abteilung_id = mitarbeiter.abteilung_id
            ausstehende = Urlaubsantrag.query.join(
    Mitarbeiter,
    Urlaubsantrag.mitarbeiter_id == Mitarbeiter.id
).filter(
                Mitarbeiter.abteilung_id == abteilung_id,
                Urlaubsantrag.status == AntragStatus.AUSSTEHEND,
                Urlaubsantrag.mitarbeiter_id != mitarbeiter.id,
            ).order_by(Urlaubsantrag.erstellt_am.asc()).all()

    # Aktuelle Abwesenheiten im Team
    team_heute = Urlaubsantrag.query.join(Mitarbeiter).filter(
        Urlaubsantrag.status == AntragStatus.GENEHMIGT,
        Urlaubsantrag.datum_von <= heute,
        Urlaubsantrag.datum_bis >= heute,
    )
    if not current_user.ist_admin and mitarbeiter.abteilung_id:
        team_heute = team_heute.filter(
            Mitarbeiter.abteilung_id == mitarbeiter.abteilung_id)
    team_heute = team_heute.all()

    return render_template(
        'main/dashboard.html',
        urlaub_info=urlaub_info,
        meine_antraege=meine_antraege,
        ausstehende=ausstehende,
        team_heute=team_heute,
        heute=heute,
        jahr=jahr,
    )


@main_bp.route('/kalender')
@login_required
def kalender():
    heute = date.today()
    return render_template('main/kalender.html', heute=heute)


@main_bp.route('/kalender/daten')
@login_required
def kalender_daten():
    """JSON-Endpunkt für FullCalendar."""
    from flask import jsonify, request
    start = request.args.get('start', '')
    end = request.args.get('end', '')

    query = Urlaubsantrag.query.filter(
        Urlaubsantrag.status == AntragStatus.GENEHMIGT,
    )

    if not current_user.ist_admin and current_user.mitarbeiter.abteilung_id:
        query = query.join(Mitarbeiter).filter(
            Mitarbeiter.abteilung_id == current_user.mitarbeiter.abteilung_id)

    antraege = query.all()

    events = []
    for a in antraege:
        from datetime import timedelta
        events.append({
            'id': a.id,
            'title': (f'{a.mitarbeiter.vollname} – '
                      f'{a.abwesenheitsart.name}'),
            'start': a.datum_von.isoformat(),
            'end': (a.datum_bis + timedelta(days=1)).isoformat(),
            'color': a.abwesenheitsart.farbe,
            'extendedProps': {
                'mitarbeiter': a.mitarbeiter.vollname,
                'art': a.abwesenheitsart.name,
                'tage': a.anzahl_tage,
            }
        })

    # Feiertage
    feiertage = Feiertag.query.all()
    for f in feiertage:
        events.append({
            'id': f'feiertag-{f.id}',
            'title': f'🎉 {f.bezeichnung}',
            'start': f.datum.isoformat(),
            'allDay': True,
            'color': '#6c757d',
            'display': 'background',
        })

    return jsonify(events)


@main_bp.route('/profil')
@login_required
def profil():
    mitarbeiter = current_user.mitarbeiter
    heute = date.today()
    urlaub_info = resturlaub_berechnen(mitarbeiter.id, heute.year)
    antraege = Urlaubsantrag.query.filter_by(
        mitarbeiter_id=mitarbeiter.id
    ).order_by(Urlaubsantrag.datum_von.desc()).all()
    return render_template('main/profil.html', mitarbeiter=mitarbeiter,
                           urlaub_info=urlaub_info, antraege=antraege)
