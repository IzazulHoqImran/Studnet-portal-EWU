import MySQLdb
from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, SelectField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import mysql.connector


app = Flask(__name__)
app.secret_key = 'f3cfe9ed8fae309f02079dbf'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'course'

mysql = MySQL(app)

@app.route('/')
def index():
        return render_template('index.html')

@app.route('/aboutus')
def aboutus():
        return render_template('aboutus.html')

@app.route('/contactus')
def contactus():
        return render_template('contactus.html')



class SignUpForm(Form):
    name = StringField('Name', [validators.Length(min=4, max=100)])
    email = StringField('Email', [validators.Length(min=6, max=100)])
    role = SelectField('Role', choices=[('Student', 'Student'), ('Teacher', 'Teacher') ])
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match'),validators.Length(min=6, max=100)
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        role = form.role.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        result = cur.execute("SELECT * FROM users WHERE username=%s", [username])
        if result > 0:
            flash('The entered username already exists.Please try using another username.', 'info')
            return redirect(url_for('signup'))
        else:
            cur.execute("INSERT INTO users(name , email, role, username, password) VALUES(%s, %s, %s, %s, %s)",
                    (name, email, role, username, password))
            mysql.connection.commit()
            cur.close()
            flash('You are now registered and can log in', 'success')
            return redirect(url_for('login'))
    return render_template('signUp.html', form=form)

