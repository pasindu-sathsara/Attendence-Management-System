# Attendance Management System

Rajarata University of Sri Lanka · Faculty of Applied Sciences · Department of Computing.

Python Flask, MySQL 8.0.16+ and plain HTML/CSS/JavaScript. No sample accounts, students, modules or attendance are installed.

## Update an existing installation

Do **not** drop your database. First make a database backup in MySQL Workbench (Server → Data Export).

1. Stop the Flask server with Ctrl+C.
2. Extract this ZIP. Copy its contents into your project folder, replacing the code files. Keep your existing `.venv`, `config.json` and `.session-secret`.
3. Open that project folder in VS Code. Open Terminal → New Terminal and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py upgrade
.\.venv\Scripts\python.exe setup.py check
.\.venv\Scripts\python.exe app.py
```

4. Wait for `Running on http://127.0.0.1:5000`. Keep this terminal open.
5. Open http://127.0.0.1:5000 in Chrome and press Ctrl+F5.
6. Complete the one-time password screen. You can choose a new password or enter the same password twice.
7. HOD should reimport the original workbook for each appropriate academic year and semester to populate the practical components, then assign their demonstrators/lecturers and visiting-lecturer coordinators.

If `config.json` is missing, run `setup.py configure` first using your existing MySQL credentials and database name. The upgrade command uses that configured database, not a hardcoded name.

Alternatively open `database/upgrade.sql` in MySQL Workbench, select your existing database as the default schema, and execute the entire script. Do this instead of `setup.py upgrade`, not as a fresh installation.

The upgrade targets your latest `1407DBFinal.sql` / previous application schema with `course_offering`. It is repeatable and keeps accounts, passwords, module memberships, sessions and marks. It removes the redundant `student.batch` column as requested; batch values are now calculated from registration numbers. It adds first-login flags, teaching-end dates, session updater names, a coordinator table and an attendance update-history table. Existing Ven titles become blank, without changing names or accounts.

Existing accounts go through the first-login step once after the first upgrade. Re-running upgrade does not reset completed flags. An old logged-in browser session also has to complete the step before using protected pages/API actions.

### Important: earlier combined theory/practical records

Older versions merged theory and practical sheets. Their existing module codes and attendance are preserved and displayed as theory `(T)`. No old marks are copied or guessed into practicals. Reimporting creates separate practical `(P)` offerings and their own rosters. Review old combined attendance with the department if some records actually belong to practicals. The software cannot infer their original component reliably.

## Fresh setup on Windows

### 1. Install Python and MySQL

Install Python with its launcher, MySQL Server 8 and MySQL Workbench. Remember the MySQL username and password you set. Workbench is the client; MySQL Server must also be running.

### 2. Create the empty database

In MySQL Workbench, connect to your server, choose File → Open SQL Script, open `database/schema.sql` and execute the whole script. This creates `student_attendance_system` and empty tables. Use this script only for a new installation, not over an existing database.

### 3. Prepare Python

