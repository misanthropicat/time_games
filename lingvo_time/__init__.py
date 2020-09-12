import codecs
import os
import random
import sqlite3
import uuid
from datetime import datetime

from simple_image_download import simple_image_download as simp
from flask import Flask, g, redirect, request, render_template, flash
from flask_wtf import FlaskForm
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from wtforms.widgets import HiddenInput

os.environ['REQUESTS_CA_BUNDLE'] = os.getcwd() + 'certificates.crt'

module_dir = os.path.join(os.getcwd(), 'lingvo_time')
WORDS = codecs.open(os.path.join(module_dir, 'level1.txt'),
                    encoding='utf-8').read().splitlines()


class WordForm(FlaskForm):
    task = StringField('Task', validators=[DataRequired()])
    missed_letter = StringField('Missed letter', validators=[DataRequired()])
    spaced = HiddenInput()
    submit = SubmitField('Check')


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_mapping(
    DATABASE=os.path.join(module_dir, 'gamesdata.db'),
    WTF_CSRF_ENABLED=False
)


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

    spaced = random.randint(0, len(word))
    query_db("INSERT INTO lingvo_exercises (ex_id, run_id, word, spaced, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (str(uuid.uuid4()), run_id, word, spaced,
              datetime.timestamp(datetime.now())))

    return word, spaced


@app.route('/')
def start_run():
    init_db()
    run_id = str(uuid.uuid4())
    query_db("INSERT INTO runs "
             "(run_id, runtime, play_time) VALUES "
             "(?, datetime('now'), time('00:00:00'))",
             (run_id,))
    print(f'Hey, boy! Your exercises run is started now.\n'
          f'Current time: {datetime.now()}.\n'
          f'Started run id: {run_id}')
    return redirect(f'/run/{run_id}')


def check_answer(task, answer):
    assumed_word = task.replace('_', answer)
    return get_mark("correct") if assumed_word in WORDS else get_mark(
        "incorrect")


@app.route('/run/<run_id>', methods=['GET', 'POST'])
def get_exercise(run_id):
    if request.method == 'GET':
        form = WordForm()
        word, spaced = create_task(run_id)
        form.answer = (word[spaced])
        return render_template('main.html', form=form,
                               task=f'{word[0:spaced]}_{word[spaced + 1:]}')
    else:
        result = check_answer(request.form['task'],
                              request.form['missed_letter'])
        message = "You're right. Great job!" if result
        flash(f"")
        return render_template('answer.html', result=result)


def get_mark(mark):
    response = simp.simple_image_download
    response().download(keywords=mark, limit=5,
                        extensions={'.jpg', '.png', '.ico', '.gif', '.jpeg'})
    images = response().urls(mark, 5)
    return images
