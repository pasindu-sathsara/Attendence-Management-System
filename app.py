"""Simple Flask attendance system using MySQL and Excel module rosters."""
import json, secrets, re, io, hmac
from pathlib import Path
from functools import wraps
from datetime import date
from flask import Flask, request, session, jsonify, render_template, redirect, g, abort, send_from_directory, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
import mysql.connector
from openpyxl import load_workbook, Workbook

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
    messages={1062:'This record already exists.',
              1452:'A referenced semester, course, student or staff account does not exist.',
              3819:'A value does not meet the database constraints.',
              1064:'A database query has a syntax error (1064). Please report this error to the system maintainer.',
              1054:'The database structure does not match this version. Run setup.py upgrade (1054).',
              1146:'A required database table is missing. Check the database setup (1146).'}
    connection_errors={1045,1049,2002,2003,2005,2006,2013,2055}
    if err.errno in connection_errors:
        message='Cannot connect to the database. Check config.json and that MySQL Server is running.'
        status=503
    else:
        message=messages.get(err.errno,'A database operation failed. Please report MySQL error '+str(err.errno)+'.')
        status=400 if err.errno in (1062,1452,3819) else 500
    if request.path.startswith('/api/'): return jsonify(error=message),status
    return render_template('error.html',message=message),status


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

def course_access(value):
    parts=str(value).split('~')
    if len(parts)!=2: abort(400,'Select a module and academic year.')
    code,year=parts
    course=query('SELECT c.*,o.academic_year FROM course c JOIN course_offering o ON o.course_code=c.course_code WHERE c.course_code=%s AND o.academic_year=%s',(code,year),True)
    if not course: abort(404,'Module offering not found.')
    if session['role']=='lecturer' and not query('SELECT email FROM lecturer_course WHERE email=%s AND course_code=%s AND academic_year=%s',(session['email'],code,year),True): abort(403,'This module is not assigned to you for this year.')
    return course

def roster(course):
    return query('SELECT s.email,s.reg_number FROM student s JOIN student_course e ON e.email=s.email WHERE e.course_code=%s AND e.academic_year=%s ORDER BY s.reg_number',(course['course_code'],course['academic_year']))

@app.route('/')
def home(): return redirect('/UI.html')
@app.get('/style.css')
def css(): return send_from_directory(ROOT,'style.css')
@app.get('/UI.html')
def login_page(): return render_template('UI.html', portal='student')
@app.get('/staff-login.html')
def staff_login_page(): return render_template('UI.html', portal='staff')
@app.get('/student-register.html')
def register_page(): return redirect('/UI.html')
@app.get('/staff-register.html')
def staff_register(): return redirect('/UI.html')
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
    portal=d.get('portal')
    if portal not in ('student','staff'): abort(400,'Select the student or staff login page.')
    roles=['student'] if portal=='student' else ['lecturer','ar']
    found=None
    for role in roles:
        row=query('SELECT email,name,password_hash FROM '+TABLES[role]+' WHERE email=%s',(email,),True)
        if row:
            try: valid=check_password_hash(row['password_hash'],password)
            except (ValueError,TypeError): valid=False
            if valid:
                if role=='lecturer' and query('SELECT email FROM hod WHERE email=%s',(email,),True): role='hod'
                found=(role,row);break
    if not found: abort(401,'Incorrect email or password.')
    session.clear();session.update(email=found[1]['email'],role=found[0],name=found[1]['name'],csrf=secrets.token_hex(32))
    return jsonify(next='/student-dashboard.html' if found[0]=='student' else '/dashboard.html')

