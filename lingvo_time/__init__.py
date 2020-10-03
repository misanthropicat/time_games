import codecs
import difflib
import os
import random
import sqlite3
import uuid
from datetime import datetime

from lingvo_time.utils import generate_level
from simple_image_download import simple_image_download as simp
from flask import Flask, g, redirect, request, render_template, flash, url_for
from flask_wtf import FlaskForm
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired
from wtforms.widgets import HiddenInput

os.environ['REQUESTS_CA_BUNDLE'] = os.getcwd() + 'certificates.crt'

module_dir = os.path.join(os.getcwd(), 'lingvo_time')
WORDS = codecs.open(os.path.join(module_dir, 'level1.txt'),
                    encoding='utf-8').read().splitlines()


# TODO: the system of levels which are bounded to complexity and amount of generated time

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_mapping(
    DATABASE=os.path.join(module_dir, 'gamesdata.db'),
    WTF_CSRF_ENABLED=False
)


class WordForm(FlaskForm):
    task = StringField('Task', validators=[DataRequired()])
    missed_letter = StringField('Missed letter', validators=[DataRequired()])
    spaced = HiddenInput()
    next = SubmitField()


class MainForm(FlaskForm):
    level = SelectField('Choose the level of complexity',
                        choices=[generate_level(i) for i in range(10)])
    game_type = SelectField('What game do you want to play',
                            choices=[('lingvo_task', 'Lingvo game'),
                                     ('math_task', 'Math game')])
    run_id = HiddenInput()
    next = SubmitField()


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

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


def create_task(run_id):
    word = random.choice(WORDS)
    task_id = str(uuid.uuid4())
    spaced = random.randint(0, len(word))
    query_db("INSERT INTO lingvo_exercises (ex_id, run_id, word, spaced, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (task_id, run_id, word, spaced,
              datetime.timestamp(datetime.now())))

    return task_id, word, spaced


def check_answer(task, answer):
    assumed_word = task.replace('_', answer)
    return assumed_word in WORDS


def count_time(complexity):
    """
    :param complexity: int: more pain - more gain
    :return: obtained time by resolving exercise with provided complexity
    """
    seconds = 60 * complexity
    return seconds


@app.route('/', methods=['GET', 'POST'])
def start_run():
    if request.method == 'GET':
        get_db()
        run_id = str(uuid.uuid4())
        form = MainForm()
        form.run_id = run_id
        return render_template('index.html', form=form,
                               start_time=datetime.now())
    else:
        c_level = request.form['level']
        query_db("INSERT INTO runs "
                 "(run_id, runtime, play_time, level) VALUES "
                 "(?, datetime('now'), time('00:00:00'), ?)",
                 (request.form['run_id'], c_level))
    return render_template('index.html', start_time=datetime.now(),
                           run_id=request.form['run_id'])


@app.route('/run/<run_id>/lingvo', methods=['GET'])
def lingvo_task(run_id):
    form = WordForm()
    task_id, word, spaced = create_task(run_id)
    form.answer = (word[spaced])
    return render_template('lingvo_game.html', form=form,
                           task=f'{word[0:spaced]}_{word[spaced + 1:]}',
                           run_id=run_id,
                           task_id=task_id)


@app.route('/run/<run_id>/lingvo/<task_id>', methods=['GET'])
def check_lingvo(run_id, task_id):
    result = check_answer(request.form['task'],
                          request.form['missed_letter'])
    correct_answer = query_db("SELECT word, task from lingvo_exercises "
                              "WHERE task_id = ?", (task_id,))
    difference = difflib.ndiff(correct_answer[0].word, correct_answer[0].task)
    message = "You're right. Great job!" if result else f"You're mistaken. Correct answer is {difference}"
    flash(message)
    if result:
        obtained_time = count_time()
        query_db("UPDATE runs "
                 "SET play_time ")
    return redirect()


def get_mark(mark):
    response = simp.simple_image_download
    response().download(keywords=mark, limit=5,
                        extensions={'.jpg', '.png', '.ico', '.gif', '.jpeg'})
    images = response().urls(mark, 5)
    return images
