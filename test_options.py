import sqlite3
import unittest
from unittest.mock import patch
import mysql.connector
import app as backend

def sql_functions(conn):
 import re
 conn.create_function('REGEXP',2,lambda pattern,value:bool(re.search(pattern,value or '')))
 conn.create_function('CONCAT',-1,lambda *v:''.join(str(x) for x in v))
 conn.create_function('CONCAT_WS',-1,lambda sep,*v:sep.join(str(x) for x in v if x is not None))
 conn.create_function('SUBSTRING_INDEX',3,lambda s,sep,n:sep.join(s.split(sep)[:n] if n>0 else s.split(sep)[n:]))
 conn.create_function('LPAD',3,lambda s,n,p:str(s).rjust(n,p))
 conn.create_function('MOD',2,lambda a,b:a%b)
 conn.create_function('RIGHT_STR',2,lambda s,n:s[-n:])
 conn.create_function('GREATEST',-1,max)

class OptionsTests(unittest.TestCase):
 def setUp(self):
  self.client=backend.app.test_client()
  self.conn=sqlite3.connect(':memory:');self.conn.row_factory=sqlite3.Row
  sql_functions(self.conn)
  self.conn.create_function('CONCAT_WS',-1,lambda sep,*values:sep.join(str(v) for v in values if v is not None))
  self.conn.executescript("""
   CREATE TABLE hod(email TEXT); INSERT INTO hod VALUES ('head@example.com');
   CREATE TABLE lecturer(email TEXT,name TEXT,title TEXT,type TEXT,must_change_password INT);
   INSERT INTO lecturer VALUES ('l@example.com','Lecturer','Mr','Lecturer',0),('u@example.com','Untitled',NULL,'Lecturer',0),('head@example.com','Head','Mr','Lecturer',0);
   CREATE TABLE lecturer_course(email TEXT,course_code TEXT,academic_year TEXT);
   INSERT INTO lecturer_course VALUES ('l@example.com','ICT 1305','26/27');
   CREATE TABLE course(course_code TEXT,study_year INT,semester_number INT);
   INSERT INTO course VALUES ('ICT 1305',1,1);
   CREATE TABLE course_offering(course_code TEXT,academic_year TEXT);
   INSERT INTO course_offering VALUES ('ICT 1305','26/27');
   CREATE TABLE semester(academic_year TEXT,study_year INT,semester_number INT);
   INSERT INTO semester VALUES ('26/27',1,1);
   CREATE TABLE student(reg_number TEXT); INSERT INTO student VALUES ('ICT/2024/001');
  """)
  with self.client.session_transaction() as s:s.update(email='head@example.com',role='hod',csrf='token')
 def tearDown(self):self.conn.close()
 def query(self,sql,args=(),one=False):
  rows=[dict(r) for r in self.conn.execute(sql.replace('RIGHT(', 'RIGHT_STR(').replace('%s','?'),args)]
  return (rows[0] if rows else None) if one else rows
 def test_hod_options_executes_queries_and_preserves_title_spacing(self):
  with patch.object(backend,'query',side_effect=self.query):r=self.client.get('/api/options')
  self.assertEqual(r.status_code,200)
  self.assertEqual([l['name'] for l in r.json['lecturers']],['Mr.Head','Mr.Lecturer','Untitled'])
  self.assertEqual(r.json['assignments'][0]['name'],'Mr.Lecturer')
  self.assertEqual(r.json['courses'][0]['code'],'ICT 1305~26/27')
 def test_login_tabs_and_no_password_change(self):
  for path,active in [('/UI.html','Student Login'),('/staff-login.html','Staff Login')]:
   r=self.client.get(path)
   self.assertEqual(r.status_code,200)
   self.assertIn(b'Student Login',r.data);self.assertIn(b'Staff Login',r.data)
   self.assertIn(('aria-current="page">'+active).encode(),r.data)
   self.assertNotIn(b'Change Password',r.data);self.assertNotIn(b'password-dialog',r.data)
  self.assertEqual(self.client.post('/api/change-password',json={},headers={'X-CSRF-Token':'token'}).status_code,404)
 def test_database_errors_distinguish_sql_and_connection(self):
  for number,status,word in [(1064,500,'syntax'),(1054,500,'upgrade'),(2003,503,'connect')]:
   with patch.object(backend,'query',side_effect=mysql.connector.Error(errno=number)):
    r=self.client.get('/api/options')
   self.assertEqual(r.status_code,status);self.assertIn(word,r.json['error'])

if __name__=='__main__':unittest.main()
