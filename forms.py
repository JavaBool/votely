from flask_wtf import FlaskForm
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, SelectField, SubmitField, IntegerField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Optional, Email, EqualTo, NumberRange

class ElectionForm(FlaskForm):
    title = StringField('Election Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    start_time = DateTimeLocalField('Election Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('Election End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    nomination_start = DateTimeLocalField('Nomination Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    nomination_end = DateTimeLocalField('Nomination End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    
    config_age = SelectField('Age Requirement', choices=[(0, 'Hidden'), (1, 'Optional'), (2, 'Required')], coerce=int, default=0)
    min_age = IntegerField('Minimum Age (if applicable)', default=0, validators=[Optional(), NumberRange(min=0, message="Age limit cannot be negative.")])
    config_photo = SelectField('Photo Requirement', choices=[(0, 'Hidden'), (1, 'Optional'), (2, 'Required')], coerce=int, default=1)
    allow_nota = BooleanField('Allow NOTA (None of the Above) Option', default=True)
    allow_phone_voting = BooleanField('Allow Phone Number Voting', default=False)
    submit = SubmitField('Save Election')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class NewPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Set Password')

class ForgotPasswordForm(FlaskForm):
    identify = StringField('Username or Email', validators=[DataRequired()])
    submit = SubmitField('Send OTP')

class AddAdminForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    perm_manage_elections = BooleanField('Manage Elections')
    perm_manage_electors = BooleanField('Manage Electors')
    perm_manage_admins = BooleanField('Manage Admins')
    submit = SubmitField('Create Admin')

class EditAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    perm_manage_elections = BooleanField('Manage Elections')
    perm_manage_electors = BooleanField('Manage Electors')
    perm_manage_admins = BooleanField('Manage Admins')
    reset_password = BooleanField('Reset Password (send new random password)')
    submit = SubmitField('Update Admin')

class EditElectorForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone')
    email = StringField('Email', validators=[Optional(), Email()])
    custom_success_msg = TextAreaField('Custom Success Message (HTML)')
    submit = SubmitField('Update Elector')
