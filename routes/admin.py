from flask import Blueprint, render_template, redirect, url_for, flash, request, session, make_response
import io
import csv
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Admin, Election, Candidate, Elector
from forms import ElectionForm, ChangePasswordForm, AddAdminForm, EditAdminForm, NewPasswordForm, ForgotPasswordForm, EditElectorForm
from datetime import datetime
from utils import send_otp, send_password_email, store_otp_in_session, verify_otp_in_session
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def restrict_access_if_force_change():
    if current_user.is_authenticated and current_user.is_force_change_password:

        allowed = ['admin.change_password', 'admin.logout', 'static']
        if request.endpoint and request.endpoint not in allowed:
            flash('You must change your password before proceeding.', 'warning')
            return redirect(url_for('admin.change_password'))

@admin_bp.route('/election/create', methods=['GET', 'POST'])
@login_required
def create_election():
    if not current_user.can_manage_elections:
        flash('Access denied. You do not have permission to manage elections.', 'error')
        return redirect(url_for('admin.dashboard'))
    form = ElectionForm()
    if form.validate_on_submit():

        if form.nomination_start.data >= form.nomination_end.data:
             flash('Nomination start time must be before nomination end time.', 'error')
        elif form.nomination_end.data >= form.start_time.data:
             flash('Election must start AFTER nominations end.', 'error')
        elif form.start_time.data >= form.end_time.data:
             flash('Election start time must be before end time.', 'error')
        else:
             election = Election(
                title=form.title.data,
                description=form.description.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                nomination_start=form.nomination_start.data,
                nomination_end=form.nomination_end.data,
                config_age=form.config_age.data,
                min_age=form.min_age.data if form.min_age.data else 0,
                config_photo=form.config_photo.data,
                allow_nota=form.allow_nota.data,
                allow_phone_voting=form.allow_phone_voting.data,
                status='draft'
             )
             db.session.add(election)
             db.session.commit()
             

             if election.allow_nota:
                 nota = Candidate(election_id=election.id, name="None of the Above", email="nota@system", status='nota')
                 db.session.add(nota)
                 db.session.commit()

             flash('Election created successfully!', 'success')
             return redirect(url_for('admin.dashboard'))
    return render_template('admin/election_form.html', form=form, title='Create Election')

@admin_bp.route('/election/<int:election_id>', methods=['GET'])
@login_required
def manage_election(election_id):
    election = Election.query.get_or_404(election_id)
    

    total_electors = Elector.query.filter_by(election_id=election_id, status='approved').count()
    votes_casted = Elector.query.filter_by(election_id=election_id, has_voted=True).count()
    
    return render_template('admin/manage_election.html', election=election, total_electors=total_electors, votes_casted=votes_casted)

