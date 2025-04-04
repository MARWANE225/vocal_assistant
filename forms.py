from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import InputRequired

from wtforms import StringField

class ProfileForm(FlaskForm):
    profile_pic = FileField('Profile Picture', validators=[InputRequired()])
    phone = StringField('Phone', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired()])
    submit = SubmitField('Upload')

