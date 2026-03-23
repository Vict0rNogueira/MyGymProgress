from flask import Blueprint, request, redirect, render_template
from flask_login import login_user, logout_user, login_required, current_user
from .models import Workout, User, Exercise, Progress, db

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def home():
    workouts = Workout.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', workouts=workouts)


@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect('/login')

    return '''
        <h1>Registro</h1>
        <form method="POST">
            <input name="username" placeholder="Usuário">
            <input name="password" type="password" placeholder="Senha">
            <button>Registrar</button>
        </form>
    '''


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            login_user(user)
            return redirect('/')

    return '''
        <h1>Login</h1>
        <form method="POST">
            <input name="username" placeholder="Usuário">
            <input name="password" type="password" placeholder="Senha">
            <button>Entrar</button>
        </form>
    '''


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


@main.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form['name']

    workout = Workout(
        name=name,
        user_id=current_user.id
    )

    db.session.add(workout)
    db.session.commit()

    return redirect('/')


@main.route('/delete/<int:id>')
@login_required
def delete(id):
    workout = Workout.query.get(id)

    if workout.user_id == current_user.id:
        db.session.delete(workout)
        db.session.commit()

    return redirect('/')

@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    workout = Workout.query.get(id)

    if workout.user_id != current_user.id:
        return redirect('/')

    if request.method == 'POST':
        workout.name = request.form['name']
        db.session.commit()
        return redirect('/')

    return f'''
        <h1>Editar treino</h1>

        <form method="POST">
            <input type="text" name="name" value="{workout.name}">
            <button type="submit">Salvar</button>
        </form>
    '''


@main.route('/add_progress/<int:exercise_id>', methods=['POST'])
@login_required
def add_progress(exercise_id):
    weight = request.form['weight']
    reps = request.form['reps']

    progress = Progress(
        weight=float(weight),
        reps=int(reps),
        exercise_id=exercise_id
    )

    db.session.add(progress)
    db.session.commit()

    return redirect('/')

@main.route('/add_exercise/<int:workout_id>', methods=['POST'])
@login_required
def add_exercise(workout_id):
    name = request.form['name']

    exercise = Exercise(
        name=name,
        workout_id=workout_id
    )

    db.session.add(exercise)
    db.session.commit()

    return redirect('/')

@main.route('/delete_exercise/<int:id>')
@login_required
def delete_exercise(id):
    exercise = Exercise.query.get(id)

    if exercise.workout.user_id == current_user.id:
        db.session.delete(exercise)
        db.session.commit()

    return redirect('/')

@main.route('/edit_exercise/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_exercise(id):
    exercise = Exercise.query.get(id)

    if exercise.workout.user_id != current_user.id:
        return redirect('/')

    if request.method == 'POST':
        exercise.name = request.form['name']
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

    if progress.exercise.workout.user_id == current_user.id:
        db.session.delete(progress)
        db.session.commit()

    return redirect('/')