@app.get('/api/options')
@allowed('hod','lecturer','ar')
def options():
    sql='SELECT c.*,o.academic_year FROM course c JOIN course_offering o ON o.course_code=c.course_code '
    args=()
    if session['role']=='lecturer':
        sql+='JOIN lecturer_course lc ON lc.course_code=o.course_code AND lc.academic_year=o.academic_year WHERE lc.email=%s '
        args=(session['email'],)
    courses=query(sql+'ORDER BY o.academic_year,c.study_year,c.semester_number,c.course_code',args)
    sems={semester_id(c):dict(id=semester_id(c),label=f"{c['academic_year']} · Year {c['study_year']} · Semester {c['semester_number']}") for c in courses}
    result={'semesters':list(sems.values()),'courses':[dict(code=c['course_code']+'~'+c['academic_year'],label=c['course_code']+' · '+c['academic_year'],semester=semester_id(c)) for c in courses]}
    if session['role']=='hod':
        result['semesters']=[dict(id=semester_id(c),label=f"{c['academic_year']} · Year {c['study_year']} · Semester {c['semester_number']}") for c in query('SELECT * FROM semester ORDER BY academic_year,study_year,semester_number')]
        result['lecturers']=query("SELECT email,CONCAT_WS(' ',NULLIF(title,''),name) AS name FROM lecturer ORDER BY name")
        result['assignments']=query("SELECT lc.email,CONCAT_WS(' ',NULLIF(l.title,''),l.name) AS name,lc.course_code,lc.academic_year FROM lecturer_course lc JOIN lecturer l ON l.email=lc.email ORDER BY l.name,lc.course_code")
    result['batches']=[r['batch'] for r in query('SELECT DISTINCT batch FROM student WHERE batch IS NOT NULL ORDER BY batch')]
    return jsonify(result)

@app.get('/api/sessions')
@allowed('hod','lecturer','ar')
def sessions():
    course=course_access(request.args.get('course',''));code=course['course_code']
    rows=query('SELECT date,week_number FROM class_session WHERE course_code=%s AND academic_year=%s ORDER BY date DESC',(code,course['academic_year']))
    return jsonify([dict(id=f"{r['date']}|{r['week_number']}",label=f"{r['date']} · Week {r['week_number']}") for r in rows])

def selected_session(d,lock=False):
    course=course_access(d.get('course'));code=course['course_code']
    try:
        parts=str(d.get('session','')).split('|'); when=date.fromisoformat(parts[0]);week=int(parts[1])
    except (ValueError,IndexError): abort(400,'Choose a valid class session.')
    row=query('SELECT * FROM class_session WHERE course_code=%s AND date=%s AND week_number=%s'+(' FOR UPDATE' if lock else ''),(code,when,week),True)
    if not row or row['academic_year']!=course['academic_year']: abort(404,'Class session not found for this academic year.')
    return course,when,week

@app.get('/api/attendance')
@allowed('hod','lecturer','ar')
def attendance():
    course,when,week=selected_session(request.args)
    records=query('SELECT email,attendance_status,absent_reason FROM student_class_session WHERE course_code=%s AND date=%s AND week_number=%s',(course['course_code'],when,week))
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
    rows=query('SELECT * FROM student_class_session WHERE course_code=%s AND date=%s AND week_number=%s FOR UPDATE',(course['course_code'],when,week))
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
            execute('UPDATE student_class_session SET attendance_status=%s,absent_reason=%s WHERE email=%s AND course_code=%s AND date=%s AND week_number=%s',(1 if status=='present' else 0,reason,expected[reg],course['course_code'],when,week))
        else:
            execute('INSERT INTO student_class_session (email,course_code,date,week_number,attendance_status,absent_reason) VALUES (%s,%s,%s,%s,%s,NULL)',(expected[reg],course['course_code'],when,week,1 if status=='present' else 0))
    if session['role']=='ar': execute('UPDATE class_session SET email=%s,updated_time=NOW() WHERE course_code=%s AND date=%s AND week_number=%s',(session['email'],course['course_code'],when,week))
    db().commit();return jsonify(ok=True)

