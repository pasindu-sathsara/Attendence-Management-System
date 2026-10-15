"""Attendance system using the user's existing ten-table MySQL schema."""
import json, secrets, re, io, hmac
from pathlib import Path
from functools import wraps
from datetime import date
from flask import Flask, request, session, jsonify, render_template, redirect, g, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
import mysql.connector
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
secret_file = ROOT / '.session-secret'
if not secret_file.exists(): secret_file.write_text(secrets.token_hex(32))
app = Flask(__name__, template_folder=str(ROOT), static_folder='static')
app.config.update(SECRET_KEY=secret_file.read_text().strip(), MAX_CONTENT_LENGTH=5*1024*1024,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
TABLES = {'student':'student','lecturer':'lecturer','hod':'hod','ar':'ar_user'}

def db():
    if 'db' not in g:
        try: cfg=json.loads((ROOT/'config.json').read_text())
        except (FileNotFoundError, json.JSONDecodeError): abort(503, 'Run python setup.py to configure MySQL first.')
        g.db=mysql.connector.connect(**cfg, autocommit=False, connection_timeout=5, charset='utf8mb4')
    return g.db

def query(sql, args=(), one=False):
    cur=db().cursor(dictionary=True)
    try:
        cur.execute(sql,args)
        return cur.fetchone() if one else cur.fetchall()
    finally: cur.close()

def execute(sql,args=()):
    cur=db().cursor()
    try: cur.execute(sql,args); return cur.rowcount
    finally: cur.close()

@app.teardown_appcontext
def close_db(error):
    conn=g.pop('db',None)
    if conn: conn.close()

@app.before_request
def protect():
    session.setdefault('csrf',secrets.token_hex(32))
    if request.method in ('POST','PUT','DELETE','PATCH'):
        token=request.headers.get('X-CSRF-Token') or request.form.get('csrf','')
        if not hmac.compare_digest(str(token),session['csrf']): abort(403,'Refresh the page and try again.')

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    return response

@app.errorhandler(HTTPException)
def http_error(err):
    if request.path.startswith('/api/'): return jsonify(error=err.description),err.code
    return render_template('error.html',message=err.description),err.code

@app.errorhandler(mysql.connector.Error)
def database_error(err):
    if 'db' in g: g.db.rollback()
    app.logger.error('MySQL error %s',err.errno)
    messages={1062:'This record already exists. Dates/week numbers must be unique in your current session schema.',
              1452:'A referenced semester, course, student or staff account does not exist.',
              3819:'A value does not meet the database constraints.'}
    message=messages.get(err.errno,'Database unavailable. Check config.json and that MySQL Server is running.')
    if request.path.startswith('/api/'): return jsonify(error=message),400 if err.errno in messages else 503
    return render_template('error.html',message=message),503

def allowed(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            if not session.get('email'):
                if request.path.startswith('/api/'): abort(401,'Please sign in.')
                return redirect('/UI.html')
            if session.get('role') not in roles: abort(403,'You do not have access to this page or action.')
            if not query('SELECT email FROM '+TABLES[session['role']]+' WHERE email=%s',(session['email'],),True):
                session.clear(); abort(401,'Please sign in again.')
            return fn(*args,**kwargs)
        return wrapped
    return decorator

def data():
    value=request.get_json(silent=True)
    if not isinstance(value,dict): abort(400,'Invalid request.')
    return value

def text(value,limit=255):
    value=str(value or '').strip()
    if not value or len(value)>limit: abort(400,'A required value is missing or too long.')
    return value

def semester_key(value):
    parts=str(value).split('|')
    if len(parts)!=3: abort(400,'Choose a semester.')
    try: return (parts[0],int(parts[1]),int(parts[2]))
    except ValueError: abort(400,'Invalid semester.')

def semester_id(row): return f"{row['academic_year']}|{row['study_year']}|{row['semester_number']}"

def course_access(code):
    course=query('SELECT * FROM course WHERE course_code=%s',(code,),True)
    if not course: abort(404,'Module not found.')
    if session['role']=='lecturer' and not query('SELECT email FROM lecturer_course WHERE email=%s AND course_code=%s',(session['email'],code),True): abort(403,'This module is not assigned to you.')
    return course

def roster(course):
    return query('SELECT s.email,s.reg_number FROM student s JOIN student_semester e ON e.email=s.email WHERE e.academic_year=%s AND e.study_year=%s AND e.semester_number=%s ORDER BY s.reg_number',
                 (course['academic_year'],course['study_year'],course['semester_number']))

@app.route('/')
def home(): return redirect('/UI.html')
@app.get('/style.css')
def css(): return send_from_directory(ROOT,'style.css')
@app.get('/UI.html')
def login_page(): return render_template('UI.html')
@app.get('/student-register.html')
def register_page(): return render_template('student-register.html')
@app.get('/staff-register.html')
def staff_register(): return render_template('staff-register.html')
@app.get('/dashboard.html')
@app.get('/Dashboard.html')
@allowed('hod','lecturer','ar')
def dashboard(): return render_template('Dashboard.html')
@app.get('/student-dashboard.html')
@allowed('student')
def student_dashboard(): return render_template('student-dashboard.html')
@app.get('/manage-system.html')
@allowed('hod')
def manage(): return render_template('manage-system.html')
@app.get('/reports.html')
@allowed('hod','lecturer')
def reports(): return render_template('reports.html')
@app.post('/api/logout')
def logout(): session.clear(); return jsonify(ok=True)

@app.post('/api/login')
def login():
    d=data(); email=text(d.get('email')).lower(); password=str(d.get('password',''))
    roles=['student'] if d.get('kind')=='student' else ['hod','lecturer','ar']
    found=None
    for role in roles:
        row=query('SELECT email,name,password_hash FROM '+TABLES[role]+' WHERE email=%s',(email,),True)
        if row:
            try: valid=check_password_hash(row['password_hash'],password)
            except (ValueError,TypeError): valid=False
            if valid: found=(role,row);break
    if not found: abort(401,'Incorrect email or password. Sample TEST_HASH_ONLY accounts need a password set with setup.py.')
    session.clear();session.update(email=found[1]['email'],role=found[0],name=found[1]['name'],csrf=secrets.token_hex(32))
    return jsonify(next='/student-dashboard.html' if found[0]=='student' else '/dashboard.html')

@app.post('/api/register')
def register():
    d=data(); email=text(d.get('email')).lower(); reg=text(d.get('registration_number'),30); name=text(d.get('full_name'),100)
    pw=str(d.get('password',''))
    if '@' not in email or len(pw)<8 or pw!=d.get('confirm_password'): abort(400,'Enter a valid email and matching passwords of at least 8 characters.')
    # Activate only an existing student imported by the HOD, not a self-chosen identity.
    row=query('SELECT * FROM student WHERE email=%s AND reg_number=%s FOR UPDATE',(email,reg),True)
    if not row: abort(400,'Your details must first be imported by the HOD. Check your email and registration number.')
    if row['name'].strip().casefold()!=name.casefold(): abort(400,'Your name must match the imported student record.')
    # Placeholder/disabled credentials can only be activated with a one-time code issued locally.
    token=str(d.get('activation_code',''))
    try: codes=json.loads((ROOT/'.activation-codes.json').read_text())
    except (FileNotFoundError,json.JSONDecodeError): codes={}
    digest=codes.get(email)
    if not digest or not check_password_hash(digest,token): abort(400,'An activation code issued by staff is required.')
    execute('UPDATE student SET password_hash=%s WHERE email=%s',(generate_password_hash(pw),email));db().commit()
    codes.pop(email,None);(ROOT/'.activation-codes.json').write_text(json.dumps(codes))
    return jsonify(ok=True)

@app.get('/api/options')
@allowed('hod','lecturer','ar')
def options():
    courses=query('SELECT c.* FROM course c '+('JOIN lecturer_course lc ON lc.course_code=c.course_code WHERE lc.email=%s ' if session['role']=='lecturer' else '')+'ORDER BY c.academic_year,c.study_year,c.semester_number,c.course_code', (session['email'],) if session['role']=='lecturer' else ())
    sems={semester_id(c):dict(id=semester_id(c),label=f"{c['academic_year']} · Year {c['study_year']} · Semester {c['semester_number']}") for c in courses}
    result={'semesters':list(sems.values()),'courses':[dict(code=c['course_code'],semester=semester_id(c)) for c in courses]}
    if session['role']=='hod':
        result['semesters']=[dict(id=semester_id(c),label=f"{c['academic_year']} · Year {c['study_year']} · Semester {c['semester_number']}") for c in query('SELECT * FROM semester ORDER BY academic_year,study_year,semester_number')]
        result['lecturers']=query('SELECT email,name FROM lecturer ORDER BY name')
        result['assignments']=query('SELECT lc.email,l.name,lc.course_code FROM lecturer_course lc JOIN lecturer l ON l.email=lc.email ORDER BY l.name,lc.course_code')
    return jsonify(result)

@app.get('/api/sessions')
@allowed('hod','lecturer','ar')
def sessions():
    code=request.args.get('course','');course_access(code)
    rows=query('SELECT date,week_number FROM class_session WHERE course_code=%s ORDER BY date DESC',(code,))
    return jsonify([dict(id=f"{r['date']}|{r['week_number']}",label=f"{r['date']} · Week {r['week_number']}") for r in rows])

def selected_session(d,lock=False):
    code=text(d.get('course'),20);course=course_access(code)
    try:
        parts=str(d.get('session','')).split('|'); when=date.fromisoformat(parts[0]);week=int(parts[1])
    except (ValueError,IndexError): abort(400,'Choose a valid class session.')
    row=query('SELECT * FROM class_session WHERE course_code=%s AND date=%s AND week_number=%s'+(' FOR UPDATE' if lock else ''),(code,when,week),True)
    if not row: abort(404,'Class session not found.')
    return course,when,week

@app.get('/api/attendance')
@allowed('hod','lecturer','ar')
def attendance():
    course,when,week=selected_session(request.args)
    records=query('SELECT email,attendance_status,absent_reason FROM student_class_session WHERE date=%s AND week_number=%s',(when,week))
    saved={r['email']: ('medical' if r['attendance_status']==0 and r['absent_reason']=='MC' else 'present' if r['attendance_status']==1 else 'absent') for r in records}
    return jsonify(students=[dict(registrationNumber=s['reg_number'],status=saved.get(s['email'],'')) for s in roster(course)])

@app.post('/api/attendance')
@allowed('hod','lecturer','ar')
def save_attendance():
    d=data();course,when,week=selected_session(d,True); students=roster(course)
    submitted=d.get('statuses'); originals=d.get('originals'); mode=d.get('mode')
    if not isinstance(submitted,dict) or mode not in ('mark','update'): abort(400,'Invalid attendance request.')
    expected={s['reg_number']:s['email'] for s in students}
    if not expected or set(submitted)!=set(expected): abort(400,'Attendance must include the entire enrolled class.')
    rows=query('SELECT * FROM student_class_session WHERE date=%s AND week_number=%s FOR UPDATE',(when,week))
    old={r['email']:r for r in rows}
    if mode=='mark' and old: abort(409,'Attendance already exists. Use Update Attendance.')
    for reg,status in submitted.items():
        row=old.get(expected[reg]); current='' if not row else 'medical' if row['attendance_status']==0 and row['absent_reason']=='MC' else 'present' if row['attendance_status']==1 else 'absent'
        if mode=='update' and (not isinstance(originals,dict) or originals.get(reg)!=current): abort(409,'Attendance changed since you opened it. Reload before updating.')
        if status not in ('present','absent','medical'): abort(400,'Mark every student.')
        if status=='medical' and (mode!='update' or current not in ('absent','medical')): abort(400,'MC is available only for an existing absent record.')
        if session['role']=='ar' and (mode!='update' or (status!=current and not (current=='absent' and status=='medical'))): abort(403,'AR users can only change a saved absence to MC.')
        if row:
            if current==status: continue
            reason='MC' if status=='medical' else None
            execute('UPDATE student_class_session SET attendance_status=%s,absent_reason=%s WHERE email=%s AND date=%s AND week_number=%s',(1 if status=='present' else 0,reason,expected[reg],when,week))
        else:
            execute('INSERT INTO student_class_session (email,date,week_number,attendance_status,absent_reason) VALUES (%s,%s,%s,%s,NULL)',(expected[reg],when,week,1 if status=='present' else 0))
    if session['role']=='ar': execute('UPDATE class_session SET email=%s,updated_time=NOW() WHERE date=%s AND week_number=%s',(session['email'],when,week))
    db().commit();return jsonify(ok=True)

@app.get('/api/my-attendance')
@allowed('student')
def own_attendance():
    student=query('SELECT name,reg_number FROM student WHERE email=%s',(session['email'],),True)
    rows=query('''SELECT c.course_code,c.academic_year,c.study_year,c.semester_number,
       SUM(CASE WHEN a.attendance_status=1 THEN 1 ELSE 0 END) AS present,
       SUM(CASE WHEN a.attendance_status=0 AND COALESCE(a.absent_reason,'')<>'MC' THEN 1 ELSE 0 END) AS absent,
       SUM(CASE WHEN a.attendance_status=0 AND a.absent_reason='MC' THEN 1 ELSE 0 END) AS medical,
       COUNT(a.email) AS total
       FROM student_semester e JOIN course c ON c.academic_year=e.academic_year AND c.study_year=e.study_year AND c.semester_number=e.semester_number
       LEFT JOIN class_session cs ON cs.course_code=c.course_code AND cs.date<=CURRENT_DATE()
       LEFT JOIN student_class_session a ON a.date=cs.date AND a.week_number=cs.week_number AND a.email=e.email
       WHERE e.email=%s GROUP BY c.course_code,c.academic_year,c.study_year,c.semester_number
       ORDER BY c.academic_year DESC,c.study_year DESC,c.semester_number DESC,c.course_code''',(session['email'],))
    return jsonify(student=student,rows=rows)

@app.get('/api/report')
@allowed('hod','lecturer')
def report():
    code=request.args.get('course','');course=course_access(code)
    try: start=date.fromisoformat(request.args.get('start',''));end=date.fromisoformat(request.args.get('end',''))
    except ValueError: abort(400,'Choose valid dates.')
    if start>end: abort(400,'End date must follow start date.')
    rows=[]
    for s in roster(course):
        r=query('''SELECT SUM(a.attendance_status=1) AS present,SUM(a.attendance_status=0 AND COALESCE(a.absent_reason,'')<>'MC') AS absent,SUM(a.attendance_status=0 AND a.absent_reason='MC') AS medical,COUNT(*) AS total FROM student_class_session a JOIN class_session cs ON cs.date=a.date AND cs.week_number=a.week_number WHERE a.email=%s AND cs.course_code=%s AND cs.date BETWEEN %s AND %s AND cs.date<=CURRENT_DATE()''',(s['email'],code,start,end),True)
        rows.append(dict(reg=s['reg_number'],**{k:int(v or 0) for k,v in r.items()}))
    count=query('SELECT COUNT(*) AS n FROM class_session WHERE course_code=%s AND date BETWEEN %s AND %s AND date<=CURRENT_DATE()',(code,start,end),True)['n']
    return jsonify(rows=rows,sessions=count)

@app.post('/api/semesters')
@allowed('hod')
def add_semester():
    d=data()
    try: y=int(d.get('study_year')); n=int(d.get('semester_number'))
    except (TypeError,ValueError): abort(400,'Enter valid year and semester numbers.')
    a=text(d.get('academic_year'),9)
    if not re.fullmatch(r'\d{2}/\d{2}',a) or y not in range(1,5) or n not in (1,2): abort(400,'Use academic year YY/YY, study year 1–4 and semester 1 or 2.')
    execute('INSERT INTO semester VALUES (%s,%s,%s)',(a,y,n));db().commit();return jsonify(ok=True)

@app.post('/api/courses')
@allowed('hod')
def add_course():
    d=data();key=semester_key(d.get('semester'));code=text(d.get('code'),20)
    execute('INSERT INTO course (course_code,academic_year,study_year,semester_number) VALUES (%s,%s,%s,%s)',(code,*key));db().commit();return jsonify(ok=True)

@app.post('/api/assignments')
@allowed('hod')
def assign():
    d=data();email=text(d.get('email'));code=text(d.get('course'),20)
    execute('INSERT INTO lecturer_course VALUES (%s,%s)',(email,code));db().commit();return jsonify(ok=True)

@app.post('/api/sessions')
@allowed('hod','lecturer')
def add_session():
    d=data();course_access(text(d.get('course'),20))
    try: when=date.fromisoformat(d.get('date',''));week=int(d.get('week'))
    except (ValueError,TypeError): abort(400,'Enter a valid date and week.')
    if not 1<=week<=14: abort(400,'Week must be 1–14.')
    ar=query('SELECT email FROM ar_user ORDER BY email LIMIT 1',one=True)
    if not ar: abort(400,'Your schema requires an AR account for every session. Create one with setup.py first.')
    execute('INSERT INTO class_session (date,week_number,course_code,email) VALUES (%s,%s,%s,%s)',(when,week,d['course'],ar['email']));db().commit();return jsonify(ok=True)

@app.post('/api/import-preview')
@allowed('hod')
def import_preview():
    file=request.files.get('file');key=semester_key(request.form.get('semester'))
    if not file or not file.filename.lower().endswith('.xlsx'): abort(400,'Choose an .xlsx file. Convert older .xls files to .xlsx first.')
    if not query('SELECT * FROM semester WHERE academic_year=%s AND study_year=%s AND semester_number=%s',key,True): abort(400,'Semester does not exist.')
    try:
        book=load_workbook(io.BytesIO(file.read()),read_only=True,data_only=True); sheet=book.active
        iterator=sheet.iter_rows(values_only=True);heads=[str(x or '').strip().lower() for x in next(iterator)]
        names=['registration number','full name','email']; indexes=[heads.index(n) for n in names]
        rows=[];regs=set();emails=set()
        for values in iterator:
            if not any(v is not None for v in values):continue
            if len(rows)>=1000: abort(400,'Import at most 1000 students at a time.')
            reg,name,email=[text(values[i],30 if j==0 else 100 if j==1 else 255) for j,i in enumerate(indexes)];email=email.lower()
            if '@' not in email or reg in regs or email in emails: abort(400,'Invalid email or duplicate registration/email in spreadsheet.')
            regs.add(reg);emails.add(email);rows.append(dict(reg=reg,name=name,email=email))
        book.close()
    except HTTPException: raise
    except Exception: abort(400,'Unable to read spreadsheet. Required headers: Registration Number, Full Name, Email.')
    if not rows: abort(400,'Spreadsheet has no students.')
    # Stage server-side, never place the workbook in a cookie or trust a client confirmation payload.
    stage=ROOT/'.imports';stage.mkdir(exist_ok=True);token=secrets.token_hex(24)
    old=session.get('import_token')
    if old: (stage/old).unlink(missing_ok=True)
    (stage/token).write_text(json.dumps(dict(rows=rows,semester=key)));session['import_token']=token
    return jsonify(rows=rows)

@app.post('/api/import-confirm')
@allowed('hod')
def import_confirm():
    token=session.get('import_token');path=ROOT/'.imports'/str(token)
    if not token or not path.is_file(): abort(400,'Preview a spreadsheet first.')
    payload=json.loads(path.read_text());key=tuple(payload['semester'])
    for r in payload['rows']:
        existing=query('SELECT email,reg_number FROM student WHERE email=%s OR reg_number=%s FOR UPDATE',(r['email'],r['reg']))
        if existing:
            if len(existing)!=1 or existing[0]['email'].lower()!=r['email'] or existing[0]['reg_number']!=r['reg']: abort(409,'An email or registration number conflicts with an existing student.')
        else:
            execute('INSERT INTO student (email,reg_number,password_hash,name) VALUES (%s,%s,%s,%s)',(r['email'],r['reg'],generate_password_hash(secrets.token_urlsafe(32)),r['name']))
        execute('INSERT IGNORE INTO student_semester VALUES (%s,%s,%s,%s)',(r['email'],*key))
    db().commit();path.unlink();session.pop('import_token',None);return jsonify(ok=True,count=len(payload['rows']))

if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
