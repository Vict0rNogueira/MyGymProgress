from datetime import datetime

from flask import Blueprint, request, redirect, render_template, session as flask_session
from flask_login import login_user, logout_user, login_required, current_user

from .models import Workout, User, Exercise, Progress, WorkoutSession, db

main = Blueprint('main', __name__)


def _workout_session_key(workout_id):
    return f'ws_{workout_id}'


def _get_or_create_active_session(workout_id):
    key = _workout_session_key(workout_id)
    ws_id = flask_session.get(key)
    today = datetime.utcnow().date()
    if ws_id:
        ws = WorkoutSession.query.get(ws_id)
        if (
            ws
            and ws.workout_id == workout_id
            and ws.created_at.date() == today
        ):
            return ws
    ws = WorkoutSession(workout_id=workout_id)
    db.session.add(ws)
    db.session.flush()
    flask_session[key] = ws.id
    return ws


@main.route('/')
@login_required
def home():
    workouts = Workout.query.filter_by(user_id=current_user.id).all()
    session_started = request.args.get('session_started')
    started_workout_id = None
    if session_started and session_started.isdigit():
        started_workout_id = int(session_started)
    return render_template(
        'index.html',
        workouts=workouts,
        started_workout_id=started_workout_id,
    )


@main.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if not username or not password:
            error = 'Preencha usuário e senha.'
        elif User.query.filter_by(username=username).first():
            error = 'Este usuário já existe.'
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect('/login')

    return render_template('register.html', error=error)


@main.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect('/')
        error = 'Usuário ou senha inválidos.'
    return render_template('login.html', error=error)


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


@main.route('/add', methods=['POST'])
@login_required
def add():
    name = (request.form.get('name') or '').strip()
    if name:
        workout = Workout(name=name, user_id=current_user.id)
        db.session.add(workout)
        db.session.commit()
    return redirect('/')


@main.route('/delete/<int:id>')
@login_required
def delete(id):
    workout = Workout.query.get(id)
    if workout and workout.user_id == current_user.id:
        # Remove em cascata manualmente para evitar erro de FK no SQLite.
        # Primeiro: progressões; depois: exercícios; depois: sessões; por fim: o treino.
        exercises = Exercise.query.filter_by(workout_id=workout.id).all()
        for ex in exercises:
            Progress.query.filter_by(exercise_id=ex.id).delete(synchronize_session=False)

        WorkoutSession.query.filter_by(workout_id=workout.id).delete(synchronize_session=False)
        Exercise.query.filter_by(workout_id=workout.id).delete(synchronize_session=False)

        db.session.delete(workout)
        db.session.commit()
    return redirect('/')


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    workout = Workout.query.get(id)
    if not workout or workout.user_id != current_user.id:
        return redirect('/')
    if request.method == 'POST':
        workout.name = (request.form.get('name') or workout.name).strip()
        db.session.commit()
        return redirect('/')
    return f'''
        <h1>Editar treino</h1>
        <form method="POST">
            <input type="text" name="name" value="{workout.name}">
            <button type="submit">Salvar</button>
        </form>
    '''