# One row per enrolled student and module. Only sessions with saved attendance count.
ATTENDANCE_SQL = """
WITH recorded AS (
 SELECT cs.course_code,cs.academic_year,cs.date,cs.week_number
 FROM class_session cs
 WHERE {dates} AND EXISTS (
  SELECT 1 FROM student_class_session a WHERE a.course_code=cs.course_code
  AND a.date=cs.date AND a.week_number=cs.week_number)
), totals AS (
 SELECT s.email,s.reg_number AS reg,s.name,s.batch,e.course_code,e.academic_year,
 c.study_year,c.semester_number,COUNT(r.date) AS total,
 COALESCE(SUM(a.attendance_status=1),0) AS present,
 COALESCE(SUM(a.attendance_status=0),0) AS absent,
 COALESCE(SUM(a.attendance_status=0 AND a.absent_reason='MC'),0) AS medical,
 COUNT(r.date)-COUNT(a.email) AS unmarked
 FROM student_course e JOIN student s ON s.email=e.email
 JOIN course c ON c.course_code=e.course_code
 LEFT JOIN recorded r ON r.course_code=e.course_code AND r.academic_year=e.academic_year
 LEFT JOIN student_class_session a ON a.email=e.email AND a.course_code=r.course_code
 AND a.date=r.date AND a.week_number=r.week_number
 WHERE {filters}
 GROUP BY s.email,s.reg_number,s.name,s.batch,e.course_code,e.academic_year,c.study_year,c.semester_number
), scores AS (
 SELECT totals.*,100.0*present/NULLIF(total,0) AS raw_percentage,
 ROUND(100.0*present/NULLIF(total,0),2) AS percentage,
 CASE WHEN total=0 THEN 'Not assessed' WHEN present*100>total*80 THEN 'Eligible' ELSE 'Ineligible' END AS eligibility
 FROM totals
)
"""

@app.get('/api/my-attendance')
@allowed('student')
def own_attendance():
    student=query('SELECT name,reg_number FROM student WHERE email=%s',(session['email'],),True)
    sql=ATTENDANCE_SQL.format(dates='1=1',filters='s.email=%s')
    rows=query(sql+'SELECT * FROM scores ORDER BY academic_year DESC,study_year DESC,semester_number,course_code',(session['email'],))
    return jsonify(student=student,rows=rows)

def report_data():
    params=request.args; chosen=params.get('course',''); filters=[]; args=[]
    if chosen:
        course=course_access(chosen)
        filters+=['e.course_code=%s','e.academic_year=%s'];args+=[course['course_code'],course['academic_year']]
    elif session['role']!='hod': abort(403,'Select one of your assigned modules.')
    for key,column in [('academic_year','e.academic_year'),('study_year','c.study_year'),('semester_number','c.semester_number'),('batch','s.batch')]:
        value=params.get(key,'')
        if value:
            filters.append(column+'=%s');args.append(value)
    if not chosen and not params.get('academic_year'): abort(400,'Select an academic year.')
    dates=[];dateargs=[]
    for key,operator in [('start','>='),('end','<=')]:
        value=params.get(key,'')
        if value:
            try: when=date.fromisoformat(value)
            except ValueError: abort(400,'Choose valid dates.')
            dates.append('cs.date'+operator+'%s');dateargs.append(when)
    if params.get('start') and params.get('end') and params['start']>params['end']: abort(400,'End date must follow start date.')
    sql=ATTENDANCE_SQL.format(dates=' AND '.join(dates) or '1=1',filters=' AND '.join(filters) or '1=1')
    args=tuple(dateargs+args)
    if chosen:
        rows=query(sql+'SELECT reg,name,present,absent,total,percentage,eligibility,medical,unmarked FROM scores ORDER BY reg',args)
        kind='students'
    else:
        outer_filters=[];outer_args=[]
        for key,column in [('academic_year','o.academic_year'),('study_year','c.study_year'),('semester_number','c.semester_number')]:
            if params.get(key): outer_filters.append(column+'=%s');outer_args.append(params[key])
        rows=query(sql+"""SELECT c.course_code,o.academic_year,c.study_year,c.semester_number,
          COUNT(scores.email) AS students,COALESCE(rc.total,0) AS total,
          COALESCE(SUM(scores.present),0) AS present,COALESCE(SUM(scores.absent),0) AS absent,
          COALESCE(SUM(scores.unmarked),0) AS unmarked,ROUND(AVG(scores.raw_percentage),2) AS percentage
          FROM course_offering o JOIN course c ON c.course_code=o.course_code
          LEFT JOIN scores ON scores.course_code=o.course_code AND scores.academic_year=o.academic_year
          LEFT JOIN (SELECT course_code,academic_year,COUNT(*) AS total FROM recorded GROUP BY course_code,academic_year) rc
          ON rc.course_code=o.course_code AND rc.academic_year=o.academic_year
          WHERE """+' AND '.join(outer_filters)+"""
          GROUP BY c.course_code,o.academic_year,c.study_year,c.semester_number,rc.total
          ORDER BY c.study_year,c.semester_number,c.course_code""",args+tuple(outer_args))
        kind='modules'
    return dict(rows=rows,kind=kind)

