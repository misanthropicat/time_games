import uuid
from datetime import datetime

from flask import request, render_template
from werkzeug.utils import redirect

from lingvo_time import app, query_db, get_answer_for_task, WordForm, get_excercise

