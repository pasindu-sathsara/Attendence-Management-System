"""Run locally to configure MySQL or create the first staff accounts."""
import argparse
import getpass
import json
from pathlib import Path
import mysql.connector
from werkzeug.security import generate_password_hash

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['configure','check','password','create-staff','upgrade'])
action=parser.parse_args().action
if action=='configure':
    settings={
        'host':input('MySQL host [127.0.0.1]: ').strip() or '127.0.0.1',
        'port':int(input('Port [3306]: ') or 3306),
        'user':input('MySQL user [root]: ').strip() or 'root',
        'password':getpass.getpass('MySQL password: '),
        'database':input('Database [student_attendance_system]: ').strip() or 'student_attendance_system'
    }
    connection=mysql.connector.connect(**settings)
    connection.close()
    (root/'config.json').write_text(json.dumps(settings,indent=2))
    print('Connection tested. Configuration saved.')
else:
    if not (root/'config.json').exists():
        raise SystemExit('Run python setup.py configure first.')
    settings=json.loads((root/'config.json').read_text())
    connection=mysql.connector.connect(**settings)
    cursor=connection.cursor()
    try:
        if action=='upgrade':
            script=(root/'database'/'upgrade.sql').read_text()
            for statement in script.split(';'):
                if statement.strip():
                    cursor.execute(statement)
                    if cursor.with_rows: cursor.fetchall()
            connection.commit()
            print('Database upgraded. Existing records preserved.')
        elif action=='check':
            cursor.execute('SHOW TABLES')
            print('\n'.join(row[0] for row in cursor.fetchall()))
        else:
            role=input('Role (student/lecturer/hod/ar): ').strip()
            tables={'student':'student','lecturer':'lecturer','hod':'lecturer','ar':'ar_user'}
            if role not in tables or (action=='create-staff' and role=='student'):
                raise ValueError('Choose a valid staff role.')
            email=input('Email: ').strip().lower()
            password=getpass.getpass('Password (8+ characters): ')
            if '@' not in email or len(password)<8 or password!=getpass.getpass('Confirm password: '):
                raise ValueError('Valid email and matching passwords required.')
            if action=='password':
                cursor.execute('UPDATE '+tables[role]+' SET password_hash=%s WHERE email=%s',(generate_password_hash(password),email))
                if not cursor.rowcount: raise ValueError('Account not found.')
            else:
                name=input('Full name: ').strip()
                if not name: raise ValueError('Name required.')
                for table in ('student','lecturer','ar_user'):
                    cursor.execute('SELECT email FROM '+table+' WHERE email=%s',(email,))
                    if cursor.fetchone(): raise ValueError('Email is already used.')
                title=input('Title (Mr/Mrs/Ms/Ven): ').strip()
                if title not in ('Mr','Mrs','Ms','Ven'): raise ValueError('Choose Mr, Mrs, Ms or Ven.')
                cursor.execute('INSERT INTO '+tables[role]+' (email,name,title,password_hash) VALUES (%s,%s,%s,%s)',(email,name,title,generate_password_hash(password)))
                if role=='hod': cursor.execute('INSERT INTO hod (email) VALUES (%s)',(email,))
            connection.commit()
            print('Account saved.')
    finally:
        cursor.close()
        connection.close()
