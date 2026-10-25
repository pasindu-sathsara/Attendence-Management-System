# Attendance Management System — Setup

## Requirements

- Windows with Python 3.11 or newer.
- MySQL Server 8.0.16 or newer and MySQL Workbench.
- VS Code and a web browser.

## New installation

A new installation starts with empty tables. No student, staff, module or attendance data is supplied. Create the first HOD account below, then use that account to configure the system.

1. Extract the project and open its folder in VS Code.
2. Open MySQL Workbench and connect to your MySQL server.
3. Choose **File → Open SQL Script**, open `database/schema.sql`, and execute the whole script. Use this script only for a new database.
4. In the VS Code terminal, run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py configure
```

Enter your MySQL connection details:

- Host: `127.0.0.1` for a local server.
- Port: `3306`, unless you changed it.
- Username: your MySQL username.
- Password: your MySQL password. Characters do not appear while typing; press Enter when finished.
- Database: `student_attendance_system`.

5. Create the first HOD account:

```powershell
.\.venv\Scripts\python.exe setup.py create-staff
```

When prompted, enter:

- Role: `hod`
- Email: the email you want to use for HOD sign-in.
- Password: a password of at least 8 characters.
- Confirm password: enter the same password again.
- Full name: the HOD's name.
- Title: `Mr`, `Mrs` or `Ms`.

Wait for **Account saved.** This creates the HOD's lecturer account and HOD role. These login details are separate from your MySQL username and password.

6. Start the system:

```powershell
.\.venv\Scripts\python.exe app.py
```

7. Open **http://127.0.0.1:5000**. Keep the terminal open. Use **Staff Login** for the HOD account and complete the first-login password step. The same password may be kept.

Open the website through this address, not by double-clicking an HTML file or using Live Server.

## Update an existing installation

1. Back up your database using MySQL Workbench → **Server → Data Export**.
2. Stop the running server with **Ctrl+C**.
3. Copy the updated project files into your project folder. Keep your existing `.venv`, `config.json`, and `.session-secret`.
4. Run these commands in that project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py upgrade
.\.venv\Scripts\python.exe setup.py check
.\.venv\Scripts\python.exe app.py
```

If `config.json` is missing, run `setup.py configure` before `setup.py upgrade`, entering the existing database's details.

5. Open **http://127.0.0.1:5000** and press **Ctrl+F5**.

Use `setup.py upgrade` for an existing database. Do not drop the database or run the fresh-installation script over it.

## Initial system configuration

1. Sign in as HOD and open **Manage System → Semesters**.
2. Enter the academic year as `YY/YY`, study year, semester number, start date, and end date. Save each required semester. Use **Edit** to set dates for an existing semester.
3. Open **Import**, select the academic year and semester, choose the attendance workbook, and click **Preview Import**.
4. Download the account template. Fill each new student's Email and NIC, keeping the registration numbers unchanged. Format NIC cells as text and save as CSV or XLSX.
5. Select the workbook and completed account file, preview again, then click **Import Students and Modules**. The import creates the student accounts and module enrolments. A new student signs in with the imported email and NIC as the initial password, then completes the first-login password step. Existing accounts keep their passwords.
6. Open **Staff** and create the required lecturer, visiting lecturer, demonstrator and AR accounts. Enter each account's email and initial password. New staff complete the first-login password step too.
7. Open **Assignments** and assign staff to their modules. Assign demonstrators to practical components. Assign visiting lecturers directly to their modules. Assign the HOD to their own teaching modules too; the HOD can mark attendance and review normal medicals or excuse letters only for assigned modules.
8. Check the semester dates for all imported study years. All modules in the same academic year, study year, and semester share these dates.
9. Sign in as assigned teaching staff, create class sessions in **Dashboard**, and mark attendance. Use the actual class date and a week number from 1 to 14.

## Start the system later

Open the project folder in VS Code and run:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:5000**. MySQL Server must be running.

## Setup checks

To test the database connection and list its tables:

```powershell
.\.venv\Scripts\python.exe setup.py check
```

- If `config.json` is missing, run `setup.py configure` in the project folder.
- If the website reports a missing database column (1054), stop the app, run `setup.py upgrade` using the latest project files, and restart it.
- If password characters do not appear in the terminal, continue typing and press Enter. Password input is hidden.
- If the browser shows an older page after replacing files, press **Ctrl+F5**.
- Updating code does not clear records already stored in your MySQL database.
