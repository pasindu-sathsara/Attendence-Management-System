"""Local administrator utilities. Does not change the schema."""
import json, secrets, getpass, argparse
from pathlib import Path
import mysql.connector
from werkzeug.security import generate_password_hash
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('action',choices=['configure','check','password','create-staff','activate']);args=p.parse_args()
if args.action=='configure':
 cfg={'host':input('MySQL host [127.0.0.1]: ').strip() or '127.0.0.1','port':int(input('Port [3306]: ') or 3306),'user':input('MySQL user [root]: ').strip() or 'root','password':getpass.getpass('MySQL password: '),'database':'student_attendance_system'}
 cn=mysql.connector.connect(**cfg);cn.close();(root/'config.json').write_text(json.dumps(cfg,indent=2));print('Connection tested. Configuration saved locally.');raise SystemExit
cfg=json.loads((root/'config.json').read_text());cn=mysql.connector.connect(**cfg);cur=cn.cursor()
try:
 if args.action=='check':
  cur.execute('SHOW TABLES');print('Connected. Tables:');print('\n'.join(r[0] for r in cur.fetchall()))
 elif args.action in ('password','create-staff'):
  role=input('Role (student/lecturer/hod/ar): ').strip();tables={'student':'student','lecturer':'lecturer','hod':'hod','ar':'ar_user'}
  if role not in tables or (args.action=='create-staff' and role=='student'):raise ValueError('Invalid role')
  email=input('Account email: ').strip().lower();pw=getpass.getpass('New password (8+ characters): ')
  if len(pw)<8 or pw!=getpass.getpass('Confirm password: '):raise ValueError('Passwords must match and contain 8+ characters')
  if args.action=='password':
   cur.execute('UPDATE '+tables[role]+' SET password_hash=%s WHERE email=%s',(generate_password_hash(pw),email))
   if not cur.rowcount:raise ValueError('Account not found')
  else:
   name=input('Full name: ').strip()
   if not name:raise ValueError('Name required')
   if role=='lecturer':cur.execute('INSERT INTO lecturer (email,password_hash,name,type) VALUES (%s,%s,%s,%s)',(email,generate_password_hash(pw),name,'Lecturer'))
   else:cur.execute('INSERT INTO '+tables[role]+' (email,password_hash,name) VALUES (%s,%s,%s)',(email,generate_password_hash(pw),name))
  cn.commit();print('Account saved.')
 else:
  email=input('Imported student email: ').strip().lower();cur.execute('SELECT email FROM student WHERE email=%s',(email,))
  if not cur.fetchone():raise ValueError('Student not found')
  token=secrets.token_urlsafe(18);path=root/'.activation-codes.json';codes=json.loads(path.read_text()) if path.exists() else {};codes[email]=generate_password_hash(token);path.write_text(json.dumps(codes));print('Give this one-time activation code to the student:',token)
finally:cur.close();cn.close()
