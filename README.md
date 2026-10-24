# Attendance Management System

Simple Flask, vanilla JavaScript and MySQL 8.0.16+ application. No sample accounts, students, modules or attendance are installed.

## Latest small update

This update adds the two large login tabs, removes the website password-change feature, fixes the HOD options queries (MySQL 1064), and distinguishes query errors from connection failures. If you already upgraded the database for the previous version, this update needs only replacing code files and restarting Flask. No additional database changes are required.

## Update your existing project

Do not drop your database.

1. Stop Flask with Ctrl+C in the VS Code terminal.
2. Extract the ZIP and copy its contents into your project folder, replacing the old code. Keep your existing `config.json`, `.venv` and `.session-secret`.
3. Open the project folder in VS Code. Run in its PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py upgrade
.\.venv\Scripts\python.exe app.py
```

4. Open http://127.0.0.1:5000 and press Ctrl+F5. Use **Staff login** for HOD, lecturer or AR accounts.

If configuration is missing, run `setup.py configure` first, entering your existing MySQL connection details. The upgrade uses `student_attendance_system`, the database name in your supplied SQL. If you renamed it, change the `USE` line in `database/upgrade.sql` to your actual database name before running the upgrade.

Alternatively, execute `database/upgrade.sql` in MySQL Workbench instead of `setup.py upgrade`. Both use the same script. It can be run again; it does not delete records.

The upgrade adds a nullable `student.batch` column, permits `Ven` in AR titles, and makes the existing AR reference on `class_session` optional. Existing AR references are retained. It also creates `student_course` if absent. This version targets your latest `1407DBFinal.sql` schema, including `course_offering`; it does not convert older incompatible schemas.

Existing students have no batch assigned automatically. Open **Manage System → Students**, choose the academic year/study year, select the students and save their correct batch (e.g. 23/24). Selection carries across pages; changing a filter clears selection. The header checkbox selects only the current page. No registration-number-to-batch mapping is guessed.

## Fresh installation only

Run `database/schema.sql` in MySQL Workbench to create a new empty database. Do not run this script over your existing installation.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py configure
.\.venv\Scripts\python.exe setup.py create-staff
.\.venv\Scripts\python.exe app.py
```

Choose `hod` when creating the first staff account. The command creates its lecturer record and related HOD record. An AR account is optional.

## Login and passwords

- Large Student Login | Staff Login tabs appear above the form. Students: `/UI.html`; staff: `/staff-login.html`.
- There is no public registration. The department creates accounts.
- The login page does not choose HOD/lecturer permissions. The server reads the account's role from MySQL.
- There is no Change Password button, dialog or public password-change endpoint.
- For a forgotten password, the department can use `python setup.py password` locally.
- Students use their email and the department-provided NIC as the initial password. NICs are hashed; there is no plain NIC database column. Password resets are handled by the department using the local setup command.

## Import students and modules

1. HOD opens **Manage System → Import**.
2. Enter the academic year (`YY/YY`) and semester. Choose the original attendance XLSX workbook.
3. Use Preview Import. The preview does not save records.
4. If new accounts lack details, download the account template, fill confirmed Email and NIC values, select it alongside the workbook, and preview again.
5. Click **Import Students and Modules**. **Import Modules Only** saves module offerings without creating students.

Account CSV/XLSX headers: `Reg_no,Email,NIC,Batch`. Batch is optional but needed to separate batch reports. Use one Batch value per student for mixed-batch files. Alternatively use the import form's batch field only when the whole upload shares that batch. A row's Batch takes priority over the form's value. Blank batch values preserve existing assignments. Existing students' batches can also be assigned in the Students tab without an account file.

NIC accepts 12 digits or 9 digits plus V/X (case preserved for the password). Store NIC and Batch cells as text. Numeric XLSX NICs with all 12 digits intact are supported. Rounded/scientific-notation CSV strings are rejected rather than guessed. Validation errors identify the account-file row and field.

The supplied attendance workbook has module sheets with `Reg_no` and `Name with Initials` headings, but no emails/NICs. The importer combines each student's module memberships across sheets. A missing name is filled from another sheet with the exact same registration number; if no matching name exists, the error identifies its sheet and row. Study year comes from the first digit of each module's four-digit code; academic year and semester come from the import form. Split uploads if the sheets belong to different academic years or semester numbers.

