import codecs
import os
import sqlite3
import uuid
from datetime import datetime
import random
from lingvo_time.forms import MainForm, WordForm, MathForm
from simple_image_download import simple_image_download as simp
from flask import Flask, g, redirect, request, render_template, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix

module_dir = os.path.join(os.getcwd(), 'lingvo_time')

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_mapping(
    DATABASE=os.path.join(module_dir, 'gamesdata.db'),
    WTF_CSRF_ENABLED=False,
    SESSION_TYPE='filesystem'
)
app.secret_key = 'super secret key'


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
    get_db().commit()
    return (rv[0] if rv else None) if one else rv


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def create_lingvo_task(run_id, level):
    WORDS = codecs.open(os.path.join(module_dir, f'level{level}.txt'), encoding='utf-8').read().splitlines()
    word = random.choice(WORDS)
    task_id = str(uuid.uuid4())
    spaced = random.randint(0, len(word))
    cur_time = datetime.timestamp(datetime.now())
    query_db("INSERT INTO lingvo_exercises (ex_id, run_id, word, spaced, task_created, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (task_id, run_id, word, spaced, cur_time, cur_time))

    return task_id


def create_math_task(run_id, complexity):
    a, b = random.choice(range(2, 10 * complexity)), random.choice(range(2, 10 * complexity))
    randomized_task = random.choice(['+', '-'])
    expected = -1
    task = ''
    if randomized_task == '+':
        expected = a + b
        task += f"{a} + {b}"
        if complexity in range(3, 5):
            c = random.choice(range(2, 10 * complexity))
            expected += c
            task += f" + {c}"
    if randomized_task == '-':
        a, b = (a, b) if a > b else (b, a)
        expected = a - b
        task += f"{a} - {b}"
        if complexity in range(3, 5):
            c = random.choice(range(1, expected + 1))
            task += f" - {c}"
            expected -= c
    task_id = str(uuid.uuid4())
    cur_time = datetime.timestamp(datetime.now())
    query_db("INSERT INTO math_exercises (ex_id, run_id, task, expected, task_created, "
             "last_updated) VALUES (?, ?, ?, ?, ?)",
             (task_id, run_id, task, expected, cur_time, cur_time))
    return task_id


def update_play_time(run_id, task_id):
    """
    :param task_id: uuid
    :param run_id: uuid
    :return: obtained time by resolving exercise with provided complexity
    """
    run_info = query_db('SELECT * FROM runs WHERE run_id = ?', (run_id,), one=True)
    game_type = run_info['game_type']
    task_info = query_db('SELECT * FROM lingvo_exercises '
                         'WHERE task_id = ?', (task_id,), one=True) if game_type == 'lingvo' \
        else query_db('SELECT * FROM math_exercises '
                      'WHERE task_id = ?', (task_id,), one=True)
    complexity = task_info['complexity']
    cur_time = datetime.timestamp(datetime.now())
    task_created = task_info['task_created']
    mined_time = (cur_time - task_created) * complexity
    if game_type == 'lingvo':
        query_db('UPDATE lingvo_exercises '
                 'SET last_updated = ? '
                 'WHERE task_id = ?', (cur_time, task_id))
    elif game_type == 'math':
        query_db('UPDATE math_exercises '
                 'SET last_updated = ? '
                 'WHERE task_id = ?', (cur_time, task_id))
    run_info = query_db('SELECT * FROM runs '
                        'WHERE run_id = ?', (run_id,), one=True)
    play_time = int(run_info['play_time_sec']) + mined_time
    query_db('UPDATE runs '
             'SET play_time_sec = ?, runtime = ? '
             'WHERE run_id = ?', (play_time, cur_time, run_id))
    return mined_time


@app.route('/', methods=['GET', 'POST'])
def start_run():
    form = MainForm()
    if request.method == 'POST':
        get_db()
        complexity = float(form['level'].data)
        game_type = form['game_type'].data
        run_id = str(uuid.uuid4())
        query_db("INSERT INTO runs "
                 "(run_id, runtime, play_time_sec, complexity, game_type) VALUES "
                 "(?, datetime('now'), 0, ?, ?)",
                 (run_id, complexity, game_type))
        return redirect(url_for('create_task', run_id=run_id, game_type=game_type))
    return render_template('index.html', form=form, start_time=datetime.now())


@app.route('/run/<run_id>/<game_type>', methods=['GET'], endpoint='create_task')
def create_task(run_id, game_type):
    run_info = query_db("SELECT complexity FROM runs "
                        "WHERE run_id = ?", (run_id,), one=True)
    complexity = run_info['complexity']
    level = round(complexity / 0.75)
    if game_type == 'lingvo':
        task_id = create_lingvo_task(run_id, level)
        return redirect(url_for('lingvo_task', run_id=run_id, task_id=task_id))
    elif game_type == 'math':
        task_id = create_math_task(run_id, level)
        return redirect(url_for('math_task', run_id=run_id, task_id=task_id))


@app.route('/run/<run_id>/lingvo/<task_id>', methods=['GET', 'POST'])
def lingvo_task(run_id, task_id):
    form = WordForm()
    result = query_db('SELECT word, spaced '
                      'FROM lingvo_exercises '
                      'WHERE ex_id = ? '
                      'AND run_id = ?', (task_id, run_id), one=True)
    word = result['word']
    spaced = result['spaced']
    if request.method == 'GET':
        task = f'{word[0:spaced]}_{word[spaced + 1:]}'
        form.task = task
        return render_template('lingvo_game.html', form=form)
    answer = form.missed_letter.data
    query_db('UPDATE lingvo_exercises '
             'SET answer = ? '
             'WHERE task_id = ?', (answer, task_id))
    if answer == word[spaced]:
        mined_time = update_play_time(run_id, task_id)
        flash(f"Correct. Good job! You've mined {mined_time} seconds of playing time.")
    else:
        flash(f"You've mistaken. Correct answer is {answer}.")
    return redirect(url_for('create_task', run_id=run_id, game_type='lingvo'))


@app.route('/run/<run_id>/math/<task_id>', methods=['GET', 'POST'])
def math_task(run_id, task_id):
    form = MathForm()
    task_info = query_db('SELECT task, expected '
                         'FROM math_exercises '
                         'WHERE ex_id = ? '
                         'AND run_id = ?', (task_id, run_id), one=True)
    if request.method == 'GET':
        form.task = task_info['task']
        return render_template('math_game.html', form=form)
    result = form.result.data
    query_db('UPDATE math_exercises '
             'SET result = ? '
             'WHERE task_id = ?', (result, task_id))
    if int(result) == task_info['expected']:
        mined_time = update_play_time(run_id, task_id)
        flash(f"Correct. Good job! You've mined {mined_time} seconds of playing time.")
    else:
        flash(f"You've mistaken. Correct answer is {task_info['expected']}.")
    return redirect(url_for('create_task', run_id=run_id, game_type='math'))


def get_mark(mark):
    response = simp.simple_image_download
    response().download(keywords=mark, limit=5,
                        extensions={'.jpg', '.png', '.ico', '.gif', '.jpeg'})
    images = response().urls(mark, 5)
    return images


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True)
