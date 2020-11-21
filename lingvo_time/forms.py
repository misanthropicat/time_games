from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
from wtforms.widgets import HiddenInput


def generate_level(i):
    return i * 0.75, f'Level {i}'


class WordForm(FlaskForm):
    task = StringField(label='Task', validators=[DataRequired()])
    missed_letter = StringField(label='Missed letter', validators=[DataRequired()])
    next = SubmitField(label='Next word')


class MainForm(FlaskForm):
    level = SelectField('Choose the level of complexity',
                        choices=[generate_level(i) for i in range(1, 10)])
    game_type = SelectField('What game do you want to play',
                            choices=[('lingvo', 'Lingvo game'),
                                     ('math', 'Math game')])
    start = SubmitField(label='Start')


class MathForm(FlaskForm):
    task = StringField(label='Task')
    result = StringField(label='Result', validators=[DataRequired()])
    next = SubmitField(label='Next task')