Module codes come from worksheet names. In the supplied workbook, the ICT4302 tab has a different code in its heading; correct the tab name first if it is wrong. Theory/practical sheets with the same module code share one roster because the existing schema does not distinguish them. Attendance marks, dates and lecturer names in the workbook are not imported.

Reimporting preserves passwords, accounts and existing module links. It adds memberships; it does not delete old ones. Conflicting emails are rejected. Student grouping uses their highest enrolled module study year in that academic year. ASP/ASB registrations display as Computer Science; other registrations display as ICT.

## Manage and mark attendance

- HOD manages Import, Students, Modules, Assignments, Staff and Semesters in separate tabs. Lists have search and ten rows per page.
- Staff titles: Mr, Mrs, Ms, Ven. Existing titles can be changed in the Staff tab. Lecturer lists display title and name, without email.
- HOD assigns a lecturer to a specific module and academic year.
- HOD, AR and assigned lecturers can create sessions from the dashboard. No AR account is required for HOD/lecturer sessions. The optional session email remains an AR reference; it is not a generic creator field.
- Lecturers see and access only assigned module offerings. The server applies this restriction to session creation, marking, updates, reports and Excel exports.
- Choose semester, module and session, then open Mark Attendance. Mark All Present sets the whole class, including rows hidden by search; change absentees individually. Nothing is saved until Save Attendance.
- Update Attendance corrects saved records. MC is available only for a student already marked absent. Physical medical documents remain outside the website.
- AR can create sessions and change an existing absence to MC; it cannot mark general attendance or change present records.
- Students see only their own module attendance, with no other students' details or medical-document tabs.

## Reports and SQL calculations

HOD can select academic year, study year, semester, batch, module and optional dates. All Modules gives one row per module offering, including empty modules. Individual Module gives one row per enrolled student. Lecturers must select one assigned module; they cannot request All Modules, including through the export endpoint.

Batch means admission cohort (e.g. 23/24), separate from academic year and study year. Choosing a batch includes only that batch's students in percentages and averages. Unassigned batches are included only in All batches.

A **recorded session** is a class session with at least one saved attendance record. An empty scheduled session does not enter the denominator yet. Saved attendance counts even if its session date is in the future, provided it falls within the selected report dates. This fixes the earlier missing-session count. Multiple students' marks for the same session still count as one session.

- Student attendance percentage = Present / Total recorded module sessions × 100.
- Eligibility is strictly greater than 80%; exactly 80% is Ineligible.
- No recorded sessions: percentage is blank and eligibility is Not assessed.
- MC remains an absence and does not increase Present.
- If a student was enrolled after a session was marked, missing marks are not invented as present or absent. The report flags unmarked records; update those sessions before using the final report. Total Sessions still includes them.
- HOD Average Attendance % = arithmetic mean of the individual students' unrounded percentages in that module and selected batch. Display rounds to two decimal places. Modules without enrolled students show no average.
- Individual columns: Reg No, Name, Present, Absent, Total Sessions, Attendance %, Eligibility.
- Excel includes all matching rows, not just the displayed page, and a Report details sheet recording filters and calculation rules. There is no Print button.

MySQL queries handle authentication/account lookup, imports, membership links, staff assignments, session creation, attendance saves/updates, filtering, management-list pagination, and report counts/percentages/averages/eligibility. `ATTENDANCE_SQL` in app.py contains the shared report/student calculation. Query values use parameters.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -q
```

Tests cover permissions, account matching, NIC validation, marking/MC rules, import persistence, batch-separated reporting, >80 eligibility, future-dated recorded sessions and Excel output. The report tests execute the calculation queries against an isolated SQLite fixture; other backend tests mock MySQL. They do not replace a check against your actual MySQL database. Test fixtures are never installed into the application database.

Keep the Flask terminal running and use the localhost URL, not HTML files opened directly. The VS Code browser configuration opens that URL but does not start Flask.

This package is configured for local use; external hosting needs its own deployment settings. Do not commit config.json, .session-secret, .activation-codes.json, .imports, .venv or account-details files with personal data. Keep your original database backup before any upgrade.
