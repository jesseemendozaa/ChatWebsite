from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectMultipleField, BooleanField, FieldList, FormField, RadioField
from wtforms.validators import DataRequired, Length
from wtforms.widgets import ListWidget, CheckboxInput

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4, max=35)])
    submit = SubmitField('Register')

class GameSelectionForm(FlaskForm):
    games = SelectMultipleField(
        'Select all the games you play',
        choices=[('UNO', 'UNO'), ('DBD', 'Dead By Daylight')],
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False)
    )
    submit = SubmitField('Finish Registration')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RoomForm(FlaskForm):
    code = StringField('Room Code', validators=[DataRequired()])
    submit = SubmitField('Join or Create Room')

# Optional: Define a small subform to hold per-game fields if you want to go dynamic
class GameTagField(FlaskForm):
    same_as_platform = BooleanField('Same as platform gamertag')
    gamertag = StringField('Gamertag')

class GamertagForm(FlaskForm):
    platform = RadioField('Platform', choices=[
        ('Xbox', 'Xbox'), ('PlayStation', 'PlayStation'), ('PC', 'Steam')
    ], validators=[DataRequired()])
    platform_gamertag = StringField('Platform Gamertag', validators=[DataRequired()])
    submit = SubmitField('Submit')