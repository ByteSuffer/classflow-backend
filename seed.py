"""
seed.py — Run once to populate the database with ClassFlow sample data.
Usage: python seed.py
All passwords: password123
"""

from app import app, db, bcrypt
from app import User, Subject, Enrollment, Assignment, Submission, Announcement, StreamComment
from datetime import datetime, timedelta


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print('🗑️  Cleared and recreated tables')

        # ── Teachers ──
        teacher_data = [
            ('Prof. R. Kumar',  'kumar@faculty.du.ac.in'),
            ('Prof. S. Mehta',  'mehta@faculty.du.ac.in'),
            ('Prof. A. Sharma', 'sharma@faculty.du.ac.in'),
            ('Prof. D. Verma',  'verma@faculty.du.ac.in'),
            ('Prof. M. Gupta',  'gupta@faculty.du.ac.in'),
            ('Prof. N. Singh',  'singh@faculty.du.ac.in'),
        ]
        teachers = []
        for name, email in teacher_data:
            t = User(name=name, email=email,
                     password=bcrypt.generate_password_hash('password123').decode('utf-8'),
                     role='teacher')
            db.session.add(t); teachers.append(t)

        # ── Students ──
        student_data = [
            ('Priya Sharma',  'priya@student.du.ac.in'),
            ('Rahul Kumar',   'rahul@student.du.ac.in'),
            ('Anjali Patel',  'anjali@student.du.ac.in'),
            ('Mohit Kumar',   'mohit@student.du.ac.in'),
            ('Sneha Verma',   'sneha@student.du.ac.in'),
        ]
        students = []
        for name, email in student_data:
            s = User(name=name, email=email,
                     password=bcrypt.generate_password_hash('password123').decode('utf-8'),
                     role='student')
            db.session.add(s); students.append(s)

        db.session.commit()
        print(f'✅ Created {len(teachers)} teachers, {len(students)} students')

        # ── Subjects ── (match frontend SUBJECTS exactly)
        subject_data = [
            ('Operating Systems',    'OS',    '#E24B4A', teachers[0]),
            ('Database Management',  'DBMS',  '#378ADD', teachers[1]),
            ('Computer Networks',    'CN',    '#1D9E75', teachers[2]),
            ('Engineering Maths',    'MATHS', '#BA7517', teachers[3]),
            ('Software Engineering', 'SE',    '#7F77DD', teachers[4]),
            ('HCI & Design',         'HCI',   '#D4537E', teachers[5]),
        ]
        subjects = []
        for name, code, color, teacher in subject_data:
            s = Subject(name=name, code=code, color=color, teacher_id=teacher.id)
            db.session.add(s); subjects.append(s)
        db.session.commit()
        print(f'✅ Created {len(subjects)} subjects')

        # ── Enroll all students in all subjects ──
        for student in students:
            for subject in subjects:
                db.session.add(Enrollment(student_id=student.id, subject_id=subject.id))
        db.session.commit()
        print('✅ Enrolled all students in all subjects')

        # ── Assignments ── (match frontend ASSIGNMENTS exactly)
        now = datetime.utcnow()
        assignment_data = [
            ('OS Lab Assignment 3',  subjects[0], now + timedelta(hours=6),    'OS Lab 3 instructions attached.'),
            ('DBMS Quiz 2',          subjects[1], now + timedelta(days=1),     'Covers B+ Trees and Hashing.'),
            ('HCI Project Proposal', subjects[5], now + timedelta(days=2),     '1000-1500 words. Include research plan.'),
            ('SE Report',            subjects[4], now + timedelta(days=3),     'Cover all UML diagrams.'),
            ('CN Lab Report 2',      subjects[2], now - timedelta(days=2),     'Already submitted.'),
            ('CN Mid-term',          subjects[2], now - timedelta(days=7),     'Mid-term exam.'),
            ('Maths Assignment 4',   subjects[3], now - timedelta(days=5),     'Chapter 7 problems.'),
        ]
        assignments = []
        for title, subject, due, desc in assignment_data:
            a = Assignment(title=title, description=desc, subject_id=subject.id, due_date=due, points=100)
            db.session.add(a); assignments.append(a)
        db.session.commit()
        print(f'✅ Created {len(assignments)} assignments')

        # ── Submissions for Priya (student[0]) ──
        priya = students[0]

        # CN Lab Report — submitted
        db.session.add(Submission(
            student_id=priya.id, assignment_id=assignments[4].id,
            file_links='CN_Lab2_Report.pdf',
            status='submitted'
        ))
        # CN Mid-term — graded 82
        db.session.add(Submission(
            student_id=priya.id, assignment_id=assignments[5].id,
            file_links='CN_Midterm_Answers.pdf',
            status='graded', score=82, feedback='Well done! Strong on routing protocols.',
            graded_at=now - timedelta(days=1)
        ))
        # Maths — graded 61
        db.session.add(Submission(
            student_id=priya.id, assignment_id=assignments[6].id,
            file_links='Maths_HW4.pdf',
            status='graded', score=61, feedback='Review integration techniques.',
            graded_at=now - timedelta(days=2)
        ))

        # Other students submitted OS Lab (for teacher grade queue)
        for student in students[:3]:
            db.session.add(Submission(
                student_id=student.id, assignment_id=assignments[0].id,
                file_links=f'{student.name.split()[0].lower()}_os_lab3.cpp,lab3_report.pdf',
                status='submitted'
            ))

        db.session.commit()
        print('✅ Created sample submissions')

        # ── Announcements ── (match frontend STREAM_POSTS)
        ann_data = [
            ('Task 4 and Task 5 Demo/Evaluation',
             'All students are requested to attend the Task 4 evaluation during today\'s tutorial class. Task 5 Demo/evaluation will be done on 19-03-2026.',
             subjects[5], teachers[5], 'announcement', now - timedelta(days=6)),
            ('W8-9: B+ Trees and Hashing',
             'New study material posted for Week 8-9 covering B+ Trees and Hashing algorithms. Please review before next lecture.',
             subjects[1], teachers[1], 'material', now - timedelta(days=2)),
            ('OS Lab Assignment 3 — Due Today',
             'Reminder: OS Lab Assignment 3 is due today at 11:59 PM. Submit your solution file via the Assignments tab.',
             subjects[0], teachers[0], 'assignment', now - timedelta(hours=6)),
            ('CN Mid-term Results Published',
             'Mid-term results have been published. Class average was 78%. Check your individual score in the Grades section.',
             subjects[2], teachers[2], 'material', now - timedelta(days=3)),
            ('SE Report deadline extended',
             'The Software Engineering Report deadline has been extended to 20th March. Make sure your report covers all UML diagrams.',
             subjects[4], teachers[4], 'announcement', now - timedelta(days=4)),
        ]
        announcements = []
        for title, body, subject, author, ann_type, created in ann_data:
            a = Announcement(title=title, body=body, subject_id=subject.id,
                             author_id=author.id, type=ann_type, created_at=created)
            db.session.add(a); announcements.append(a)
        db.session.commit()

        # ── Stream comments on first announcement ──
        db.session.add(StreamComment(announcement_id=announcements[0].id, author_id=priya.id,
                                     text='Thank you for the update!', created_at=now - timedelta(days=6, hours=-1)))
        db.session.add(StreamComment(announcement_id=announcements[0].id, author_id=students[1].id,
                                     text='+1', created_at=now - timedelta(days=6, hours=-2)))
        db.session.add(StreamComment(announcement_id=announcements[2].id, author_id=students[4].id,
                                     text='Submitted!', created_at=now - timedelta(hours=5)))
        db.session.commit()
        print('✅ Created announcements and stream comments')

        print('\n🎉 Database seeded successfully!')
        print('\n── Login credentials ──')
        print('Student:  priya@student.du.ac.in  /  password123')
        print('Teacher:  kumar@faculty.du.ac.in  /  password123')
        print('All users have the same password: password123')
        print('\nSubject codes for "Join class": OS, DBMS, CN, MATHS, SE, HCI')


if __name__ == '__main__':
    seed()
