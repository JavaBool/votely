from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, Election, Candidate
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from utils import send_otp, store_otp_in_session, verify_otp_in_session, get_ist_now

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():

    elections = Election.query.filter(Election.status != 'draft').order_by(Election.start_time.desc()).all()
    return render_template('public/index.html', elections=elections)

@public_bp.route('/election/<int:election_id>')
def election_details(election_id):
    election = Election.query.get_or_404(election_id)
    if election.status == 'draft':
        flash('This election is not public.', 'error')
        return redirect(url_for('public.index'))
    
    candidates = Candidate.query.filter_by(election_id=election_id, status='approved').all()
    return render_template('public/election_details.html', election=election, candidates=candidates)

@public_bp.route('/nominate/<int:election_id>', methods=['GET', 'POST'])
def nominate(election_id):
    election = Election.query.get_or_404(election_id)
    now = get_ist_now()
    
    if now < election.nomination_start or now > election.nomination_end:
        flash('Nominations are not currently open for this election.', 'error')
        return redirect(url_for('public.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        age = request.form.get('age')
        photo = request.files.get('photo')
        

        if Candidate.query.filter_by(election_id=election_id, email=email).first():
            flash('You have already nominated yourself for this election.', 'error')
            return redirect(url_for('public.index'))
            

        
        photo_path = None
        if photo and photo.filename != '' and election.config_photo != 0:
            filename = secure_filename(photo.filename)
            upload_dir = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
            os.makedirs(upload_dir, exist_ok=True)
            
            filename = f"{election_id}_{int(get_ist_now().timestamp())}_{filename}"
            photo.save(os.path.join(upload_dir, filename))
            photo_path = f"uploads/{filename}"
        

        candidate_age = None
        if age:
            try:
                candidate_age = int(age)
                if candidate_age < 0:
                     flash('Invalid age provided. Age cannot be negative.', 'error')
                     return redirect(url_for('public.nominate', election_id=election_id))

                if election.min_age > 0 and candidate_age < election.min_age:
                     flash(f'Nomination rejected: Minimum age requirement is {election.min_age}.', 'error')
                     return redirect(url_for('public.nominate', election_id=election_id))
            except ValueError:
                if election.config_age == 2:
                    flash('Invalid age provided.', 'error')
                    return redirect(url_for('public.nominate', election_id=election_id))

        candidate = Candidate(
            election_id=election_id,
            name=name,
            email=email,
            age=candidate_age,
            photo_path=photo_path,
            status='pending'
        )
        db.session.add(candidate)
        db.session.commit()
        
        flash('Nomination submitted successfully! Pending admin approval. You will receive an email update.', 'success')
        return redirect(url_for('public.index'))
        
    return render_template('public/nominate.html', election=election)

@public_bp.route('/vote/<int:election_id>/login', methods=['GET', 'POST'])
def vote_login(election_id):
    from models import Elector
    from flask import session
    from firebase_admin import auth
    from utils import verify_otp_in_session
    
    election = Election.query.get_or_404(election_id)
    now = get_ist_now()
    
    if now < election.start_time or now > election.end_time:
        flash('Voting is not currently active for this election.', 'error')
        return redirect(url_for('public.index'))

    if request.method == 'POST':

        id_token = request.form.get('idToken')
        if id_token:
            if not election.allow_phone_voting:
                flash('Phone voting is disabled for this election.', 'error')
                return redirect(url_for('public.vote_login', election_id=election_id))

            try:
                decoded_token = auth.verify_id_token(id_token)
                phone_number = decoded_token.get('phone_number')
                
                if not phone_number:
                    flash('Could not retrieve phone number from authentication.', 'error')
                    return redirect(url_for('public.vote_login', election_id=election_id))
                    
                elector = Elector.query.filter_by(election_id=election_id, phone=phone_number).first()
                
                if not elector:
                    flash(f'Phone {phone_number} is not registered for this election.', 'error')
                    return redirect(url_for('public.vote_login', election_id=election_id))

                if elector.status != 'approved':
                    flash('Your access request is pending approval or has been rejected.', 'error')
                    return redirect(url_for('public.vote_login', election_id=election_id))
                
                if elector.has_voted:
                    flash('You have already voted in this election.', 'warning')
                    return redirect(url_for('public.index'))
                    
                session['voter_elector_id'] = elector.id
                session['voter_election_id'] = election_id
                return redirect(url_for('public.ballot', election_id=election_id))
                
            except Exception as e:
                print(f"Firebase verification error: {e}")
                flash(f'Authentication failed: {str(e)}', 'error')
                return redirect(url_for('public.vote_login', election_id=election_id))


        email = request.form.get('email')
        otp = request.form.get('otp')
        
        if email and otp:
            # First verify OTP using session helper
            key = f"elector_otp_{email}"
            is_valid, msg = verify_otp_in_session(key, otp)
            
            if is_valid:
                elector = Elector.query.filter_by(election_id=election_id, email=email).first()
                if not elector:
                     flash('Email not found in voter list.', 'error')
                     return redirect(url_for('public.vote_login', election_id=election_id))
                
                if elector.status != 'approved':
                     flash('Your access request is pending approval or has been rejected.', 'error')
                     return redirect(url_for('public.vote_login', election_id=election_id))


                
                if elector.has_voted:
                    flash('You have already voted in this election.', 'warning')
                    return redirect(url_for('public.index'))
                 
                session['voter_elector_id'] = elector.id
                session['voter_election_id'] = election_id
                return redirect(url_for('public.ballot', election_id=election_id))
            else:
                 flash(msg, 'error')
                 return redirect(url_for('public.vote_login', election_id=election_id))
              
    return render_template('public/login.html', election=election)

@public_bp.route('/vote/<int:election_id>/send_otp', methods=['POST'])
def send_login_otp(election_id):
    from models import Elector
    from utils import send_otp, store_otp_in_session
    import random
    
    email = request.form.get('email')
    if not email:
        return {'success': False, 'message': 'Email is required'}, 400
        
    elector = Elector.query.filter_by(election_id=election_id, email=email).first()
    if not elector:
        return {'success': False, 'message': 'Email not registered for this election'}, 404
        
    otp = str(random.randint(100000, 999999))

    key = f"elector_otp_{email}"
    store_otp_in_session(key, otp)
    
    if send_otp(email, otp, purpose=f"Login for {elector.election.title}"):
        return {'success': True, 'message': 'OTP sent successfully'}
    else:
        return {'success': False, 'message': 'Failed to send OTP'}, 500

@public_bp.route('/vote/<int:election_id>/check_phone', methods=['POST'])
def check_phone(election_id):
    from models import Elector
    
    phone = request.json.get('phone')
    if not phone:
        return {'exists': False, 'message': 'Phone number is required'}, 400
        

    
    elector = Elector.query.filter_by(election_id=election_id, phone=phone).first()
    
    if elector:
        if elector.status != 'approved':
             return {'exists': False, 'message': 'Your access request is pending or rejected.'}
        if elector.has_voted:
             return {'exists': True, 'message': 'You have already voted.', 'voted': True}
             
        return {'exists': True, 'message': 'User found'}
    else:
        return {'exists': False, 'message': 'Phone number not found in voter list.'}

@public_bp.route('/vote/<int:election_id>/secret_login', methods=['GET', 'POST'])
def secret_vote_login(election_id):
    from models import Elector
    from flask import session
    
    election = Election.query.get_or_404(election_id)
    now = get_ist_now()
    
    if now < election.start_time or now > election.end_time:
         flash('Voting is not currently active.', 'error')

         return redirect(url_for('public.index'))
         
    if request.method == 'POST':
        name = request.form.get('name').strip()
        identifier = request.form.get('identifier').strip()
        code = request.form.get('code').strip()
        
        if not name or not identifier or not code:
            flash('All fields are required.', 'error')
            return render_template('public/secret_login.html', election=election)
            

        elector = None
        elector_phone = Elector.query.filter_by(election_id=election_id, phone=identifier, name=name, secret_code=code).first()
        if elector_phone and (election.allow_phone_voting or elector_phone.phone): 
            elector = elector_phone
        else:
            elector_email = Elector.query.filter_by(election_id=election_id, email=identifier, name=name, secret_code=code).first()
            if elector_email:
                elector = elector_email
        
        if elector:
             if elector.has_voted:
                    flash('You have already voted.', 'warning')
                    return redirect(url_for('public.index'))
             
             session['voter_elector_id'] = elector.id
             session['voter_election_id'] = election_id
             return redirect(url_for('public.ballot', election_id=election_id))
        else:
            flash('Invalid Details or Secret Code.', 'error')
            
    return render_template('public/secret_login.html', election=election)



@public_bp.route('/vote/<int:election_id>/ballot', methods=['GET', 'POST'])
def ballot(election_id):
    from flask import session
    from models import Elector, Vote
    
    elector_id = session.get('voter_elector_id')
    if not elector_id:
        return redirect(url_for('public.vote_login', election_id=election_id))
    
    elector = Elector.query.get(elector_id)
    if not elector or elector.election_id != election_id:
        session.pop('voter_elector_id', None)
        return redirect(url_for('public.vote_login', election_id=election_id))
        
    if elector.has_voted:
        flash('You have already voted.', 'warning')
        return redirect(url_for('public.index'))
        
    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        if candidate_id:
            # Create anonymous vote - NO elector_id linked
            vote = Vote(election_id=election_id, candidate_id=candidate_id)
            elector.has_voted = True
            
            db.session.add(vote)
            db.session.commit()
            
            session.pop('voter_elector_id', None)
            
            if elector.custom_success_msg:
                return render_template('public/custom_success.html', msg=elector.custom_success_msg)
                
            flash('Your vote has been cast successfully!', 'success')
            return redirect(url_for('public.index'))
        else:
            flash('Please select a candidate.', 'error')
            
            
    candidates = Candidate.query.filter_by(election_id=election_id, status='approved').all()
    nota_candidate = Candidate.query.filter_by(election_id=election_id, status='nota').first()
    
    election = Election.query.get(election_id)
    return render_template('public/ballot.html', election=election, candidates=candidates, nota=nota_candidate)