class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
    ])


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password_input = form.password.data

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            userID = data["id"]
            password = data['password']
            role = data['role']

            if sha256_crypt.verify(password_input, password):
                session['logged_in'] = True
                session['username'] = username
                session['role'] = role
                session['userID'] = userID
                flash('You are now logged in', 'success')
                if session['role'] == 'Student':
                    return redirect(url_for('s_login'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', form=form, error=error)

            cur.close()

        else:
            error = 'Username not found'
            return render_template('login.html', form=form, error=error)

    return render_template('login.html', form=form)


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please login', 'info')
            return redirect(url_for('login'))
    return wrap


def is_teacher(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['role'] == 'Teacher':
            return f(*args, **kwargs)
        else:
            flash('You are not a Teacher', 'danger')
            return redirect(url_for('add_complaint'))
    return wrap

def is_student(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['role'] == 'Student':
            return f(*args, **kwargs)
        else:
            flash('You are not a Student', 'danger')
            return redirect(url_for('add_complaint'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/s_login')
@is_logged_in
@is_student
def s_login():

    return render_template('s_login.html')

@app.route('/dashboard')
@is_logged_in
@is_teacher
def dashboard():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute(f"SELECT * FROM courseware WHERE user_id = {session['userID']}")
    courses = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', courses=courses)
    else:
        msg = 'No courses have been created'
        return render_template('dashboard.html', msg=msg)
    cur.close()



@app.route('/all_student')
@is_logged_in
@is_teacher
def all_student():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute(f"SELECT * FROM users WHERE (role = 'Student' )")
    courses = cur.fetchall()
    if result > 0:
        return render_template('all_student.html', courses=courses)
    else:
        msg = 'No student have been regristed'
        return render_template('all_student.html', msg=msg)
    cur.close()


@app.route('/all_courses')
@is_logged_in
@is_student
def stud_courses():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute(f"SELECT * FROM courseware")
    courses = cur.fetchall()
    if result > 0:
        return render_template('all_courses.html', courses=courses)
    else:
        msg = 'No courses have been created'
        return render_template('index.html', msg=msg)
    cur.close()

class CourseForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    subject = StringField('Course Code', [validators.Length(min=1, max=200)])
    description = StringField('Department', [validators.Length(min=1, max=200)])
    body = TextAreaField('About this course', [validators.Length(min=20)])


@app.route('/add_course', methods=['GET', 'POST'])
@is_logged_in
@is_teacher
def add_course():
    form = CourseForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        subject = form.subject.data
        description = form.description.data
        body = form.body.data

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("INSERT INTO courseware(user_id, title, subject, description, body, author) VALUES(%s, %s, %s, %s, %s, %s)",
                    (session['userID'], title, subject, description, body, session['username']))

        mysql.connection.commit()
        cur.close()

        flash('Your courseware has been registered', 'success')
        if session['role'] == 'Teacher':
            return redirect(url_for('dashboard'))
    return render_template('add_course.html', form=form)

@app.route('/review_course/<string:id>', methods=['GET', 'POST'])
@is_logged_in
@is_teacher
def review_course(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute("SELECT * FROM courseware WHERE id = %s", [id])
    courses = cur.fetchall()
    if result > 0:
        return render_template('detail_page.html', courses=courses)
    else:
        msg = 'The Course is empty and cannot be reviewed'
        return render_template('dashboard.html', msg=msg)
    cur.close()

@app.route('/entered_course/<string:title>', methods=['GET', 'POST'])
@is_logged_in
def entered_course(title):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute("""SELECT
                            users.name,
                            student_courses.id,
                            student_courses.status,
                            student_courses.enroll_date,
                            courseware.id,
                            courseware.title,
                            courseware.description,
                            courseware.body,
                            courseware.subject,
                            courseware.issue_date,
                            courseware.author
                            FROM student_courses
                            INNER JOIN courseware on courseware.id = student_courses.courseware_id
                            INNER JOIN users on users.id = student_courses.user_id
                            WHERE title = %s""", [title])
    courses = cur.fetchall()
    if result > 0:
        return render_template('detail_page.html', courses=courses)
    else:
        msg = 'The Course is empty and cannot be reviewed'
        return render_template('index.html', msg=msg)
    cur.close()

@app.route('/enrolled_students/<string:id>', methods=['GET', 'POST'])
@is_logged_in
@is_teacher
def enrolled_students(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute("SELECT COUNT(ID) from course.student_courses WHERE status = 'open' and courseware_id = %s", [id])
    data = cur.fetchone()
    total = data['COUNT(ID)']
    if result>0:
        return render_template('total.html', total=total)
    else:
        msg = 'No one has enrolled for this course yet!'
        return render_template('dashboard.html', msg=msg)
    cur.close()

@app.route('/enrolled/<string:id>', methods=['GET', 'POST'])
@is_logged_in
@is_student
def enrolled(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("INSERT INTO student_courses(user_id, courseware_id) VALUES(%s, %s)",
                    (session['userID'], [id]))
    mysql.connection.commit()
    cur.close()
    if session['role'] == 'Student':
        flash('You are now enrolled for the course', 'success')
        return redirect(url_for('my_courses'))
    return render_template('all_courses.html')

@app.route('/my_courses')
@is_logged_in
@is_student
def my_courses():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    result = cur.execute(f"""
                            SELECT
                            users.name,
                            student_courses.id,
                            student_courses.status,
                            student_courses.enroll_date,
                            courseware.id,
                            courseware.title,
                            courseware.description,
                            courseware.subject,
                            courseware.issue_date,
                            courseware.author
                            FROM student_courses
                            INNER JOIN courseware on courseware.id = student_courses.courseware_id
                            INNER JOIN users on users.id = student_courses.user_id 
                            WHERE users.id = {session['userID']}
                            """)
    courses = cur.fetchall()
    if result > 0:
        return render_template('my_courses.html', courses=courses)
    else:
        msg = 'You have not enrolled in any of the courses'
        return render_template('all_courses.html', msg=msg)
    cur.close()

@app.route('/edit_course/<string:id>', methods=['GET', 'POST'])
@is_logged_in
@is_teacher
def edit_course(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM courseware WHERE id = %s", [id])
    course = cur.fetchone()
    cur.close()
    form = CourseForm(request.form)
    form.title.data = course['title']
    form.subject.data = course['subject']
    form.description.data = course['description']
    form.body.data = course['body']
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        subject = request.form['subject']
        description = request.form['description']
        body = request.form['body']

        cur = mysql.connection.cursor()

        cur.execute ("UPDATE courseware SET title=%s, subject=%s, description=%s, body=%s WHERE id=%s",(title, subject, description, body, id))

        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Course Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_course.html', form=form)

@app.route('/std_edit/<string:id>', methods=['GET', 'POST'])
@is_logged_in
@is_teacher
def std_edit(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", [id])
    user = cur.fetchone()
    cur.close()
    form = SignUpForm(request.form)
    form.name.data = user['name']
    form.email.data = user['email']
    form.username.data = user['username']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']

        cur = mysql.connection.cursor()

        cur.execute("UPDATE users SET name=%s, email=%s, username=%s WHERE id=%s",(name, email, username, id))

        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Course Updated', 'success')

        return redirect(url_for('all_student'))

    return render_template('std_edit.html', form=form)




@app.route('/delete_course/<string:id>', methods=['POST'])
@is_logged_in
@is_teacher
def delete_course(id):
    # Create cursor
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Execute
    cur.execute("DELETE FROM courseware WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Course Deleted', 'success')

    return redirect(url_for('dashboard'))
@app.route('/delete_student/<string:id>', methods=['POST'])
@is_logged_in
@is_teacher
def delete_student(id):
    # Create cursor
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Execute
    cur.execute("DELETE FROM users WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Student Deleted', 'success')

    return redirect(url_for('all_student'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == "POST":
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        x = request.form['search']
        result=cur.execute(f"SELECT * FROM users WHERE name = '"+x+"'")
        courses = cur.fetchall()
        if result > 0:
            return render_template('all_student.html', courses=courses)
        else:
            msg = 'No student are found Search again'
            return render_template('all_student.html', msg=msg)
        cur.close()

        #c.executemany('''select * from student where name = %s''', request.form['search'])

        #return render_template("results.html", records=c.fetchall())
    #return render_template('search.html')
@app.route('/c_search', methods=['GET', 'POST'])
def c_search():
    if request.method == "POST":
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        x = request.form['c_search']
        result=cur.execute(f"SELECT * FROM courseware WHERE subject = '"+x+"'")
        courses = cur.fetchall()
        if result > 0:
            return render_template('all_courses.html', courses=courses)
        else:
            msg = 'No student are found Search again'
            return render_template('all_courses.html', msg=msg)
        cur.close()

@app.route('/d_search', methods=['GET', 'POST'])
def d_search():
    if request.method == "POST":
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        x = request.form['d_search']
        result=cur.execute(f"SELECT * FROM courseware WHERE title = '"+x+"'")
        courses = cur.fetchall()
        if result > 0:
            return render_template('all_courses.html', courses=courses)
        else:
            msg = 'No course are found Search again'
            return render_template('all_courses.html', msg=msg)
        cur.close()

@app.route('/unenroll_course/<string:id>', methods=['POST'])
@is_logged_in
@is_student
def unenroll_course(id):
    # Create cursor
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Execute
    cur.execute("DELETE FROM student_courses WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Unenrolled from course', 'success')

    return redirect(url_for('my_courses'))

if __name__ == '__main__':
    app.run(debug=True)