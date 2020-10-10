import codecs
import difflib
import os
import random
import sqlite3
import uuid
from datetime import datetime

from simple_image_download import simple_image_download as simp
from flask import Flask, g, redirect, request, render_template, flash, url_for
from flask_wtf import FlaskForm
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired
from wtforms.widgets import HiddenInput

module_dir = os.path.join(os.getcwd(), 'lingvo_time')
WORDS = codecs.open(os.path.join(module_dir, 'level1.txt'), encoding='utf-8').read().splitlines()


def generate_level(i):
    return i * 0.75, f'Level {i}'


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_mapping(
    DATABASE=os.path.join(module_dir, 'gamesdata.db'),
    WTF_CSRF_ENABLED=False
)


class WordForm(FlaskForm):
    task = StringField(label='Task', validators=[DataRequired()])
    missed_letter = StringField(label='Missed letter', validators=[DataRequired()])
    spaced = HiddenInput()
    next = SubmitField(label='Next word')


class MainForm(FlaskForm):
    level = SelectField('Choose the level of complexity',
                        choices=[generate_level(i) for i in range(1, 10)])
    game_type = SelectField('What game do you want to play',
                            choices=[('lingvo_task', 'Lingvo game'),
                                     ('math_task', 'Math game')])
    run_id = HiddenInput()


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = dict_factory

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with app.open_resource('db_scripts.sql') as f:
        db.executescript(f.read().decode('utf8'))
    db.commit()


def query_db(query, args=(), one=False):
    cur = get_db().cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def create_task(run_id):
    word = random.choice(WORDS)
    task_id = str(uuid.uuid4())
    spaced = random.randint(0, len(word))
    query_db("INSERT INTO lingvo_exercises (ex_id, run_id, word, spaced, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (task_id, run_id, word, spaced,
              datetime.timestamp(datetime.now())))

    return task_id


def count_time(complexity):
    """
    :param complexity: int: more pain - more gain
    :return: obtained time by resolving exercise with provided complexity
    """
    seconds = 60 * complexity
    return seconds


@app.route('/', methods=['GET', 'POST'])
def start_run():
    form = MainForm()
    if request.method == 'POST':
        get_db()
        c_level = form['level']
        game_type = form['game_type']
        run_id = str(uuid.uuid4())
        query_db("INSERT INTO runs "
                 "(run_id, runtime, play_time_sec, level, game_type) VALUES "
                 "(?, datetime('now'), 0, ?, ?)",
                 (run_id, c_level.data, game_type.data))
        return redirect(url_for('lingvo_task', run_id=run_id))
    return render_template('index.html', form=form, start_time=datetime.now())


@app.route('/run/<run_id>/lingvo', methods=['GET', 'POST'])
@app.route('/run/<run_id>/lingvo/<task_id>')
def lingvo_task(run_id, task_id=''):
    def _check():
        result = request.form['task'].replace('_', request.form['missed_letter'])
        correct_answer = query_db("SELECT word from lingvo_exercises WHERE ex_id = ?", (task_id,))
        if result.find(correct_answer['word']) == 0:
            level = query_db("SELECT level FROM runs WHERE run_id = ?",
                             (run_id,))
            mined_time = count_time(level)
            current_playtime = query_db("SELECT play_time_sec FROM runs WHERE run_id = ?",
                                        (run_id,))
            query_db("UPDATE runs SET play_time_sec ?",
                     (round(current_playtime + mined_time),))
            flash(f"You're right. Great job!\nPlay time increased by {mined_time} seconds")
        flash(f"You're mistaken. Correct answer is {correct_answer}")
        return redirect(url_for('lingvo_task'), run_id)

    form = WordForm()
    if request.method == 'POST':
        redirect(url_for('lingvo_task', run_id=run_id, task_id=task_id))
    if form.validate_on_submit():
        _check()
    task_id = create_task(run_id)
    result = query_db("SELECT word, spaced "
                      "FROM lingvo_exercises "
                      "WHERE ex_id = ?", (task_id,), one=True)
    word = result['word']
    spaced = int(result['spaced'])
    form.answer = word[spaced]
    form.task = f'{word[0:spaced]}_{word[spaced + 1:]}'
    return render_template('lingvo_game.html', form=form)


def get_mark(mark):
    response = simp.simple_image_download
    response().download(keywords=mark, limit=5,
                        extensions={'.jpg', '.png', '.ico', '.gif', '.jpeg'})
    images = response().urls(mark, 5)
    return images