@admin_bp.route('/election/<int:election_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_election(election_id):
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    election = Election.query.get_or_404(election_id)
    form = ElectionForm(obj=election)
    
    if form.validate_on_submit():

        if form.nomination_start.data >= form.nomination_end.data:
             flash('Nomination start time must be before nomination end time.', 'error')
        elif form.nomination_end.data >= form.start_time.data:
             flash('Election must start AFTER nominations end.', 'error')
        elif form.start_time.data >= form.end_time.data:
             flash('Election start time must be before end time.', 'error')
        else:
             election.title = form.title.data
             election.description = form.description.data
             election.start_time = form.start_time.data
             election.end_time = form.end_time.data
             election.nomination_start = form.nomination_start.data
             election.nomination_end = form.nomination_end.data
             election.config_age = form.config_age.data
             election.min_age = form.min_age.data if form.min_age.data else 0
             election.config_photo = form.config_photo.data
             election.allow_nota = form.allow_nota.data
             election.allow_phone_voting = form.allow_phone_voting.data
             

             nota_candidate = Candidate.query.filter_by(election_id=election.id, status='nota').first()
             
             if election.allow_nota and not nota_candidate:
                 nota = Candidate(election_id=election.id, name="None of the Above", email="nota@system", status='nota')
                 db.session.add(nota)
             elif not election.allow_nota and nota_candidate:
                 db.session.delete(nota_candidate)
             

             now = datetime.now()
             if election.status == 'completed' and election.end_time > now:
                 election.status = 'active'
                 flash('Election reactivated because end time was extended.', 'info')
             elif election.status == 'active' and election.end_time <= now:
                 election.status = 'completed'
                 flash('Election marked as completed because end time is in the past.', 'info')


             if election.show_results:
                 election.show_results = False
                 flash('Election results have been unpublished due to modifications.', 'warning')
             
             db.session.commit()
             flash('Election updated successfully.', 'success')
             return redirect(url_for('admin.manage_election', election_id=election.id))
             
    return render_template('admin/election_form.html', form=form, title='Edit Election')


@admin_bp.route('/candidate/<int:candidate_id>/approve')
@login_required
def approve_candidate(candidate_id):
    from utils import send_notification_email
    candidate = Candidate.query.get_or_404(candidate_id)
    candidate.status = 'approved'
    db.session.commit()
    

    if candidate.email:
        subject = f"Nomination Approved: {candidate.election.title}"
        body = f"Dear {candidate.name},\n\nCongratulations! Your nomination for '{candidate.election.title}' has been approved. You are now an official candidate.\n\nGood luck!"
        send_notification_email(candidate.email, subject, body)
        
    flash(f'{candidate.name} approved. Notification sent.', 'success')
    return redirect(url_for('admin.manage_election', election_id=candidate.election_id))

@admin_bp.route('/candidate/<int:candidate_id>/reject')
@login_required
def reject_candidate(candidate_id):
    from utils import send_notification_email
    candidate = Candidate.query.get_or_404(candidate_id)
    candidate.status = 'rejected'
    db.session.commit()
    

    if candidate.email:
        subject = f"Nomination Update: {candidate.election.title}"
        body = f"Dear {candidate.name},\n\nWe regret to inform you that your nomination for '{candidate.election.title}' has been rejected or withdrawn.\n\nIf you have questions, please contact the administration."
        send_notification_email(candidate.email, subject, body)
        
    flash(f'{candidate.name} rejected. Notification sent.', 'success')
    return redirect(url_for('admin.manage_election', election_id=candidate.election_id))

@admin_bp.route('/election/<int:election_id>/add_elector', methods=['POST'])
@login_required
def add_elector(election_id):
    import random
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
    phone = request.form.get('phone')
    email = request.form.get('email')
    name = request.form.get('name')
    
    if not phone and not email:
        flash('Either Phone or Email is required.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))

    if name:
        # Check duplicates
        if phone and Elector.query.filter_by(election_id=election_id, phone=phone).first():
            flash('Elector with this phone number already exists.', 'error')
        elif email and Elector.query.filter_by(election_id=election_id, email=email).first():
            flash('Elector with this email already exists.', 'error')
        else:
            secret_code = str(random.randint(100000, 999999))
            elector = Elector(election_id=election_id, phone=phone, email=email, name=name, secret_code=secret_code)
            db.session.add(elector)
            db.session.commit()
            flash('Elector added.', 'success')
    else:
        flash('Name is required.', 'error')
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/import_electors', methods=['POST'])
@login_required
def import_electors(election_id):
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
    if file:
        import csv
        import io
        import random
        
        def width_safe(row, idx):
            return idx < len(row) and row[idx].strip()

        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        csv_input = csv.reader(stream)
        count = 0
        skipped = 0
        
        # Determine if header exists and map columns
        rows = list(csv_input)
        if not rows:
            flash('Empty file', 'error')
            return redirect(url_for('admin.manage_election', election_id=election_id))
            
        header = [h.lower().strip() for h in rows[0]]
        
        # Default indices
        phone_idx = 0
        email_idx = 1
        name_idx = 2
        
        has_header = False
        

        try:
            # Find indices if headers exist
            p_idx = -1
            e_idx = -1
            n_idx = -1
            
            for i, col in enumerate(header):
                if 'phone' in col or 'mobile' in col:
                    p_idx = i
                elif 'email' in col:
                    e_idx = i
                elif 'name' in col:
                    n_idx = i
            

                name_idx = n_idx
                has_header = True
                if p_idx != -1: phone_idx = p_idx
                if e_idx != -1: email_idx = e_idx
                

        except:
            pass
            
        start_index = 1 if has_header else 0
        # Fallback check
        if not has_header and len(rows[0]) >= 3:
             if 'phone' in header[0] or 'email' in header[1] or 'name' in header[2]:
                 start_index = 1

        for row in rows[start_index:]:
            # Ensure row is long enough for the max index we need
            max_idx = max(phone_idx, email_idx, name_idx)
            if len(row) > max_idx:
                phone = row[phone_idx].strip() if width_safe(row, phone_idx) else None
                email = row[email_idx].strip() if width_safe(row, email_idx) else None
                name = row[name_idx].strip() if width_safe(row, name_idx) else None
                

                if has_header:
                     if p_idx == -1: phone = None
                     else: phone = row[p_idx].strip() if width_safe(row, p_idx) else None
                     
                     if e_idx == -1: email = None 
                     else: email = row[e_idx].strip() if width_safe(row, e_idx) else None
                
                if (phone or email) and name:
                    # Check duplicate
                    dup = False
                    if phone and Elector.query.filter_by(election_id=election_id, phone=phone).first():
                        dup = True
                    if email and Elector.query.filter_by(election_id=election_id, email=email).first():
                        dup = True
                        
                    if not dup:
                        secret_code = str(random.randint(100000, 999999))
                        db.session.add(Elector(election_id=election_id, phone=phone, email=email, name=name, secret_code=secret_code))
                        count += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        db.session.commit()
        if skipped > 0:
             flash(f'Imported {count} electors. Skipped {skipped} rows (duplicates or missing data).', 'warning')
        else:
            flash(f'Imported {count} electors.', 'success')
        
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/publish', methods=['POST'])
@login_required
def publish_election(election_id):
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    election = Election.query.get_or_404(election_id)
    if election.status == 'draft':
        election.status = 'active'
        db.session.commit()
        flash('Election published! It is now visible to the public.', 'success')
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/end', methods=['POST'])
@login_required
def end_election(election_id):
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    election = Election.query.get_or_404(election_id)
    if election.status == 'active':
        election.status = 'completed'
        election.end_time = datetime.now()
        db.session.commit()
        flash('Election marked as completed.', 'success')
    return redirect(url_for('admin.manage_election', election_id=election_id))

    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/start_nominations', methods=['POST'])
@login_required
def start_nominations_now(election_id):
    from datetime import timedelta
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    election = Election.query.get_or_404(election_id)
    now = datetime.now()
    
    minutes = int(request.form.get('minutes', 5))
    
    if election.nomination_start > now:
        election.nomination_start = now
        election.nomination_end = now + timedelta(minutes=minutes)
        db.session.commit()
        flash(f'Nominations started immediately for {minutes} minutes.', 'success')
        

        if election.nomination_end >= election.start_time:
             flash("WARNING: Nomination period overlaps with scheduled voting start. Automatic start disabled. You must click 'Start Voting Now' to begin election.", 'warning')
             
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/end_nominations', methods=['POST'])
@login_required
def end_nominations_now(election_id):
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    election = Election.query.get_or_404(election_id)
    now = datetime.now()

    if election.nomination_start <= now and election.nomination_end > now:
        election.nomination_end = now
        db.session.commit()
        flash('Nominations ended immediately.', 'success')
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/start_voting', methods=['POST'])
@login_required
def start_voting_now(election_id):
    from datetime import timedelta
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    election = Election.query.get_or_404(election_id)
    now = datetime.now()
    
    minutes = int(request.form.get('minutes', 60))
    
    if election.nomination_end <= now:
        election.start_time = now
        election.end_time = now + timedelta(minutes=minutes)
        if election.status == 'draft':
            election.status = 'active'
        db.session.commit()
        flash(f'Voting started immediately for {minutes} minutes.', 'success')
    else:
        flash('Cannot start voting. Ensure nominations have ended.', 'warning')
        
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/delete', methods=['POST'])
@login_required
def delete_election(election_id):
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    election = Election.query.get_or_404(election_id)
    

    otp = str(random.randint(100000, 999999))
    session['delete_election_id'] = election.id

    store_otp_in_session('delete_election_otp', otp)
    
    send_otp(current_user.email, otp, purpose=f"Deletion of '{election.title}'")
    flash(f'OTP sent to {current_user.email} to confirm deletion.', 'info')
    return redirect(url_for('admin.verify_delete_election_otp'))

@admin_bp.route('/election/verify_delete', methods=['GET', 'POST'])
@login_required
def verify_delete_election_otp():
    if 'delete_election_id' not in session:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('delete_election_otp', otp)
        
        if is_valid:
            election_id = session.get('delete_election_id')
            election = Election.query.get(election_id)
            
            if election:
                db.session.delete(election)
                db.session.commit()
                flash('Election deleted successfully.', 'success')
            else:
                 flash('Election not found (already deleted?).', 'error')
            
            session.pop('delete_election_id', None)
            return redirect(url_for('admin.dashboard'))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_otp_generic.html', title="Confirm Delete Election")

@admin_bp.route('/elector/<int:elector_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_elector(elector_id):
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    elector = Elector.query.get_or_404(elector_id)
    form = EditElectorForm(obj=elector)
    
    if form.validate_on_submit():

        phone = form.phone.data
        email = form.email.data
        elector.custom_success_msg = form.custom_success_msg.data
        
        if not phone and not email:
            flash('At least one of Phone or Email is required.', 'error')
            return render_template('admin/edit_elector.html', form=form, elector=elector)


        if phone:
            existing = Elector.query.filter_by(election_id=elector.election_id, phone=phone).first()
            if existing and existing.id != elector.id:
                flash('This phone number is already registered for this election.', 'error')
                return render_template('admin/edit_elector.html', form=form, elector=elector)
        

        if email:
            existing = Elector.query.filter_by(election_id=elector.election_id, email=email).first()
            if existing and existing.id != elector.id:
                flash('This email is already registered for this election.', 'error')
                return render_template('admin/edit_elector.html', form=form, elector=elector)

        elector.name = form.name.data
        elector.phone = phone
        elector.email = email
        db.session.commit()
        flash('Elector updated successfully.', 'success')
        return redirect(url_for('admin.manage_election', election_id=elector.election_id))
            
    return render_template('admin/edit_elector.html', form=form, elector=elector)

@admin_bp.route('/elector/<int:elector_id>/delete', methods=['POST'])
@login_required
def delete_elector(elector_id):
    from models import Vote
    elector = Elector.query.get_or_404(elector_id)
    if elector.election.status == 'completed':
        flash('Cannot delete electors from a completed election.', 'error')
        return redirect(url_for('admin.manage_election', election_id=elector.election_id))
        
    election_id = elector.election_id
    

    Vote.query.filter_by(elector_id=elector.id).delete()
        
    db.session.delete(elector)
    db.session.commit()
    flash('Elector removed.', 'success')
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/delete_electors', methods=['POST'])
@login_required
def delete_electors_bulk(election_id):
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    election = Election.query.get_or_404(election_id)
    
    if election.status == 'completed':
        flash('Cannot delete electors from a completed election.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    elector_ids = request.form.getlist('elector_ids')
    if not elector_ids:
        flash('No electors selected.', 'warning')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    from models import Vote
    deleted_count = 0
    


    valid_electors = Elector.query.filter(Elector.election_id == election_id, Elector.id.in_(elector_ids)).all()
    
    for elector in valid_electors:
        Vote.query.filter_by(elector_id=elector.id).delete()
        db.session.delete(elector)
        deleted_count += 1
        
    db.session.commit()
    flash(f'{deleted_count} electors deleted.', 'success')
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/get_secret_code', methods=['POST'])
@login_required
def get_secret_code(election_id):
    if not current_user.is_super_admin:
        flash('Access denied. Super Admin only.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    name = request.form.get('name', '').strip()
    identifier = request.form.get('identifier', '').strip()
    action = request.form.get('action', 'get')
    
    if not name or not identifier:
        flash('Name and Phone/Email are required.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
    
    elector = Elector.query.filter_by(election_id=election_id, phone=identifier, name=name).first()
    if not elector:
        elector = Elector.query.filter_by(election_id=election_id, email=identifier, name=name).first()
            
    if elector:
        if action == 'reset':
            import random
            new_code = str(random.randint(100000, 999999))
            elector.secret_code = new_code
            db.session.commit()
            flash(f'Secret Code RESET successfully. New Code for {elector.name}: {elector.secret_code}', 'success')
        else:
            flash(f'Secret Code for {elector.name}: {elector.secret_code}', 'success')
    else:
        flash('Elector not found with these EXACT details.', 'error')
        
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/elector/<int:elector_id>/reset_vote', methods=['POST'])
@login_required
def reset_vote(elector_id):
    from models import Vote
    elector = Elector.query.get_or_404(elector_id)
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.manage_election', election_id=elector.election_id))

    if not elector.has_voted:
        flash('Elector has not voted yet.', 'warning')
        return redirect(url_for('admin.manage_election', election_id=elector.election_id))

    if elector.election.status == 'completed':
        flash('Cannot reset votes for a completed election.', 'error')
        return redirect(url_for('admin.manage_election', election_id=elector.election_id))
        
    # Initiate OTP flow
    otp = str(random.randint(100000, 999999))
    session['reset_vote_elector_id'] = elector.id

    store_otp_in_session('reset_vote_otp', otp)
    
    send_otp(current_user.email, otp, purpose="Vote Reset")
    flash(f'OTP sent to {current_user.email} to confirm vote reset.', 'info')
    return redirect(url_for('admin.verify_reset_vote_otp'))

@admin_bp.route('/election/verify_reset_vote', methods=['GET', 'POST'])
@login_required
def verify_reset_vote_otp():
    if 'reset_vote_elector_id' not in session:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        if otp == session.get('reset_vote_otp'):
            from models import Vote
            elector_id = session.get('reset_vote_elector_id')
            elector = Elector.query.get(elector_id)
            
            if elector and elector.has_voted:

                vote = Vote.query.filter_by(elector_id=elector.id, election_id=elector.election_id).first()
                if vote:
                    db.session.delete(vote)
                    elector.has_voted = False
                    db.session.commit()
                    if elector.election.allow_phone_voting:
                        display_identity = f"{elector.phone or 'N/A'}"
                        if elector.email:
                            display_identity += f" / {elector.email}"
                        flash(f'Vote for {display_identity} has been reset.', 'success')
                    else:
                        flash(f'Vote for {elector.email or elector.phone} has been reset.', 'success')
                else:
                    flash('Could not find vote record to delete.', 'error')
            
            session.pop('reset_vote_elector_id', None)
            session.pop('reset_vote_otp', None)
            
            return redirect(url_for('admin.manage_election', election_id=elector.election_id if elector else 1))
        else:
            flash('Invalid OTP', 'error')
            
    return render_template('admin/verify_otp_generic.html', title="Confirm Vote Reset")

@admin_bp.route('/election/<int:election_id>/release', methods=['POST'])
@login_required
def initiate_release_results(election_id):
    if not current_user.can_manage_elections:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    election = Election.query.get_or_404(election_id)
    
    if election.status != 'completed':
        flash('Cannot release results. Election is not completed.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    if election.show_results:
        flash('Results are already released.', 'warning')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    otp = str(random.randint(100000, 999999))
    session['release_election_id'] = election.id
    store_otp_in_session('release_otp', otp)
    
    send_otp(current_user.email, otp, purpose="Result Release")
    flash(f'OTP sent to {current_user.email} to confirm result release.', 'info')
    return redirect(url_for('admin.verify_release_results_otp'))

@admin_bp.route('/election/verify_release', methods=['GET', 'POST'])
@login_required
def verify_release_results_otp():
    if 'release_election_id' not in session:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('release_otp', otp)
        
        if is_valid:
            election_id = session.get('release_election_id')
            election = Election.query.get(election_id)
            
            if election:
                election.show_results = True
                db.session.commit()
                

                try:
                    from models import Candidate, Admin, Vote
                    from utils import send_notification_email
                    


                    candidates = Candidate.query.filter_by(election_id=election.id).all()
                    
                    results = []
                    for cand in candidates:
                        count = Vote.query.filter_by(candidate_id=cand.id).count()
                        results.append({'name': cand.name, 'votes': count})
                    
                    results.sort(key=lambda x: x['votes'], reverse=True)
                    
                    electors = Elector.query.filter_by(election_id=election.id).all()
                    voted_list = [e for e in electors if e.has_voted]
                    not_voted_list = [e for e in electors if not e.has_voted]
                    
                    def build_elector_rows(elector_list, show_phone):
                        rows = ""
                        for e in elector_list:
                            phone_cell = f"<td style='padding:8px; border:1px solid #ddd;'>{e.phone or '-'}</td>" if show_phone else ""
                            rows += f"<tr><td style='padding:8px; border:1px solid #ddd;'>{e.name}</td><td style='padding:8px; border:1px solid #ddd;'>{e.email or '-'}</td>{phone_cell}</tr>"
                        return rows

                    show_phone = election.allow_phone_voting
                    phone_header = "<th style='padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Phone</th>" if show_phone else ""
                    
                    html_body = f"""
                    <h2 style="color: #333;">Election Results: {election.title}</h2>
                    <p>Results have been officially released.</p>
                    
                    <h3 style="border-bottom: 2px solid #5a5a5a; padding-bottom: 5px;">Rank List</h3>
                    <table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th style="padding:12px; border:1px solid #ddd; text-align:left;">Rank</th>
                                <th style="padding:12px; border:1px solid #ddd; text-align:left;">Candidate</th>
                                <th style="padding:12px; border:1px solid #ddd; text-align:left;">Votes</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    
                    for idx, res in enumerate(results, 1):
                        is_winner = "font-weight:bold; background-color:#e8f5e9;" if idx == 1 else ""
                        html_body += f"<tr style='{is_winner}'><td style='padding:8px; border:1px solid #ddd;'>{idx}</td><td style='padding:8px; border:1px solid #ddd;'>{res['name']}</td><td style='padding:8px; border:1px solid #ddd;'>{res['votes']}</td></tr>"
                    
                    html_body += """
                        </tbody>
                    </table>
                    
                    <h3 style="border-bottom: 2px solid #28a745; padding-bottom: 5px; color: #28a745;">Voted Electors</h3>
                    <table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr>
                                <th style="padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Name</th>
                                <th style="padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Email</th>
                                {phone_header}
                            </tr>
                        </thead>
                        <tbody>
                            {voted_rows}
                        </tbody>
                    </table>
                    
                    <h3 style="border-bottom: 2px solid #dc3545; padding-bottom: 5px; color: #dc3545;">Not Voted Electors</h3>
                    <table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr>
                                <th style="padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Name</th>
                                <th style="padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Email</th>
                                {phone_header}
                            </tr>
                        </thead>
                        <tbody>
                            {not_voted_rows}
                        </tbody>
                    </table>
                    """
                    
                    html_body = html_body.format(
                        phone_header=phone_header,
                        voted_rows=build_elector_rows(voted_list, show_phone) or "<tr><td colspan='3'>None</td></tr>",
                        not_voted_rows=build_elector_rows(not_voted_list, show_phone) or "<tr><td colspan='3'>None</td></tr>"
                    )

                    # Send to all admins
                    admins = Admin.query.all()
                    for admin in admins:
                        send_notification_email(admin.email, f"Official Results: {election.title}", html_body)
                        
                    flash('Results released. Detailed report sent to all admins.', 'success')
                except Exception as e:
                    print(f"Error sending result emails: {e}")
                    flash(f'Results released, but failed to send result emails: {e}', 'warning')
            
            session.pop('release_election_id', None)
            session.pop('release_otp', None) # Clear OTP from session
            return redirect(url_for('admin.manage_election', election_id=election_id))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_otp_generic.html', title="Confirm Release Results")

@admin_bp.route('/admins', methods=['GET', 'POST'])
@login_required
def manage_admins():
    from utils import get_current_thread_limit
    
    if not current_user.can_manage_admins:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    

    form = AddAdminForm()
    if form.validate_on_submit():
        if Admin.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'error')
        elif Admin.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'error')
        else:
            # Generate random password
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            
            new_admin = Admin(
                username=form.username.data,
                email=form.email.data,
                is_force_change_password=True,
                perm_manage_elections=form.perm_manage_elections.data,
                perm_manage_electors=form.perm_manage_electors.data,
                perm_manage_admins=form.perm_manage_admins.data
            )
            new_admin.set_password(password)
            db.session.add(new_admin)
            db.session.commit()
            
            # Send Email
            if send_password_email(form.email.data, form.username.data, password):
                flash(f'Admin created. Credentials sent to {form.email.data}', 'success')
            else:
                 flash(f'Admin created but failed to send email.', 'warning')
            
            return redirect(url_for('admin.manage_admins'))
            
    admins = Admin.query.all()
    current_limit = get_current_thread_limit()
    
    return render_template('admin/manage_admins.html', form=form, admins=admins, current_thread_limit=current_limit)

@admin_bp.route('/admin/<int:admin_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_admin(admin_id):
    if not current_user.can_manage_admins:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    admin = Admin.query.get_or_404(admin_id)

    if admin.is_super_admin and not current_user.is_super_admin:
         flash('Cannot edit Super Admin.', 'error')
         return redirect(url_for('admin.manage_admins'))

    form = EditAdminForm(obj=admin)
    

    if request.method == 'POST':
        if admin.is_super_admin:
            # Ignore form data for permissions, ensure they remain True
            form.perm_manage_elections.data = True
            form.perm_manage_electors.data = True
            form.perm_manage_admins.data = True

    if form.validate_on_submit():
        # Check if email is changing for Super Admin (Self Update)
        if admin.is_super_admin and admin.id == current_user.id and form.email.data != admin.email:
            # Initiate OTP flow
            new_email = form.email.data
            # Check if used
            if Admin.query.filter(Admin.email==new_email).first():
                 flash('Email already in use.', 'error')
                 return render_template('admin/edit_admin.html', form=form, admin=admin)
            
            # Store temp data in session
            otp = str(random.randint(100000, 999999))
            store_otp_in_session('update_admin_otp', otp)
            session['update_admin_data'] = {
                'admin_id': admin.id,
                'email': new_email,
                'perms': {
                    'perm_manage_elections': form.perm_manage_elections.data,
                    'perm_manage_electors': form.perm_manage_electors.data,
                    'perm_manage_admins': form.perm_manage_admins.data
                }
            }
            # Send to CURRENT email for security check
            send_otp(admin.email, otp, purpose="Email Change Verification")
            flash(f'OTP sent to your current email ({admin.email}) to verify change.', 'info')
            return redirect(url_for('admin.verify_update_otp'))

        admin.email = form.email.data
        
        # Enforce permissions
        if admin.is_super_admin:
            # Backend Enforcement: Super Admin MUST have all permissions
            admin.perm_manage_elections = True
            admin.perm_manage_electors = True
            admin.perm_manage_admins = True
        else:
            # Regular Admin: Update from form
            admin.perm_manage_elections = form.perm_manage_elections.data
            admin.perm_manage_electors = form.perm_manage_electors.data
            admin.perm_manage_admins = form.perm_manage_admins.data
            
        if form.reset_password.data:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            admin.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            admin.is_force_change_password = True
            send_password_email(admin.email, admin.username, password)
            flash('Password reset and sent to email.', 'info')
            
        db.session.commit()
        flash('Admin updated successfully.', 'success')
        return redirect(url_for('admin.manage_admins'))
        
    return render_template('admin/edit_admin.html', form=form, admin=admin)

@admin_bp.route('/admin/verify_update_otp', methods=['GET', 'POST'])
@login_required
def verify_update_otp():
    if 'update_admin_data' not in session:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('update_admin_otp', otp)
        
        if is_valid:
            data = session.get('update_admin_data')
            if data:
                admin = Admin.query.get(data['admin_id'])
                if admin:
                    admin.email = data['email']
                    admin.perm_manage_elections = data['perms']['perm_manage_elections']
                    admin.perm_manage_electors = data['perms']['perm_manage_electors']
                    admin.perm_manage_admins = data['perms']['perm_manage_admins']
                    db.session.commit()
                    flash('Admin updated successfully.', 'success')
            
            session.pop('update_admin_data', None)
            session.pop('update_admin_otp', None)
            return redirect(url_for('admin.manage_admins'))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_update_otp.html')

@admin_bp.route('/admin/<int:admin_id>/delete', methods=['POST'])
@login_required
def delete_admin(admin_id):
    if not current_user.can_manage_admins:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    admin = Admin.query.get_or_404(admin_id)
    if admin.is_super_admin:
        flash('Cannot delete Super Admin.', 'error')
    elif admin.id == current_user.id:
        flash('Cannot delete yourself.', 'error')
    else:
        db.session.delete(admin)
        db.session.commit()
        flash('Admin deleted.', 'success')
        
    return redirect(url_for('admin.manage_admins'))

@admin_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password_hash, form.current_password.data):
            current_user.password_hash = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
            current_user.is_force_change_password = False
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Incorrect current password.', 'error')
    return render_template('admin/change_password.html', form=form)

@admin_bp.route('/profile/password/initiate')
@login_required
def initiate_self_password_change():
    otp = str(random.randint(100000, 999999))
    store_otp_in_session('password_change_otp', otp)
    session['pwd_change_user_id'] = current_user.id
    
    send_otp(current_user.email, otp, purpose="Password Change")
    flash(f'OTP sent to {current_user.email} to verify safe password change.', 'info')
    return redirect(url_for('admin.verify_password_change_otp'))

@admin_bp.route('/profile/password/verify', methods=['GET', 'POST'])
@login_required
def verify_password_change_otp():
    if 'pwd_change_user_id' not in session or session.get('pwd_change_user_id') != current_user.id:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('password_change_otp', otp)
        
        if is_valid:
            session['pwd_change_verified'] = True
            session.pop('password_change_otp', None)
            return redirect(url_for('admin.self_set_password'))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_otp_generic.html', title="Verify Password Change")

@admin_bp.route('/profile/password/set', methods=['GET', 'POST'])
@login_required
def self_set_password():
    if not session.get('pwd_change_verified') or session.get('pwd_change_user_id') != current_user.id:
        return redirect(url_for('admin.dashboard'))
        
    form = NewPasswordForm()
    if form.validate_on_submit():
        user = Admin.query.get(current_user.id)
        user.password_hash = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
        user.is_force_change_password = False
        db.session.commit()
        
        # Cleanup
        session.pop('pwd_change_verified', None)
        session.pop('pwd_change_user_id', None)
        
        flash('Password updated successfully.', 'success')
        return redirect(url_for('admin.dashboard'))
        
    return render_template('admin/change_password_new.html', form=form)

@admin_bp.route('/login/forgot', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user_input = form.identify.data
        user = Admin.query.filter((Admin.username==user_input) | (Admin.email==user_input)).first()
        
        if user:
            otp = str(random.randint(100000, 999999))
            # Reuse same session concept but distinct keys
            store_otp_in_session('reset_pwd_otp', otp)
            session['reset_pwd_user_id'] = user.id
            
            send_otp(user.email, otp, purpose="Password Reset")

            flash(f'If an account exists for {user_input}, an OTP has been sent.', 'info')
            return redirect(url_for('admin.verify_reset_password_otp'))
        else:
            flash(f'If an account exists for {user_input}, an OTP has been sent.', 'info')
            return redirect(url_for('admin.verify_reset_password_otp'))
            
    return render_template('admin/forgot_password.html', form=form)

@admin_bp.route('/login/forgot/verify', methods=['GET', 'POST'])
def verify_reset_password_otp():
    if 'reset_pwd_otp' not in session:
        return render_template('admin/verify_otp_generic.html', title="Enter OTP")
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('reset_pwd_otp', otp)
        
        if is_valid:
            session['reset_pwd_verified'] = True
            return redirect(url_for('admin.reset_password_set'))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_otp_generic.html', title="Reset Password - Verify OTP")

@admin_bp.route('/login/forgot/set', methods=['GET', 'POST'])
def reset_password_set():
    if not session.get('reset_pwd_verified') or 'reset_pwd_user_id' not in session:
        return redirect(url_for('admin.login'))
        
    form = NewPasswordForm()
    if form.validate_on_submit():
        user = Admin.query.get(session['reset_pwd_user_id'])
        if user:
            user.password_hash = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
            user.is_force_change_password = False 
            db.session.commit()
            
            session.pop('reset_pwd_verified', None)
            session.pop('reset_pwd_user_id', None)
            session.pop('reset_pwd_otp', None)
            
            flash('Password reset successfully. Please login.', 'success')
            return redirect(url_for('admin.login'))
            
    return render_template('admin/change_password_new.html', form=form)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        login_id = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter((Admin.username==login_id) | (Admin.email==login_id)).first()
        
        if user and check_password_hash(user.password_hash, password):
                session['pending_login_user_id'] = user.id
                otp = str(random.randint(100000, 999999))
                store_otp_in_session('login_otp', otp)
                
                send_otp(user.email, otp, purpose="Admin Login")
                flash('Login OTP sent to your email.', 'info')
                return redirect(url_for('admin.verify_login_otp'))
        else:
            flash('Invalid username/email or password', 'error')
            
    return render_template('admin/login.html')

@admin_bp.route('/login/verify', methods=['GET', 'POST'])
def verify_login_otp():
    if 'pending_login_user_id' not in session:
        return redirect(url_for('admin.login'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('login_otp', otp)
        
        if is_valid:
             user_id = session.get('pending_login_user_id')
             user = Admin.query.get(user_id)
             if user:
                 login_user(user)
                 session.pop('pending_login_user_id', None)
                 session.pop('login_otp', None)
                 

                 return redirect(url_for('admin.dashboard'))
        else:
             flash(msg, 'error')
            
    return render_template('admin/login_otp.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    elections = Election.query.order_by(Election.start_time.desc()).all()
    return render_template('admin/dashboard.html', elections=elections)

@admin_bp.route('/elector/<int:elector_id>/approve')
@login_required
def approve_elector_request(elector_id):
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    elector = Elector.query.get_or_404(elector_id)
    elector.status = 'approved'
    db.session.commit()
    

    if elector.email:
        from utils import send_notification_email
        subject = f"Access Approved: {elector.election.title}"
        body = f"""
        <p>Dear {elector.name},</p>
        <p>Your request to be added to the voter roll for <strong>{elector.election.title}</strong> has been <strong>APPROVED</strong>.</p>
        <p>You can now log in and cast your vote.</p>
        <a href="{url_for('public.vote_login', election_id=elector.election.id, _external=True)}">Login to Vote</a>
        """
        send_notification_email(elector.email, subject, body)
        
    flash(f'Request for {elector.name} approved.', 'success')
    return redirect(url_for('admin.manage_election', election_id=elector.election.id))

@admin_bp.route('/elector/<int:elector_id>/reject')
@login_required
def reject_elector_request(elector_id):
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    elector = Elector.query.get_or_404(elector_id)
    

    election_id = elector.election.id
    email = elector.email
    name = elector.name
    title = elector.election.title
    
    db.session.delete(elector)
    db.session.commit()
    

    if email:
        from utils import send_notification_email
        subject = f"Access Request Update: {title}"
        body = f"""
        <p>Dear {name},</p>
        <p>Your request to be added to the voter roll for <strong>{title}</strong> has been <strong>REJECTED</strong>.</p>
        <p>You have been removed from the request list. You may apply again if there was an error in your details.</p>
        """
        send_notification_email(email, subject, body)
        
    flash(f'Request for {name} rejected and removed.', 'success')
    return redirect(url_for('admin.manage_election', election_id=election_id))

@admin_bp.route('/election/<int:election_id>/export_electors')
@login_required
def export_electors(election_id):
    if not current_user.can_manage_electors:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))

    election = Election.query.get_or_404(election_id)
    

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Name', 'Email', 'Phone'])
    
    for elector in election.electors:
        cw.writerow([elector.name, elector.email or '', elector.phone or ''])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=electors_{election_id}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
@admin_bp.route('/election/<int:election_id>/export_secret_codes/initiate', methods=['POST'])
@login_required
def initiate_export_secret_codes(election_id):
    if not current_user.is_super_admin:
        flash('Access denied. Super Admin only.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    election = Election.query.get_or_404(election_id)
    

    otp = str(random.randint(100000, 999999))
    session['export_codes_election_id'] = election.id
    store_otp_in_session('export_codes_otp', otp)
    
    send_otp(current_user.email, otp, purpose=f"SECRET CODE EXPORT for '{election.title}'")
    flash(f'CRITICAL: OTP sent to {current_user.email}. required for exporting sensitive data.', 'warning')
    return redirect(url_for('admin.verify_export_secret_codes_otp'))

@admin_bp.route('/election/verify_export_secret_codes', methods=['GET', 'POST'])
@login_required
def verify_export_secret_codes_otp():
    if 'export_codes_election_id' not in session:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        is_valid, msg = verify_otp_in_session('export_codes_otp', otp)
        
        if is_valid:
            election_id = session.get('export_codes_election_id')
            election = Election.query.get(election_id)
            
            if election:
                # GENERATE CSV
                si = io.StringIO()
                cw = csv.writer(si)
                cw.writerow(['Name', 'Phone', 'Email', 'Secret Code'])
                
                electors = Elector.query.filter_by(election_id=election.id).all()
                for elector in electors:
                    cw.writerow([elector.name, elector.phone or '', elector.email or '', elector.secret_code])
                    
                output = make_response(si.getvalue())
                output.headers["Content-Disposition"] = f"attachment; filename=secret_codes_{election.id}.csv"
                output.headers["Content-type"] = "text/csv"
                # Ensure no caching so admins always get the latest codes
                output.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                output.headers["Pragma"] = "no-cache"
                output.headers["Expires"] = "0"
                

                session.pop('export_codes_election_id', None)
                session.pop('export_codes_otp', None)
                
                return output
                
            else:
                 flash('Election not found.', 'error')
            
            session.pop('export_codes_election_id', None)
            session.pop('export_codes_otp', None)
            return redirect(url_for('admin.dashboard'))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_otp_export.html', title="Confirm Export of Secret Codes")

@admin_bp.route('/election/<int:election_id>/reset_all_codes/initiate', methods=['POST'])
@login_required
def initiate_reset_all_codes(election_id):
    if not current_user.is_super_admin:
        flash('Access denied. Super Admin only.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
        
    election = Election.query.get_or_404(election_id)
    
    if election.status == 'completed':
        flash('Cannot reset codes for a completed election.', 'error')
        return redirect(url_for('admin.manage_election', election_id=election_id))
    
    # Initiate OTP flow
    otp = str(random.randint(100000, 999999))
    session['reset_all_codes_election_id'] = election.id
    store_otp_in_session('reset_all_codes_otp', otp)
    
    send_otp(current_user.email, otp, purpose=f"RESET ALL CODES for '{election.title}'")
    flash(f'CRITICAL: OTP sent to {current_user.email}. required for bulk reset.', 'warning')
    return redirect(url_for('admin.verify_reset_all_codes_otp'))

@admin_bp.route('/election/verify_reset_all_codes', methods=['GET', 'POST'])
@login_required
def verify_reset_all_codes_otp():
    if 'reset_all_codes_election_id' not in session:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')

        is_valid, msg = verify_otp_in_session('reset_all_codes_otp', otp)
        
        if is_valid:
            election_id = session.get('reset_all_codes_election_id')
            election = Election.query.get(election_id)
            
            if election:
                import random
                electors = Elector.query.filter_by(election_id=election.id).all()
                count = 0
                for elector in electors:
                    elector.secret_code = str(random.randint(100000, 999999))
                    count += 1
                
                db.session.commit()
                flash(f'SUCCESS: Regenerated secret codes for {count} electors.', 'success')
            else:
                 flash('Election not found.', 'error')
            
            session.pop('reset_all_codes_election_id', None)
            return redirect(url_for('admin.manage_election', election_id=election_id if election else 0))
        else:
            flash(msg, 'error')
            
    return render_template('admin/verify_otp_reset_all.html', title="Confirm Reset ALL Codes")

@admin_bp.route('/admin/update_thread_limit', methods=['POST'])
@login_required
def update_email_limit():
    from utils import update_email_thread_limit
    
    if not current_user.can_manage_admins:
        flash('Access denied.', 'error')
        return redirect(url_for('admin.manage_admins'))
        
    limit = request.form.get('thread_limit')
    try:
        limit = int(limit)
        if limit < 1:
            flash('Limit must be at least 1.', 'error')
        else:
            if update_email_thread_limit(limit):
                flash(f'Email thread limit updated to {limit}.', 'success')
            else:
                flash('Failed to update thread limit check server logs.', 'error')
    except ValueError:
       flash('Invalid limit value.', 'error')
       
    return redirect(url_for('admin.manage_admins'))


