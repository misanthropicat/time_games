import codecs
import os
import sqlite3
import uuid
from datetime import datetime
import random
from lingvo_time.forms import MainForm, WordForm, MathForm
from simple_image_download import simple_image_download as simp
from flask import Flask, g, redirect, request, render_template, url_for, get_template_attribute, flash
from werkzeug.middleware.proxy_fix import ProxyFix

module_dir = os.path.join(os.getcwd(), 'lingvo_time')

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


def create_lingvo_task(run_id):
    complexity = query_db("SELECT level FROM runs "
                          "WHERE run_id = ?", (run_id,), one=True)
    level = complexity.split(' ')[1]
    WORDS = codecs.open(os.path.join(module_dir, f'level{level}.txt'), encoding='utf-8').read().splitlines()
    word = random.choice(WORDS)
    task_id = str(uuid.uuid4())
    spaced = random.randint(0, len(word))
    query_db("INSERT INTO lingvo_exercises (ex_id, run_id, word, spaced, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (task_id, run_id, word, spaced, datetime.timestamp(datetime.now())))
    task = f'{word[0:spaced]}_{word[spaced + 1:]}'

    return task, word[spaced], task_id


def create_math_task(run_id):
    task = ""
    complexity = query_db("SELECT level FROM runs "
                          "WHERE run_id = ?", (run_id,), one=True)
    a, b = random.choice(range(2, 10 * complexity)), random.choice(range(2, 10 * complexity))
    randomized_task = random.choice(['+', '-'])
    result = 0
    if randomized_task == '+':
        result = a + b
        task += f"{a} + {b}"
        if complexity in range(3, 5):
            c = random.choice(range(2, 10 * complexity))
            result += c
            task += f" + {c}".format(c)
    if randomized_task == '-':
        a, b = (a, b) if a > b else (b, a)
        result = a - b
        task += f"{a} - {b}"
        if complexity in range(3, 5):
            c = random.choice(range(1, result + 1))
            task += f" - {c}"
            result -= c
    task_id = str(uuid.uuid4())
    query_db("INSERT INTO math_exercises (ex_id, run_id, task, expected, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (task_id, run_id, task, result, datetime.timestamp(datetime.now())))
    return task, result, task_id


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
        c_level = float(form['level'].data)
        game_type = form['game_type'].data
        run_id = str(uuid.uuid4())
        query_db("INSERT INTO runs "
                 "(run_id, runtime, play_time_sec, level, game_type) VALUES "
                 "(?, datetime('now'), 0, ?, ?)",
                 (run_id, c_level, game_type))
        return redirect(url_for('create_task', run_id=run_id, game_type=game_type))
    return render_template('index.html', form=form, start_time=datetime.now())


@app.route('/run/<run_id>/<game_type>', methods=['GET'], endpoint='create_task')
def create_task(run_id, game_type):
    if game_type == 'lingvo':
        task, answer, task_id = create_lingvo_task(run_id)
        redirect(url_for('check_task', run_id=run_id, game_type='lingvo', task_id=task_id))
    elif game_type == 'math':
        task, result, task_id = create_math_task(run_id)
        redirect(url_for('check_task', run_id=run_id, game_type='math', task_id=task_id))


@app.route('/run/<run_id>/<game_type>/<task_id>', methods=['GET', 'POST'], endpoint='check_task')
def check_task(run_id, game_type, task_id):
    if game_type == 'lingvo':
        form = WordForm()
        word, spaced = query_db('SELECT word, spaced '
                                'FROM lingvo_exercises '
                                'WHERE ex_id = ? '
                                'AND run_id = ?', (task_id, run_id), one=True)
        if form.validate_on_submit():
            answer = form.missed_letter
            if answer == word[spaced]:
                flash('Correct. Good job!')
            else:
                flash(f"You've mistaken. Correct answer is {answer}.")
        task = f'{word[0:spaced]}_{word[spaced + 1:]}'
        form.task = task
        return render_template('lingvo_game.html', form=form)
    elif game_type == 'math':
        form = MathForm()
        task, expected = query_db('SELECT task, expected '
                                  'FROM math_exercises '
                                  'WHERE ex_id = ? '
                                  'AND run_id = ?', (task_id, run_id), one=True)
        if form.validate_on_submit():
            result = form.result
            if result == expected:
                flash('Correct. Good job!')
            else:
                flash(f"You've mistaken. Correct answer is {expected}.")


def get_mark(mark):
    response = simp.simple_image_download
    response().download(keywords=mark, limit=5,
                        extensions={'.jpg', '.png', '.ico', '.gif', '.jpeg'})
    images = response().urls(mark, 5)
    return images


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True)
