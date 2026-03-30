"""
ClassFlow Backend — Flask + MySQL
Updated to match ClassFlow frontend exactly
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY']                     = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY']                 = os.getenv('JWT_SECRET_KEY', 'dev-jwt-key')
app.config['SQLALCHEMY_DATABASE_URI']        = os.getenv('DATABASE_URL', 'postgresql+psycopg2://root:password@localhost:3306/classflow')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES']       = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH']             = 100 * 1024 * 1024  # 100 MB

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt    = JWTManager(app)
CORS(app, origins='*')


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.Enum('student', 'teacher'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments      = db.relationship('Enrollment',     backref='student', lazy=True)
    submissions      = db.relationship('Submission',     backref='student', lazy=True)
    announcements    = db.relationship('Announcement',   backref='author',  lazy=True)
    stream_comments  = db.relationship('StreamComment',  backref='author',  lazy=True)
    private_comments = db.relationship('PrivateComment', backref='author',  lazy=True)

    def to_dict(self):
        ini = ''.join([w[0] for w in self.name.split() if w])[:2].upper()
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role, 'initials': ini}


class Subject(db.Model):
    __tablename__ = 'subjects'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    code       = db.Column(db.String(20),  unique=True, nullable=False)
    color      = db.Column(db.String(10),  default='#378ADD')
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher       = db.relationship('User', foreign_keys=[teacher_id])
    enrollments   = db.relationship('Enrollment',   backref='subject', lazy=True)
    assignments   = db.relationship('Assignment',   backref='subject', lazy=True)
    announcements = db.relationship('Announcement', backref='subject', lazy=True)

    def to_dict(self, student_id=None):
        teacher = User.query.get(self.teacher_id)
        grade, pending = None, 0
        if student_id:
            assignments = Assignment.query.filter_by(subject_id=self.id).all()
            graded_subs = Submission.query.filter_by(student_id=student_id, status='graded').join(Assignment).filter(Assignment.subject_id == self.id).all()
            scores = [s.score for s in graded_subs if s.score is not None]
            if scores: grade = round(sum(scores) / len(scores))
            pending = sum(1 for a in assignments if not Submission.query.filter_by(student_id=student_id, assignment_id=a.id).first())
        return {'id': self.id, 'name': self.name, 'code': self.code, 'color': self.color,
                'professor': teacher.name if teacher else '', 'grade': grade, 'pending': pending}


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    joined_at  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', name='unique_enrollment'),)


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject_id  = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    due_date    = db.Column(db.DateTime, nullable=False)
    points      = db.Column(db.Integer, default=100)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

    def to_dict(self, student_id=None):
        now, due = datetime.utcnow(), self.due_date
        status, score = 'pending', None
        if student_id:
            sub = Submission.query.filter_by(student_id=student_id, assignment_id=self.id).first()
            if sub: status, score = sub.status, sub.score
        if due.date() == now.date():           due_label = f"Today {due.strftime('%I:%M %p')}"
        elif due.date() == (now + timedelta(days=1)).date(): due_label = f"Tomorrow {due.strftime('%I:%M %p')}"
        elif due < now and status != 'pending': due_label = 'Submitted'
        else:                                  due_label = due.strftime('%d %b')
        return {'id': self.id, 'title': self.title, 'description': self.description or '',
                'subject': self.subject_id, 'due': due_label, 'due_date': due.isoformat(),
                'points': self.points, 'status': status, 'score': score}


class Submission(db.Model):
    __tablename__ = 'submissions'
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'),       nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    file_links    = db.Column(db.Text)       # comma-separated links/filenames
    text_answer   = db.Column(db.Text)       # typed answer
    status        = db.Column(db.Enum('submitted', 'graded'), default='submitted')
    score         = db.Column(db.Integer)
    feedback      = db.Column(db.Text)       # teacher written feedback
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    graded_at     = db.Column(db.DateTime)
    private_comments = db.relationship('PrivateComment', backref='submission', lazy=True)
    __table_args__ = (db.UniqueConstraint('student_id', 'assignment_id', name='unique_submission'),)

    def to_dict(self):
        student = User.query.get(self.student_id)
        ini     = ''.join([w[0] for w in student.name.split() if w])[:2].upper() if student else 'UK'
        links   = [l.strip() for l in self.file_links.split(',')] if self.file_links else []
        return {'id': self.id, 'student_id': self.student_id, 'student_name': student.name if student else '',
                'initials': ini, 'assignment_id': self.assignment_id, 'file_links': links,
                'text_answer': self.text_answer or '', 'status': self.status, 'score': self.score,
                'feedback': self.feedback or '',
                'submitted_at': self.submitted_at.strftime('%d %b, %I:%M %p'),
                'graded_at': self.graded_at.strftime('%d %b, %I:%M %p') if self.graded_at else None}


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    body       = db.Column(db.Text, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    author_id  = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    type       = db.Column(db.Enum('announcement', 'material', 'assignment'), default='announcement')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stream_comments = db.relationship('StreamComment', backref='announcement', lazy=True)

    def to_dict(self):
        author  = User.query.get(self.author_id)
        subject = Subject.query.get(self.subject_id) if self.subject_id else None
        ini     = ''.join([w[0] for w in author.name.split() if w])[:2].upper() if author else 'UK'
        return {'id': self.id, 'title': self.title, 'body': self.body,
                'subject': subject.code if subject else 'all', 'subject_id': self.subject_id,
                'author': author.name if author else '', 'initials': ini,
                'color': subject.color if subject else '#1a5a9a', 'type': self.type,
                'time': self.created_at.strftime('%b %d'),
                'comments': [c.to_dict() for c in self.stream_comments]}


class StreamComment(db.Model):
    """Public stream comments visible to entire class."""
    __tablename__ = 'stream_comments'
    id              = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id'), nullable=False)
    author_id       = db.Column(db.Integer, db.ForeignKey('users.id'),         nullable=False)
    text            = db.Column(db.Text, nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        author = User.query.get(self.author_id)
        ini    = ''.join([w[0] for w in author.name.split() if w])[:2].upper() if author else 'UK'
        return {'author': author.name if author else '', 'initials': ini,
                'text': self.text, 'time': self.created_at.strftime('%b %d, %I:%M %p')}


class PrivateComment(db.Model):
    """Private comments between student and teacher on a submission."""
    __tablename__ = 'private_comments'
    id            = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    author_id     = db.Column(db.Integer, db.ForeignKey('users.id'),       nullable=False)
    text          = db.Column(db.Text, nullable=False)
    role          = db.Column(db.Enum('student', 'teacher'), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        author = User.query.get(self.author_id)
        ini    = ''.join([w[0] for w in author.name.split() if w])[:2].upper() if author else 'UK'
        return {'author': author.name if author else '', 'initials': ini,
                'text': self.text, 'role': self.role,
                'time': self.created_at.strftime('%b %d, %I:%M %p')}


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def detect_role(email):
    email = email.lower()
    return 'teacher' if ('faculty' in email or 'prof' in email or 'teacher' in email) else 'student'

def error(msg, code=400): return jsonify({'error': msg}), code
def ok(data, code=200):   return jsonify(data), code


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data     = request.get_json()
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not name or not email or not password: return error('Name, email and password are required')
    if len(password) < 6:                    return error('Password must be at least 6 characters')
    if User.query.filter_by(email=email).first(): return error('Email already registered')
    role = detect_role(email)
    user = User(name=name, email=email, password=bcrypt.generate_password_hash(password).decode('utf-8'), role=role)
    db.session.add(user); db.session.commit()
    return ok({'token': create_access_token(identity=str(user.id)), 'user': user.to_dict()}, 201)


@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    user     = User.query.filter_by(email=email).first()
    if not user: return error('Invalid email or password', 401)
    # Allow password-less demo login in development
    skip_pw = os.getenv('FLASK_ENV') == 'development' and not password
    if not skip_pw and not bcrypt.check_password_hash(user.password, password):
        return error('Invalid email or password', 401)
    return ok({'token': create_access_token(identity=str(user.id)), 'user': user.to_dict()})


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    return ok(user.to_dict()) if user else error('User not found', 404)


# ─────────────────────────────────────────
# SUBJECTS
# ─────────────────────────────────────────

@app.route('/api/subjects', methods=['GET'])
@jwt_required()
def get_subjects():
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role == 'teacher':
        return ok([s.to_dict() for s in Subject.query.filter_by(teacher_id=uid).all()])
    enrollments = Enrollment.query.filter_by(student_id=uid).all()
    subjects    = [Subject.query.get(e.subject_id) for e in enrollments]
    return ok([s.to_dict(student_id=uid) for s in subjects if s])


@app.route('/api/subjects', methods=['POST'])
@jwt_required()
def create_subject():
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'teacher': return error('Only teachers can create subjects', 403)
    data  = request.get_json()
    name  = data.get('name', '').strip()
    code  = data.get('code', '').strip().upper()
    color = data.get('color', '#378ADD')
    if not name or not code: return error('Name and code are required')
    if Subject.query.filter_by(code=code).first(): return error('Subject code already exists')
    s = Subject(name=name, code=code, color=color, teacher_id=uid)
    db.session.add(s); db.session.commit()
    return ok(s.to_dict(), 201)


@app.route('/api/subjects/join', methods=['POST'])
@jwt_required()
def join_subject():
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'student': return error('Only students can join subjects', 403)
    code    = request.get_json().get('code', '').strip().upper()
    subject = Subject.query.filter_by(code=code).first()
    if not subject: return error('Subject code not found')
    if Enrollment.query.filter_by(student_id=uid, subject_id=subject.id).first():
        return error('Already enrolled in this subject')
    db.session.add(Enrollment(student_id=uid, subject_id=subject.id)); db.session.commit()
    return ok({'message': f'Joined {subject.name} successfully', 'subject': subject.to_dict(uid)}, 201)


@app.route('/api/subjects/<int:subject_id>/students', methods=['GET'])
@jwt_required()
def get_students(subject_id):
    enrollments = Enrollment.query.filter_by(subject_id=subject_id).all()
    return ok([User.query.get(e.student_id).to_dict() for e in enrollments if User.query.get(e.student_id)])


# ─────────────────────────────────────────
# ASSIGNMENTS
# ─────────────────────────────────────────

@app.route('/api/assignments', methods=['GET'])
@jwt_required()
def get_assignments():
    uid        = int(get_jwt_identity())
    user       = User.query.get(uid)
    subject_id = request.args.get('subject_id')
    if user.role == 'student':
        enrollments = Enrollment.query.filter_by(student_id=uid).all()
        sids = [e.subject_id for e in enrollments]
        if subject_id: sids = [int(subject_id)] if int(subject_id) in sids else []
        assigns = Assignment.query.filter(Assignment.subject_id.in_(sids)).order_by(Assignment.due_date).all()
        return ok([a.to_dict(student_id=uid) for a in assigns])
    else:
        if subject_id:
            assigns = Assignment.query.filter_by(subject_id=subject_id).order_by(Assignment.due_date).all()
        else:
            sids    = [s.id for s in Subject.query.filter_by(teacher_id=uid).all()]
            assigns = Assignment.query.filter(Assignment.subject_id.in_(sids)).order_by(Assignment.due_date).all()
        return ok([a.to_dict() for a in assigns])


@app.route('/api/assignments', methods=['POST'])
@jwt_required()
def create_assignment():
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'teacher': return error('Only teachers can create assignments', 403)
    data = request.get_json()
    title, subject_id, due_date = data.get('title','').strip(), data.get('subject_id'), data.get('due_date')
    if not title or not subject_id or not due_date: return error('Title, subject and due date are required')
    subject = Subject.query.get(subject_id)
    if not subject or subject.teacher_id != uid: return error('Subject not found or not yours', 403)
    a = Assignment(title=title, description=data.get('description',''), subject_id=subject_id,
                   due_date=datetime.fromisoformat(due_date), points=data.get('points', 100))
    db.session.add(a); db.session.commit()
    return ok(a.to_dict(), 201)


# ─────────────────────────────────────────
# SUBMISSIONS
# ─────────────────────────────────────────

@app.route('/api/submissions', methods=['POST'])
@jwt_required()
def submit_assignment():
    """Student hands in assignment. Matches finalSubmit() in submission.js"""
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'student': return error('Only students can submit assignments', 403)
    data          = request.get_json()
    assignment_id = data.get('assignment_id')
    file_links    = data.get('file_links', '')   # comma-separated
    text_answer   = data.get('text_answer', '')
    if not assignment_id:                    return error('Assignment ID is required')
    if not file_links and not text_answer:   return error('Please add at least one file, link, or answer')
    assignment = Assignment.query.get(assignment_id)
    if not assignment: return error('Assignment not found', 404)
    if not Enrollment.query.filter_by(student_id=uid, subject_id=assignment.subject_id).first():
        return error('You are not enrolled in this subject', 403)
    if Submission.query.filter_by(student_id=uid, assignment_id=assignment_id).first():
        return error('Already submitted. Unsubmit first to resubmit.')
    sub = Submission(student_id=uid, assignment_id=assignment_id,
                     file_links=file_links, text_answer=text_answer, status='submitted')
    db.session.add(sub); db.session.commit()
    return ok({'message': 'Assignment submitted successfully', 'submission': sub.to_dict()}, 201)


@app.route('/api/submissions/<int:assignment_id>/mine', methods=['GET'])
@jwt_required()
def get_my_submission(assignment_id):
    """Student fetches their own submission for an assignment."""
    uid = int(get_jwt_identity())
    sub = Submission.query.filter_by(student_id=uid, assignment_id=assignment_id).first()
    return ok(sub.to_dict() if sub else None)


@app.route('/api/submissions/<int:submission_id>/unsubmit', methods=['DELETE'])
@jwt_required()
def unsubmit(submission_id):
    """Student recalls submission. Matches unsubmitAssignment() in submission.js"""
    uid        = int(get_jwt_identity())
    submission = Submission.query.get(submission_id)
    if not submission:                    return error('Submission not found', 404)
    if submission.student_id != uid:      return error('Not your submission', 403)
    if submission.status == 'graded':     return error('Cannot unsubmit a graded assignment', 400)
    db.session.delete(submission); db.session.commit()
    return ok({'message': 'Submission recalled successfully'})


@app.route('/api/submissions/<int:assignment_id>', methods=['GET'])
@jwt_required()
def get_submissions(assignment_id):
    """Teacher gets all submissions for an assignment."""
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'teacher': return error('Only teachers can view all submissions', 403)
    assignment = Assignment.query.get(assignment_id)
    if not assignment: return error('Assignment not found', 404)
    subject = Subject.query.get(assignment.subject_id)
    if not subject or subject.teacher_id != uid: return error('Not your assignment', 403)
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    enrolled    = Enrollment.query.filter_by(subject_id=assignment.subject_id).count()
    missing_ids = set(e.student_id for e in Enrollment.query.filter_by(subject_id=assignment.subject_id).all()) \
                  - set(s.student_id for s in submissions)
    return ok({'submissions': [s.to_dict() for s in submissions], 'total_enrolled': enrolled,
               'total_submitted': len(submissions),
               'missing_students': [User.query.get(sid).to_dict() for sid in missing_ids if User.query.get(sid)]})


@app.route('/api/submissions/grade', methods=['POST'])
@jwt_required()
def grade_submission():
    """Teacher grades and returns. Matches returnGradeToStudent() in submission.js"""
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'teacher': return error('Only teachers can grade', 403)
    data          = request.get_json()
    submission_id = data.get('submission_id')
    score         = data.get('score')
    feedback      = data.get('feedback', '')
    if score is None or not (0 <= int(score) <= 100): return error('Score must be 0–100')
    submission = Submission.query.get(submission_id)
    if not submission: return error('Submission not found', 404)
    assignment = Assignment.query.get(submission.assignment_id)
    subject    = Subject.query.get(assignment.subject_id)
    if subject.teacher_id != uid: return error('Not your assignment', 403)
    submission.score = int(score); submission.feedback = feedback
    submission.status = 'graded'; submission.graded_at = datetime.utcnow()
    db.session.commit()
    return ok({'message': f'Graded — {score}/100', 'submission': submission.to_dict()})


@app.route('/api/grades', methods=['GET'])
@jwt_required()
def get_grades():
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'student': return error('Students only', 403)
    result = []
    for e in Enrollment.query.filter_by(student_id=uid).all():
        subject = Subject.query.get(e.subject_id)
        graded  = Submission.query.filter_by(student_id=uid, status='graded').join(Assignment).filter(Assignment.subject_id == subject.id).all()
        scores  = [s.score for s in graded if s.score is not None]
        result.append({'subject_id': subject.id, 'subject_name': subject.name, 'color': subject.color,
                        'grade': round(sum(scores)/len(scores)) if scores else None, 'graded_count': len(graded)})
    scored  = [r['grade'] for r in result if r['grade'] is not None]
    overall = round(sum(scored)/len(scored)) if scored else None
    return ok({'grades': result, 'overall_average': overall})


# ─────────────────────────────────────────
# PRIVATE COMMENTS
# ─────────────────────────────────────────

@app.route('/api/submissions/<int:submission_id>/private-comments', methods=['GET'])
@jwt_required()
def get_private_comments(submission_id):
    """Visible only to the student who submitted and the teacher."""
    uid        = int(get_jwt_identity())
    submission = Submission.query.get(submission_id)
    if not submission: return error('Submission not found', 404)
    assignment = Assignment.query.get(submission.assignment_id)
    subject    = Subject.query.get(assignment.subject_id)
    if submission.student_id != uid and subject.teacher_id != uid: return error('Access denied', 403)
    comments = PrivateComment.query.filter_by(submission_id=submission_id).order_by(PrivateComment.created_at).all()
    return ok([c.to_dict() for c in comments])


@app.route('/api/submissions/<int:submission_id>/private-comments', methods=['POST'])
@jwt_required()
def add_private_comment(submission_id):
    """Matches addPrivateComment() and addTeacherPrivateComment() in submission.js"""
    uid        = int(get_jwt_identity())
    user       = User.query.get(uid)
    submission = Submission.query.get(submission_id)
    if not submission: return error('Submission not found', 404)
    assignment = Assignment.query.get(submission.assignment_id)
    subject    = Subject.query.get(assignment.subject_id)
    if submission.student_id != uid and subject.teacher_id != uid: return error('Access denied', 403)
    text = request.get_json().get('text', '').strip()
    if not text: return error('Comment text is required')
    c = PrivateComment(submission_id=submission_id, author_id=uid, text=text, role=user.role)
    db.session.add(c); db.session.commit()
    return ok(c.to_dict(), 201)


# ─────────────────────────────────────────
# ANNOUNCEMENTS
# ─────────────────────────────────────────

@app.route('/api/announcements', methods=['GET'])
@jwt_required()
def get_announcements():
    uid        = int(get_jwt_identity())
    user       = User.query.get(uid)
    subject_id = request.args.get('subject_id')
    if subject_id:
        anns = Announcement.query.filter_by(subject_id=subject_id).order_by(Announcement.created_at.desc()).all()
    elif user.role == 'student':
        sids = [e.subject_id for e in Enrollment.query.filter_by(student_id=uid).all()]
        anns = Announcement.query.filter((Announcement.subject_id.in_(sids)) | (Announcement.subject_id.is_(None))).order_by(Announcement.created_at.desc()).all()
    else:
        sids = [s.id for s in Subject.query.filter_by(teacher_id=uid).all()]
        anns = Announcement.query.filter(Announcement.subject_id.in_(sids)).order_by(Announcement.created_at.desc()).all()
    return ok([a.to_dict() for a in anns])


@app.route('/api/announcements', methods=['POST'])
@jwt_required()
def post_announcement():
    """Matches postAnnouncement() in script.js"""
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'teacher': return error('Only teachers can post announcements', 403)
    data       = request.get_json()
    title      = data.get('title', '').strip()
    body       = data.get('body', '').strip()
    subject_id = data.get('subject_id')
    ann_type   = data.get('type', 'announcement')
    if not title or not body: return error('Title and body are required')
    # Resolve subject name string to ID (frontend sends class name from dropdown)
    if subject_id and isinstance(subject_id, str) and not str(subject_id).isdigit():
        s = Subject.query.filter_by(name=subject_id).first()
        subject_id = s.id if s else None
    ann = Announcement(title=title, body=body, subject_id=subject_id or None, author_id=uid, type=ann_type)
    db.session.add(ann); db.session.commit()
    return ok(ann.to_dict(), 201)


@app.route('/api/announcements/<int:ann_id>/comments', methods=['POST'])
@jwt_required()
def add_stream_comment(ann_id):
    """Public class stream comment. Matches addClassComment() in script.js"""
    uid  = int(get_jwt_identity())
    text = request.get_json().get('text', '').strip()
    if not text: return error('Comment text is required')
    ann = Announcement.query.get(ann_id)
    if not ann: return error('Announcement not found', 404)
    c = StreamComment(announcement_id=ann_id, author_id=uid, text=text)
    db.session.add(c); db.session.commit()
    return ok(c.to_dict(), 201)


# ─────────────────────────────────────────
# DASHBOARDS
# ─────────────────────────────────────────

@app.route('/api/dashboard/student', methods=['GET'])
@jwt_required()
def student_dashboard():
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if user.role != 'student': return error('Students only', 403)
    enrollments = Enrollment.query.filter_by(student_id=uid).all()
    sids        = [e.subject_id for e in enrollments]
    all_assigns = Assignment.query.filter(Assignment.subject_id.in_(sids)).order_by(Assignment.due_date).all()
    pending     = [a.to_dict(student_id=uid) for a in all_assigns
                   if not Submission.query.filter_by(student_id=uid, assignment_id=a.id).first()]
    graded_subs = Submission.query.filter_by(student_id=uid, status='graded').order_by(Submission.graded_at.desc()).limit(5).all()
    graded      = [s.assignment.to_dict(student_id=uid) for s in graded_subs]
    all_graded  = Submission.query.filter_by(student_id=uid, status='graded').all()
    scores      = [s.score for s in all_graded if s.score is not None]
    avg         = round(sum(scores)/len(scores)) if scores else None
    now         = datetime.utcnow()
    due_week    = [p for p in pending if p['due_date'] and datetime.fromisoformat(p['due_date']) <= now + timedelta(days=7)]
    return ok({'name': user.name, 'classes_joined': len(enrollments), 'due_this_week': len(due_week),
               'avg_grade': avg, 'due_soon': pending[:3], 'recently_graded': graded})


@app.route('/api/dashboard/teacher', methods=['GET'])
@jwt_required()
def teacher_dashboard():
    uid      = int(get_jwt_identity())
    user     = User.query.get(uid)
    if user.role != 'teacher': return error('Teachers only', 403)
    subjects    = Subject.query.filter_by(teacher_id=uid).all()
    sids        = [s.id for s in subjects]
    all_students = set()
    for sid in sids:
        for e in Enrollment.query.filter_by(subject_id=sid).all(): all_students.add(e.student_id)
    assigns     = Assignment.query.filter(Assignment.subject_id.in_(sids)).all()
    assign_ids  = [a.id for a in assigns]
    pending_grading = Submission.query.filter(Submission.assignment_id.in_(assign_ids), Submission.status == 'submitted').count()
    total_subs  = Submission.query.filter(Submission.assignment_id.in_(assign_ids)).count()
    total_poss  = sum(Enrollment.query.filter_by(subject_id=a.subject_id).count() for a in assigns)
    sub_rate    = round((total_subs / total_poss) * 100) if total_poss else 0
    needs_grading = Submission.query.filter(Submission.assignment_id.in_(assign_ids), Submission.status == 'submitted').order_by(Submission.submitted_at.desc()).limit(5).all()
    tracker = []
    for a in sorted(assigns, key=lambda x: x.due_date, reverse=True)[:5]:
        sub = Subject.query.get(a.subject_id)
        enrl = Enrollment.query.filter_by(subject_id=a.subject_id).count()
        subm = Submission.query.filter_by(assignment_id=a.id).count()
        tracker.append({'id': a.id, 'title': a.title, 'subject': sub.name if sub else '',
                        'due': a.to_dict()['due'], 'enrolled': enrl, 'submitted': subm, 'missing': enrl - subm})
    return ok({'name': user.name, 'total_students': len(all_students), 'pending_grading': pending_grading,
               'submission_rate': sub_rate, 'needs_grading': [s.to_dict() for s in needs_grading],
               'assignment_tracker': tracker})


# ─────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    uid   = int(get_jwt_identity())
    user  = User.query.get(uid)
    notifs = []
    if user.role == 'student':
        sids  = [e.subject_id for e in Enrollment.query.filter_by(student_id=uid).all()]
        today = datetime.utcnow().date()
        for a in Assignment.query.filter(Assignment.subject_id.in_(sids), db.func.date(Assignment.due_date) == today).all():
            if not Submission.query.filter_by(student_id=uid, assignment_id=a.id).first():
                notifs.append({'type': 'danger', 'icon': '🚨', 'title': f'{a.title} due today',
                                'body': 'Not submitted yet', 'time': f"Today {a.due_date.strftime('%I:%M %p')}"})
        for s in Submission.query.filter_by(student_id=uid, status='graded').order_by(Submission.graded_at.desc()).limit(3).all():
            notifs.append({'type': 'success', 'icon': '🎯', 'title': f'{s.assignment.title} graded — {s.score}/100',
                           'body': 'Check your grades for feedback', 'time': s.graded_at.strftime('%b %d') if s.graded_at else ''})
        for a in Announcement.query.filter(Announcement.subject_id.in_(sids)).order_by(Announcement.created_at.desc()).limit(3).all():
            notifs.append({'type': 'warning', 'icon': '📢', 'title': a.title,
                           'body': (a.body[:80] + '...') if len(a.body) > 80 else a.body,
                           'time': a.created_at.strftime('%b %d')})
    return ok(notifs[:10])


# ─────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    return ok({'status': 'ok', 'message': 'ClassFlow API is running ✅'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ Database tables created')
    app.run(debug=True, port=5000)

@app.route('/api/seed-once', methods=['GET'])
def seed_once():
    from seed import seed
    seed()
    return jsonify({'status': 'seeded'})