@main.route('/workout/<int:workout_id>/session/start', methods=['POST'])
@login_required
def start_workout_session(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    if workout.user_id != current_user.id:
        return redirect('/')
    ws = WorkoutSession(workout_id=workout_id)
    db.session.add(ws)
    db.session.commit()
    flask_session[_workout_session_key(workout_id)] = ws.id
    return redirect(f'/?session_started={workout_id}')


@main.route('/workout/<int:workout_id>/compare')
@login_required
def workout_compare(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    if workout.user_id != current_user.id:
        return redirect('/')

    # Compara as 2 últimas sessões criadas do treino (mesmo que uma delas
    # não tenha séries registradas para alguns exercícios).
    sessions = (
        WorkoutSession.query.filter_by(workout_id=workout_id)
        .order_by(WorkoutSession.created_at.desc())
        .limit(2)
        .all()
    )

    if len(sessions) < 2:
        return render_template(
            'workout_compare.html',
            workout=workout,
            enough_data=False,
            labels=[],
            current_volumes=[],
            prev_volumes=[],
            current_label='',
            prev_label='',
            any_progress_current=False,
            any_progress_prev=False,
        )

    current_s = sessions[0]
    prev_s = sessions[1]

    def volume_for(exercise_id, session_id):
        rows = Progress.query.filter_by(
            session_id=session_id, exercise_id=exercise_id
        ).all()
        return sum((p.weight or 0) * (p.reps or 0) for p in rows)

    labels = []
    current_volumes = []
    prev_volumes = []
    for ex in workout.exercises:
        labels.append(ex.name)
        current_volumes.append(volume_for(ex.id, current_s.id))
        prev_volumes.append(volume_for(ex.id, prev_s.id))

    any_progress_current = any(v > 0 for v in current_volumes)
    any_progress_prev = any(v > 0 for v in prev_volumes)

    fmt = '%d/%m/%Y %H:%M'
    current_label = current_s.created_at.strftime(fmt)
    prev_label = prev_s.created_at.strftime(fmt)

    return render_template(
        'workout_compare.html',
        workout=workout,
        enough_data=True,
        labels=labels,
        current_volumes=current_volumes,
        prev_volumes=prev_volumes,
        current_label=current_label,
        prev_label=prev_label,
        any_progress_current=any_progress_current,
        any_progress_prev=any_progress_prev,
    )


@main.route('/add_progress/<int:exercise_id>', methods=['POST'])
@login_required
def add_progress(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    if exercise.workout.user_id != current_user.id:
        return redirect('/')
    weight = request.form.get('weight')
    reps = request.form.get('reps')
    if weight is None or reps is None:
        return redirect('/')
    ws = _get_or_create_active_session(exercise.workout_id)
    progress = Progress(
        weight=float(weight),
        reps=int(reps),
        exercise_id=exercise_id,
        session_id=ws.id,
    )
    db.session.add(progress)
    db.session.commit()
    return redirect('/')


@main.route('/add_exercise/<int:workout_id>', methods=['POST'])
@login_required
def add_exercise(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    if workout.user_id != current_user.id:
        return redirect('/')
    name = (request.form.get('name') or '').strip()
    if name:
        exercise = Exercise(name=name, workout_id=workout_id)
        db.session.add(exercise)
        db.session.commit()
    return redirect('/')


@main.route('/delete_exercise/<int:id>')
@login_required
def delete_exercise(id):
    exercise = Exercise.query.get(id)
    if exercise and exercise.workout.user_id == current_user.id:
        Progress.query.filter_by(exercise_id=exercise.id).delete(synchronize_session=False)
        db.session.commit()
        db.session.delete(exercise)
        db.session.commit()
    return redirect('/')


@main.route('/edit_exercise/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_exercise(id):
    exercise = Exercise.query.get(id)
    if not exercise or exercise.workout.user_id != current_user.id:
        return redirect('/')
    if request.method == 'POST':
        exercise.name = (request.form.get('name') or exercise.name).strip()
        db.session.commit()
        return redirect('/')
    return f'''
        <h1>Editar exercício</h1>
        <form method="POST">
            <input type="text" name="name" value="{exercise.name}">
            <button>Salvar</button>
        </form>
    '''


@main.route('/delete_progress/<int:id>')
@login_required
def delete_progress(id):
    progress = Progress.query.get(id)
    if progress and progress.exercise.workout.user_id == current_user.id:
        db.session.delete(progress)
        db.session.commit()
    return redirect('/')


@main.route('/exercise/<int:id>')
@login_required
def exercise_detail(id):
    exercise = Exercise.query.get(id)
    if not exercise or exercise.workout.user_id != current_user.id:
        return redirect('/')
    progress = Progress.query.filter_by(exercise_id=id).order_by(Progress.id).all()
    weights = [p.weight for p in progress]
    reps = [p.reps for p in progress]
    return render_template(
        'exercise.html',
        exercise=exercise,
        weights=weights,
        reps=reps,
    )
