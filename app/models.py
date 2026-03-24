from . import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    exercises = db.relationship('Exercise', backref='workout', lazy=True)
    sessions = db.relationship('WorkoutSession', backref='workout', lazy=True)


class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'))

    progress = db.relationship(
        'Progress',
        backref='exercise',
        lazy=True,
        order_by='Progress.id',
    )


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float)
    reps = db.Column(db.Integer)

    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'))
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=True)