Extract the project, open the folder in VS Code, then run in its terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py configure
```

Configure prompts:

- Host: `127.0.0.1` for your local MySQL server.
- Port: normally `3306`.
- User: your MySQL user, often `root` during local development.
- Password: your MySQL password. Nothing appears while typing; this is normal. Type it and press Enter.
- Database: `student_attendance_system`, unless you used a different name.

### 4. Create the first HOD account

```powershell
.\.venv\Scripts\python.exe setup.py create-staff
```

Choose `hod`; enter email, initial password, name and title. This creates the linked lecturer and HOD records. HOD can create other lecturers, visiting lecturers, demonstrators and AR accounts in Manage System → Staff. There is no public registration. An AR account is not required to create class sessions.

### 5. Run the website

```powershell
.\.venv\Scripts\python.exe app.py
```

Visit http://127.0.0.1:5000. Staff use the Staff Login tab; students use Student Login. The server determines actual staff permissions from the database. Keep Flask running. Do not double-click HTML files or open the site through Live Server.

The supplied VS Code browser configuration opens localhost; it does not start Flask itself.

## First-login passwords and department resets

Students initially use the confirmed NIC from the account-details file as their password. Staff initial passwords are entered by the department when creating their accounts. Only password hashes are saved, not the NIC as a separate field.

At first login, all account types must enter and confirm a password of 8–128 characters. Reusing the current password is allowed. Clicking Save and Continue completes this step; there is no Change Password option afterwards. Password eye buttons reveal/hide text without submitting the form.

If a user forgets a password or wants to change it later, the department runs this command locally:

```powershell
.\.venv\Scripts\python.exe setup.py password
```

Choose the role and account email and set a temporary password. On next access the user completes the first-login step again. Do not send users your MySQL password or `config.json`.

## Import the Excel workbook

1. HOD opens Manage System → Import.
2. Enter academic year as `YY/YY` and choose semester 1 or 2.
3. Select the original multi-sheet attendance `.xlsx` workbook, then Preview Import.
4. If new students lack accounts, download the account template, enter confirmed Email and NIC values, attach that CSV/XLSX file and preview again.
5. Click Import Students and Modules to save. Preview alone saves no records.

Account file first-row headings: `Reg_no,Email,NIC`. The workbook itself has no email/NIC fields. A NIC can contain 12 digits or 9 digits followed by V/X. Format cells as text to preserve all digits; a rounded/scientific CSV string is rejected. Errors identify the field and row. Existing passwords are preserved on reimport.

Import Modules Only saves components without creating students and leaves the preview available. Student import requires account details for every new student. Repeated registration numbers across sheets share one account but receive separate component memberships. Reimport is additive and does not delete historical memberships or attendance.

Worksheet names identify the component. For example `ICT 1407` becomes **ICT 1407(T)** on screen, and `ICT 1407 Practical` becomes **ICT 1407(P)**. The unsuffixed theory code stays in SQL for compatibility; the practical code is stored with `(P)`. The database's `course` table represents each separately teachable component. No primary-key rewrite of historical records is performed.

The importer locates `Reg_no` and `Name with Initials`. Missing names can be recovered from another sheet with the exact same registration number; unresolved names produce a sheet/row error. Workbook attendance marks, session dates and lecturer labels are not imported as saved attendance. Module year comes from the first digit of the four-digit code; academic year and semester come from the import form. Split the workbook if sheets belong to different academic years or semesters. Correct mismatched tab names before upload.

Student lists use separate year tabs, search, programme and calculated batch filters, with ten rows per page. Study year is the highest enrolled module year within the selected academic year; it is not advanced by the calendar year alone. ASP/ASB registrations display as Computer Science; others display as ICT.

Batch is calculated in SQL: `ICT/2024/146 → 23/24`, `ASP/2023/001 → 22/23`. No manual batch assignment or batch column remains. Supported registration format is programme/year/number. Unrecognised legacy registrations cannot have a batch inferred and should be corrected in source data.

## Roles, assignments and attendance

- **HOD:** imports, staff creation/types, semesters, theory/practical assignments, visiting-lecturer coordinators, teaching-end dates, marking/updating, full reports.
- **Lecturer / Visiting Lecturer:** sees and accesses only directly assigned components or components for which they are the assigned coordinator. Cannot generate All Modules or scholarship reports.
- **Demonstrator:** stored as an academic staff account with type Demonstrator; HOD assigns it to practical components. It receives the same restricted dashboard, marking and individual-module report access for its assigned practicals.
- **Coordinator:** a regular lecturer assigned by HOD to a specific visiting lecturer and component/year. The visiting lecturer must first have that component assignment. Both may mark and update it. Coordinator is an assignment, not another account to create.
- **AR:** creates sessions, reviews medicals, generates full/module and Mahapola/bursary attendance reports. Cannot perform general Present/Absent marking.
- **Student:** own attendance only; no medical upload, message form, other-student data, profile tabs or batch selector.

Create class sessions from the dashboard, then select semester, component and session. Each component/year has a plan of **14 sessions** and session week numbers 1–14. New session creation stops at 14. Existing installations with more sessions are retained; student predictions flag these for department review.

Mark Attendance opens the registration-number-only popup. Mark All Present affects the entire class, including rows hidden by search; change absentees and Save Attendance. Update Attendance handles corrections and medical approvals. Stale concurrent updates are rejected. HOD sees Updated By and Updated Time for each saved session; old records show Not recorded until an update is actually made. Per-student changes are also stored in `attendance_audit` and included in full report update history for HOD/AR.

## Physical medical documents

There is no student submission through the website. Documents go to staff physically.

- **MC:** a saved absence can be marked Medical within 14 calendar days after its class date (day 14 included).
- **SMC / Special Medical:** only AR can approve this after the component's 14-week teaching period ends. It changes a saved absence/medical record, never a Present record.
- HOD can set the end date under Manage System → Modules. It must be at least 14 weeks after the first session. If no end date is set, the system uses first-session date + 14 weeks. Set an accurate later date where the teaching calendar has breaks.
- A late medical after the normal window but before the period ends cannot be approved as Special Medical yet.
- MC and SMC remain absences for percentage calculations and do not increase Present. They are identified separately in history and reports. This preserves the existing calculation rule; no unstated medical eligibility credit is assumed.

## Student dashboard and predictions

Attendance refreshes every five seconds while the page is visible and immediately when returning to it. Only saved changes appear. Click a component to see its session dates, weeks and statuses. No message panel or Action column appears.

Percentage = Present / recorded sessions × 100. A recorded session has at least one saved attendance entry; empty scheduled placeholders do not count yet. Saved future-dated sessions are included, fixing the earlier missing-session problem.

Best possible final percentage = `(Present + remaining sessions) / 14 × 100`, with remaining = `14 − recorded sessions`. For 5 attended out of 9 recorded, five remain: maximum is `10/14 = 71.43%`. The dashboard warns the student that the requirement is no longer reachable. This is an on-screen warning, not an email or SMS. Predictions assume the 14-session plan, future attendance at all remaining sessions, and the stated medical rule.

Eligibility remains **strictly greater than 80%**, as requested earlier; exactly 80% is Ineligible. During teaching the dashboard shows Above threshold / Can recover / Cannot reach threshold, rather than treating a provisional percentage as a final decision. With no recorded sessions the result is Not assessed.

## Reports

Filter by academic year, study year, semester, calculated batch, component and optional dates. HOD and AR can generate All Modules; other academic staff must choose one assigned component. Restrictions also apply to the detailed preview and export endpoints.

- **Generate Summary:** compact website table, one row per component for All Modules. It shows student numbers, sessions, Present/Absent totals and average individual attendance percentage.
- **View Detailed Report:** a preview with per-student component totals, medical counts, eligibility and session-by-session statuses, before downloading.
- **Download Excel:** all matching rows, not only the current page. Includes a summary, separate component worksheets with registration/name, each saved session's date/week and P/A/MC/SMC, totals, percentage and eligibility. HOD/AR receive update history too. Filters and rules are recorded in Report details. Index numbers are omitted because the supplied database has no index-number field; they are not invented.
- **Mahapola / Bursary Attendance:** HOD/AR only. One summary row per student with totals across selected components; an optional registration number limits it to one student. Excel includes a separate sheet per student as well as component details. This supplies attendance evidence; it does not decide scholarship entitlement.

Module average is the mean of enrolled students' unrounded percentages within the selected batch. Display rounds to two decimals. For scholarship summaries the overall percentage is total attended student-sessions divided by total recorded student-sessions, weighted by component session counts. These measures are different and the report columns reflect that.

If someone is enrolled after a session was marked, a missing individual entry is not invented as present or absent. Total Sessions still includes that recorded class. Reports flag unmarked entries; correct those before using a final report.

SQL performs registration-to-batch calculation, account/role lookup, membership links, assignments, filtering, management pagination, session/mark persistence, audit history and attendance report counts/percentages/averages/eligibility. Spreadsheet formatting and password hashing use Python.

## Troubleshooting

- **This site can't be reached / connection refused:** start `app.py` and keep the terminal running. If it exits, read the terminal error.
- **Python not found:** use `py`, or install Python and reopen the terminal.
- **Missing .venv python.exe:** run `py -m venv .venv`, then install requirements.
- **ModuleNotFoundError:** run the requirements command using the same `.venv` interpreter as `app.py`.
- **config.json missing:** run `setup.py configure`.
- **MySQL 1045:** wrong MySQL user/password or account permissions. Use the credentials that work in Workbench.
- **MySQL 1054/1146:** ensure the configured database is the right one and run the upgrade. Do not drop the database.
- **MySQL 1064:** a query syntax error, not proof that MySQL is offline. Report the code and terminal output.
- **Can't connect to MySQL:** check the Windows MySQL service and configured host/port.
- **No components after import:** Preview doesn't save; click an import action, then check academic year/semester. Practical assignments must be created separately.
- **Lecturer sees no components:** HOD must assign the correct component and academic year, or assign the person as its coordinator.
- **Old page appearance:** stop/restart Flask after replacing files and press Ctrl+F5.

## Checks and files to keep private

```powershell
.\.venv\Scripts\python.exe -m unittest discover -q
```

Tests use mock connections plus isolated SQLite fixtures with equivalents of MySQL string functions to evaluate report queries, batch derivation and Excel matrices. They also cover permissions, imports, first-login restrictions, coordinator checks and medical boundaries. These are not a live MySQL server test; verify the migration and account flows on your own MySQL installation before using real attendance.

Do not push `.venv`, `config.json`, `.session-secret`, `.activation-codes.json`, `.imports`, caches, account-detail files or database exports with personal data to GitHub. The ZIP excludes local secrets and contains no real student dataset. Hosting configuration is separate from this local setup.

## University image sources

The bundled images are real assets from official university sites, not generated campus pictures:

- Campus photo: https://aps.rjt.ac.lk/wp-content/uploads/2019/10/Slider-1.jpg (Faculty of Applied Sciences homepage, https://aps.rjt.ac.lk/).
- University crest: https://www.rjt.ac.lk/wp-content/uploads/2022/05/crest.jpg (https://www.rjt.ac.lk/university-crest/).

Both are stored locally under `static/images`, so the login page doesn't depend on hotlinking or internet access. University ownership of these assets is unchanged.