@app.get('/api/report')
@allowed('hod','lecturer')
def report(): return jsonify(report_data())

@app.get('/api/report.xlsx')
@allowed('hod','lecturer')
def export_report():
    result=report_data(); book=Workbook();sheet=book.active;sheet.title='Attendance'
    columns=[('reg','Reg No'),('name','Name'),('present','Present'),('absent','Absent'),('total','Total Sessions'),('percentage','Attendance %'),('eligibility','Eligibility')] if result['kind']=='students' else [('course_code','Module'),('academic_year','Academic Year'),('study_year','Study Year'),('semester_number','Semester'),('students','Students'),('total','Total Sessions'),('present','Present'),('absent','Absent'),('percentage','Average Attendance %')]
    sheet.append([label for key,label in columns])
    from openpyxl.styles import Font, PatternFill
    for row in result['rows']:
        sheet.append([row.get(key) for key,label in columns])
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value,str): cell.data_type='s'
    for cell in sheet[1]: cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='183659')
    sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
    for col in sheet.columns: sheet.column_dimensions[col[0].column_letter].width=min(40,max(15,max(len(str(c.value or '')) for c in col)+2))
    filters=book.create_sheet('Report details')
    filters.append(['Filter','Value'])
    for key in ('academic_year','study_year','semester_number','batch','course','start','end'):
        filters.append([key,request.args.get(key) or 'All'])
        filters.cell(filters.max_row,2).data_type='s'
    filters.append(['Sessions','Class sessions with saved attendance in the selected date range.'])
    filters.append(['Medical','MC is included in Absent; it does not count as Present.'])
    filters.append(['Eligibility','More than 80%; exactly 80% is Ineligible.'])
    filters.append(['Unmarked records',sum(int(r['unmarked']) for r in result['rows'])])
    filters.column_dimensions['A'].width=24;filters.column_dimensions['B'].width=85
    out=io.BytesIO();book.save(out);out.seek(0)
    return send_file(out,as_attachment=True,download_name='attendance-report.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

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
    ensure_course(code,key);db().commit();return jsonify(ok=True)

@app.post('/api/assignments')
@allowed('hod')
def assign():
    d=data();email=text(d.get('email'));course=course_access(d.get('course'))
    execute('INSERT INTO lecturer_course (email,course_code,academic_year) VALUES (%s,%s,%s)',(email,course['course_code'],course['academic_year']));db().commit();return jsonify(ok=True)

@app.post('/api/sessions')
@allowed('hod','lecturer','ar')
def add_session():
    d=data();course=course_access(d.get('course'))
    try: when=date.fromisoformat(d.get('date',''));week=int(d.get('week'))
    except (ValueError,TypeError): abort(400,'Enter a valid date and week.')
    if not 1<=week<=14: abort(400,'Week must be 1–14.')
    ar_email=session['email'] if session['role']=='ar' else None
    execute('INSERT INTO class_session (date,week_number,course_code,academic_year,email) VALUES (%s,%s,%s,%s,%s)',(when,week,course['course_code'],course['academic_year'],ar_email));db().commit();return jsonify(ok=True)

def ensure_course(code,key):
    year,study,semester=key
    existing=query('SELECT * FROM course WHERE course_code=%s',(code,),True)
    if existing and (existing['study_year']!=study or existing['semester_number']!=semester):
        abort(400,'Module '+code+' already has a different study year or semester.')
    execute('INSERT IGNORE INTO semester VALUES (%s,%s,%s)',key)
    execute('INSERT IGNORE INTO course (course_code,study_year,semester_number) VALUES (%s,%s,%s)',(code,study,semester))
    execute('INSERT IGNORE INTO course_offering VALUES (%s,%s)',(code,year))

@app.get('/api/roster')
@allowed('hod','lecturer','ar')
def module_roster():
    return jsonify(students=[dict(registrationNumber=r['reg_number'],status='') for r in roster(course_access(request.args.get('course')))])

@app.post('/api/staff')
@allowed('hod')
def create_staff():
    d=data();email=text(d.get('email')).lower();name=text(d.get('name'),100);role=d.get('role')
    password=str(d.get('password',''))
    if role not in ('lecturer','ar') or '@' not in email or len(password)<8: abort(400,'Choose a role, valid email and password of at least 8 characters.')
    if any(query('SELECT email FROM '+t+' WHERE email=%s',(email,),True) for t in ('student','lecturer','ar_user')): abort(400,'Email already belongs to an account.')
    title=d.get('title')
    if title not in ('Mr','Mrs','Ms','Ven'): abort(400,'Choose a title.')
    table='lecturer' if role=='lecturer' else 'ar_user'
    execute('INSERT INTO '+table+' (email,name,title,password_hash) VALUES (%s,%s,%s,%s)',(email,name,title,generate_password_hash(password)))
    db().commit();return jsonify(ok=True)

def workbook_rows(file):
    if not file or not file.filename.lower().endswith('.xlsx'): abort(400,'Choose an .xlsx workbook.')
    try:
        book=load_workbook(io.BytesIO(file.read()),read_only=True,data_only=True)
        result=[];names={};missing_names=[]
        for sheet in book:
            match=re.match(r'^\s*((?:ICT|COM|IDC))\s*(\d{4})',sheet.title,re.I)
            if not match: continue
            code=match[1].upper()+' '+match[2]
            students=[];header=None
            for number,values in enumerate(sheet.iter_rows(values_only=True),1):
                if number>10000: abort(400,'A sheet exceeds 10000 rows.')
                if header is None:
                    heads=[str(v or '').strip().lower() for v in values]
                    if 'reg_no' in heads and 'name with initials' in heads:
                        header=(heads.index('reg_no'),heads.index('name with initials'))
                    continue
                if len(values)<=max(header): continue
                reg=str(values[header[0]] or '').strip().upper();name=str(values[header[1]] or '').strip()
                if not reg or '/' not in reg: continue
                prefix=sheet.title+' row '+str(number)+': '
                if len(reg)>30: abort(400,prefix+'Reg_no is too long.')
                if len(name)>100: abort(400,prefix+'Name with Initials exceeds 100 characters.')
                row=dict(reg=reg,name=name)
                if name: names[reg]=name
                else: missing_names.append((row,prefix))
                students.append(row)
            if students: result.append(dict(code=code,study=int(match[2][0]),sheet=sheet.title,students=students))
        book.close()
        for row,prefix in missing_names:
            if row['reg'] not in names: abort(400,prefix+'Name with Initials is missing for '+row['reg']+'.')
            row['name']=names[row['reg']]
        if not result: abort(400,'No module sheets with Reg_no and Name with Initials headings were found.')
        return result
    except HTTPException: raise
    except Exception: abort(400,'Unable to read the attendance workbook.')

def account_details(file):
    import csv
    if not file: return {}
    result={};emails=set()
    try:
        if file.filename.lower().endswith('.csv'):
            rows=list(csv.reader(io.StringIO(file.read().decode('utf-8-sig'))))
        elif file.filename.lower().endswith('.xlsx'):
            book=load_workbook(io.BytesIO(file.read()),read_only=True,data_only=True)
            rows=list(book.active.iter_rows(values_only=True));book.close()
        else: abort(400,'Account details must be CSV or XLSX.')
        if not rows: abort(400,'Account details file is empty.')
        heads=[str(v or '').strip().lower() for v in rows[0]]
        for field in ('reg_no','email','nic'):
            if field not in heads: abort(400,'Account details row 1: missing '+field+' heading.')
        for number,values in enumerate(rows[1:],2):
            if not any(v is not None and str(v).strip() for v in values): continue
            def field(name):
                if name not in heads or heads.index(name)>=len(values): return ''
                value=values[heads.index(name)]
                if value is None: return ''
                if isinstance(value,float) and value.is_integer(): value=int(value)
                return str(value).strip()
            reg=field('reg_no').upper();email=field('email').lower();nic=field('nic');batch=field('batch')
            if not email and not nic and not batch: continue
            prefix='Account details row '+str(number)+': '
            if not reg or len(reg)>30: abort(400,prefix+'Reg_no is missing or too long.')
            if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(email)>255: abort(400,prefix+'Email is invalid.')
            if not re.fullmatch(r'(?:\d{9}[vVxX]|\d{12})',nic): abort(400,prefix+'NIC must contain 12 digits, or 9 digits followed by V or X. Format NIC cells as text.')
            if batch and not re.fullmatch(r'\d{2}/\d{2}',batch): abort(400,prefix+'Batch must use YY/YY.')
            if reg in result: abort(400,prefix+'duplicate Reg_no '+reg)
            if email in emails: abort(400,prefix+'duplicate Email '+email)
            emails.add(email)
            result[reg]=dict(email=email,password_hash=generate_password_hash(nic),batch=batch or None)
        return result
    except HTTPException: raise
    except Exception: abort(400,'Unable to read account details. Use a CSV or XLSX file with Reg_no, Email and NIC headings.')

@app.post('/api/import-preview')
@allowed('hod')
def import_preview():
    old=session.pop('import_token',None)
    if old: (ROOT/'.imports'/old).unlink(missing_ok=True)
    key=semester_key(request.form.get('semester'))
    if not re.fullmatch(r'\d{2}/\d{2}',key[0]) or key[2] not in (1,2): abort(400,'Choose an academic year and semester.')
    modules=workbook_rows(request.files.get('file'));accounts=account_details(request.files.get('accounts'))
    default_batch=request.form.get('batch','').strip()
    if default_batch and not re.fullmatch(r'\d{2}/\d{2}',default_batch): abort(400,'Batch must use YY/YY.')
    rows={};members=set()
    for module in modules:
        if module['study'] not in range(1,5): abort(400,'Invalid study year in '+module['sheet'])
        for student in module['students']:
            reg=student['reg']
            if reg not in rows:
                old=query('SELECT email FROM student WHERE reg_number=%s',(reg,),True)
                account=accounts.get(reg)
                if old and account and old['email'].lower()!=account['email']: abort(400,'Email differs from the existing account for '+reg)
                rows[reg]=dict(reg=reg,name=student['name'],email=old['email'] if old else account['email'] if account else '',password_hash=account['password_hash'] if account and not old else '',batch=(account or {}).get('batch') or default_batch or None,modules=[])
            if (reg,module['code']) not in members:
                members.add((reg,module['code']));rows[reg]['modules'].append(module['code'])
    module_map={m['code']:dict(code=m['code'],study=m['study']) for m in modules}
    stage=ROOT/'.imports';stage.mkdir(exist_ok=True);token=secrets.token_hex(24)
    if session.get('import_token'): (stage/session['import_token']).unlink(missing_ok=True)
    payload=dict(rows=list(rows.values()),modules=list(module_map.values()),semester=key)
    (stage/token).write_text(json.dumps(payload));session['import_token']=token
    missing=sum(not r['email'] for r in rows.values())
    return jsonify(rows=[dict(reg=r['reg'],name=r['name'],email=r['email'] or 'Account details required',modules=', '.join(r['modules']),study_year=max(module_map[c]['study'] for c in r['modules']),programme=student_programme(r['reg'])) for r in rows.values()],missing=missing,modules=len(module_map),sheets=len(modules))

def student_programme(reg):
    parts=re.split(r'[^A-Z0-9]+',reg.upper())
    return 'Computer Science' if any(p in ('ASP','ASB') for p in parts) else 'ICT'

def page_result(sql,args,order):
    try: page=max(1,int(request.args.get('page',1)))
    except ValueError: abort(400,'Invalid page.')
    count=query('SELECT COUNT(*) AS n FROM ('+sql+') AS results',tuple(args),True)['n']
    pages=max(1,(count+9)//10);page=min(page,pages)
    rows=query(sql+' ORDER BY '+order+' LIMIT 10 OFFSET %s',tuple(args)+((page-1)*10,))
    return jsonify(rows=rows,total=count,page=page,pages=pages)

@app.get('/api/students')
@allowed('hod')
def imported_students():
    sql="""SELECT s.reg_number AS reg,s.name,s.email,s.batch,e.academic_year,
        MAX(c.study_year) AS study_year,
        CASE WHEN UPPER(s.reg_number) REGEXP '(^|[^A-Z0-9])(ASP|ASB)([^A-Z0-9]|$)' THEN 'Computer Science' ELSE 'ICT' END AS programme,
        GROUP_CONCAT(DISTINCT c.course_code ORDER BY c.course_code SEPARATOR ', ') AS modules
        FROM student s JOIN student_course e ON e.email=s.email JOIN course c ON c.course_code=e.course_code
        GROUP BY s.email,s.reg_number,s.name,s.batch,e.academic_year"""
    filters=[];args=[]
    for key in ('academic_year','study_year','programme','batch'):
        if request.args.get(key): filters.append(key+'=%s');args.append(request.args[key])
    if request.args.get('search'):
        filters.append('(reg LIKE %s OR name LIKE %s)');args += ['%'+request.args['search']+'%']*2
    sql='SELECT * FROM ('+sql+') AS students WHERE '+(' AND '.join(filters) or '1=1')
    return page_result(sql,args,'reg')

@app.post('/api/student-batch')
@allowed('hod')
def set_batch():
    d=data();batch=str(d.get('batch',''));regs=d.get('registrations')
    if not re.fullmatch(r'\d{2}/\d{2}',batch): abort(400,'Use batch YY/YY.')
    if not isinstance(regs,list) or not regs or len(regs)>1000 or any(not isinstance(r,str) for r in regs): abort(400,'Select students.')
    execute('UPDATE student SET batch=%s WHERE reg_number IN ('+','.join(['%s']*len(regs))+')',tuple([batch]+regs))
    db().commit();return jsonify(ok=True)

@app.get('/api/manage-list')
@allowed('hod')
def manage_list():
    kind=request.args.get('kind'); search='%'+request.args.get('search','')+'%'
    queries={
      'modules':("SELECT c.course_code,o.academic_year,c.study_year,c.semester_number FROM course c JOIN course_offering o ON o.course_code=c.course_code WHERE c.course_code LIKE %s",'academic_year DESC,study_year,course_code'),
      'assignments':("SELECT CONCAT_WS(' ',NULLIF(l.title,''),l.name) AS name,lc.course_code,lc.academic_year FROM lecturer_course lc JOIN lecturer l ON l.email=lc.email WHERE CONCAT(l.name,' ',lc.course_code) LIKE %s",'name,course_code'),
      'staff':("SELECT * FROM (SELECT l.email,l.name,l.title,CASE WHEN h.email IS NULL THEN 'lecturer' ELSE 'hod' END AS role FROM lecturer l LEFT JOIN hod h ON h.email=l.email UNION ALL SELECT email,name,title,'ar' AS role FROM ar_user) AS staff WHERE name LIKE %s",'name'),
      'semesters':("SELECT * FROM semester WHERE academic_year LIKE %s",'academic_year DESC,study_year,semester_number')}
    if kind not in queries: abort(400,'Choose a valid tab.')
    sql,order=queries[kind];return page_result(sql,[search],order)

@app.post('/api/staff-title')
@allowed('hod')
def staff_title():
    d=data();title=d.get('title');role=d.get('role')
    if title not in ('Mr','Mrs','Ms','Ven') or role not in ('lecturer','hod','ar'): abort(400,'Choose a valid title and role.')
    table='ar_user' if role=='ar' else 'lecturer'
    execute('UPDATE '+table+' SET title=%s WHERE email=%s',(title,text(d.get('email'))))
    db().commit();return jsonify(ok=True)

@app.post('/api/import-modules')
@allowed('hod')
def import_modules():
    token=session.get('import_token');path=ROOT/'.imports'/str(token)
    if not token or not path.is_file(): abort(400,'Preview a workbook first.')
    payload=json.loads(path.read_text());year,_,semester=payload['semester']
    for module in payload['modules']:
        ensure_course(module['code'],(year,module['study'],semester))
    db().commit()
    return jsonify(count=len(payload['modules']))

@app.get('/api/account-template')
@allowed('hod')
def account_template():
    import csv
    from flask import Response
    token=session.get('import_token');path=ROOT/'.imports'/str(token)
    if not token or not path.is_file(): abort(400,'Preview a workbook first.')
    out=io.StringIO();writer=csv.writer(out);writer.writerow(['Reg_no','Email','NIC','Batch'])
    for r in json.loads(path.read_text())['rows']:
        if not r['email']: writer.writerow([r['reg'],'','',''])
    return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=account-details.csv'})

@app.post('/api/import-confirm')
@allowed('hod')
def import_confirm():
    token=session.get('import_token');path=ROOT/'.imports'/str(token)
    if not token or not path.is_file(): abort(400,'Preview a workbook first.')
    payload=json.loads(path.read_text());year,_,semester=payload['semester']
    if any(not r['email'] for r in payload['rows']): abort(400,'Supply account details for every new student and preview again.')
    for m in payload['modules']: ensure_course(m['code'],(year,m['study'],semester))
    studies={m['code']:m['study'] for m in payload['modules']}
    for r in payload['rows']:
        existing=query('SELECT email,reg_number FROM student WHERE email=%s OR reg_number=%s FOR UPDATE',(r['email'],r['reg']))
        if existing:
            if len(existing)!=1 or existing[0]['email'].lower()!=r['email'].lower() or existing[0]['reg_number']!=r['reg']: abort(409,'Account conflict for '+r['reg'])
        else:
            if query('SELECT email FROM lecturer WHERE email=%s UNION SELECT email FROM ar_user WHERE email=%s',(r['email'],r['email'])): abort(409,'Email belongs to a staff account.')
            execute('INSERT INTO student (email,reg_number,password_hash,name) VALUES (%s,%s,%s,%s)',(r['email'],r['reg'],r['password_hash'],r['name']))
        if r.get('batch'): execute('UPDATE student SET batch=%s WHERE email=%s',(r['batch'],r['email']))
        for code in r['modules']:
            execute('INSERT IGNORE INTO student_semester VALUES (%s,%s,%s,%s)',(r['email'],year,studies[code],semester))
            execute('INSERT IGNORE INTO student_course VALUES (%s,%s,%s)',(r['email'],code,year))
    db().commit();path.unlink();session.pop('import_token',None)
    return jsonify(ok=True,count=len(payload['rows']))

if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
