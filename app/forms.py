from flask_wtf import FlaskForm
from wtforms import Form, BooleanField, StringField, PasswordField, SubmitField, SelectMultipleField, widgets, BooleanField, FieldList, FormField, RadioField, ValidationError
from wtforms.validators import DataRequired, Length, Optional
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
class GameTagField(Form):
    same_as_platform = BooleanField('Same as platform gamertag')
    gamertag = StringField('Gamertag')

    def validate(self):
        # Always run base validations first
        if not super().validate():
            return False

        # If "same as platform" is not checked, gamertag is required
        if not self.same_as_platform.data and not self.gamertag.data:
            self.gamertag.errors.append('Gamertag required if not same as platform')
            return False

        return True

class GamertagForm(FlaskForm):
    platform = SelectMultipleField(
        'Select your platform(s)',
        choices=[('Xbox', 'Xbox'), ('PlayStation', 'PlayStation'), ('PC', 'PC')],
        validators=[DataRequired(message="Please select at least one platform.")],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    platform_gamertag = StringField('Platform Gamertag', validators=[DataRequired()])
    submit = SubmitField('Submit')
