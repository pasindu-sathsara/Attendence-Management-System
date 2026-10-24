# Attendance Management System — Setup

## Requirements

- Windows with Python 3.11 or newer.
- MySQL Server 8.0.16 or newer and MySQL Workbench.
- VS Code and a web browser.

## New installation

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

Choose `hod` and enter the requested account details.

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
5. Select the workbook and completed account file, preview again, then click **Import Students and Modules**. Existing accounts keep their passwords.
6. Open **Staff** and create the required staff accounts.
7. Open **Assignments** and assign staff to their modules. Assign demonstrators to practical components. Assign a coordinator after assigning a visiting lecturer to the module.
8. Check the semester dates for all imported study years. All modules in the same academic year, study year, and semester share these dates.

## Start the system later

Open the project folder in VS Code and run:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:5000**. MySQL Server must be running.
