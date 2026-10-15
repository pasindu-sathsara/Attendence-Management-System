# ICT Attendance: Flask + MySQL

Your original website design is connected to Flask. Use the existing `student_attendance_system` database; this package does not create, drop, or migrate tables.

## Start on Windows

Extract this ZIP into a new folder. Open that folder in VS Code.

If this folder has no virtual environment:

```powershell
py -m venv .venv
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py configure
```

Enter the host, port, username and password that you use for MySQL Workbench. The default database is student_attendance_system. Credentials are saved only in your local config.json. Never upload or commit that file.

Check the connection:

```powershell
.\.venv\Scripts\python.exe setup.py check
```

Your SQL sample accounts use TEST_HASH_ONLY, which is not a password hash. Set real passwords for the accounts you want to test:

```powershell
.\.venv\Scripts\python.exe setup.py password
```

Choose hod and hod@example.com first. Repeat for lecturer/student/AR accounts as needed. Passwords are entered privately and stored as hashes; no database schema change is required.

Start the website:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 in your browser. Do not open the HTML files directly or use Live Server. Sign in with email and the password you set. Staff login determines HOD, lecturer or AR role from the database. There is no role-switching dropdown.

## Connected features

- Student dashboard: own details and own module attendance only, including enrolled modules with no records. Academic period appears per module because course_name is absent from the ER.
- Staff dashboard: assigned-module filters for lecturers, enrolled class roster, marking/updating popup, bulk present marking, search, MC on existing saved absences. HOD can access all modules. AR can only update an absence to MC through this popup; no online medical submissions.
- Save validates the whole class, rejects stale updates and prevents marking over existing records.
- HOD management: semester/course creation, lecturer assignment, Excel preview and confirmation, student semester enrolment, class session creation.
- Reports: authorized class totals, dates, and printing.
- Sign out clears the authenticated session. Server checks protect pages and actions; changing HTML does not grant access.

## Excel student import

Use .xlsx, with exactly these header names (case insensitive):

Registration Number | Full Name | Email

Choose the semester, preview the file, then confirm. The operation imports student records and enrols them in that semester. An exact existing email/registration pair may be enrolled again without changing its password. Conflicting identities abort the transaction. Extra Batch columns are ignored: enrolment uses student_semester, not a new batch table. Old .xls files must be saved as .xlsx first.

Imported student accounts have unusable random credentials until activated. An authorized administrator runs:

```powershell
.\.venv\Scripts\python.exe setup.py activate
```

Give the generated one-time code to the identified student. The student registration page uses their imported name, email, registration number, activation code and new password. This prevents someone claiming a known registration number without a staff-issued code. An administrator can also set their password directly with setup.py password.

## Staff accounts and schema limits

Your ER has no employee number, username, course name or staff approval status. Those inputs/approval controls are removed. New staff accounts are created locally by the administrator:

```powershell
.\.venv\Scripts\python.exe setup.py create-staff
```

The existing schema is preserved, including its limitations:

- Sessions have PRIMARY KEY(date, week_number). Two modules cannot have sessions on the same date/week. A duplicate displays an error instead of silently overwriting another module. Fixing this requires a separate ER-aligned key migration.
- A course_code can belong to only one semester in this schema.
- Semester enrolment implies attendance in all that semester's courses, as drawn in the ER.
- Every new session requires an AR account. The first AR account is used to satisfy the existing NOT NULL email foreign key; this initial association does not mean a medical review has happened. updated_time remains NULL until an AR update.
- HOD is a separate subtype. If the same person must also teach, an administrator must also create their lecturer record; no inheritance relationship is added.
- Academic year must use YY/YY, study year 1–4, semester 1 or 2, week 1–14.
- MC stays attendance_status=0 and absent_reason='MC'; percentage is Present / recorded completed sessions, with MC included in denominator. MC is shown separately. Missing marks and future sessions are excluded. Confirm department percentage policy before adopting a different calculation.
- Medical documents remain physically submitted. The backend does not add online upload or extra medical reference fields.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_backend
```

Tests cover permissions, CSRF, own-student isolation, stale updates, full-class marking and MC storage. They use mocked database responses. The delivered code has not been tested against your laptop's live MySQL instance; setup.py check is the first local connection check.

The Flask development server is for local project work. Public deployment requires production hosting, HTTPS and appropriate account/database administration.
