import io
import unittest
from datetime import date,timedelta
from unittest.mock import patch
from werkzeug.security import generate_password_hash,check_password_hash
import app as backend
from test_reports import ReportTests

class NewFeatureTests(unittest.TestCase):
 def setUp(self):
  backend.app.config['TESTING']=True
  self.client=backend.app.test_client()
  self.signin('lecturer')
 def signin(self,role,first=0):
  with self.client.session_transaction() as s:s.update(email='staff@example.com',role=role,name='Mr Staff',csrf='token')
  return {'email':'staff@example.com','must_change_password':first}
 def post(self,url,data):return self.client.post(url,json=data,headers={'X-CSRF-Token':'token'})
 def test_first_login_blocks_dashboard_and_api_even_with_old_cookie(self):
  for role in ['student','lecturer','hod','ar']:
   account=self.signin(role,1)
   with patch.object(backend,'query',return_value=account):
    self.assertEqual(self.client.get('/api/my-attendance' if role=='student' else '/api/options').status_code,403)
    self.assertEqual(self.client.get('/student-dashboard.html' if role=='student' else '/dashboard.html').location,'/first-password.html')
 def test_first_password_can_reuse_nic_but_cannot_run_twice(self):
  account=self.signin('student',1);nic='200012345678'
  with patch.object(backend,'query',return_value=account),patch.object(backend,'execute',return_value=1) as execute,patch.object(backend,'db'):
   self.assertEqual(self.post('/api/first-password',{'password':nic,'confirm':nic}).status_code,200)
   self.assertTrue(check_password_hash(execute.call_args.args[1][0],nic))
  with patch.object(backend,'query',return_value=self.signin('student')),patch.object(backend,'execute',return_value=0):
   self.assertEqual(self.post('/api/first-password',{'password':nic,'confirm':nic}).status_code,403)
 def test_login_redirects_new_accounts_to_first_password(self):
  with patch.object(backend,'query',return_value={'email':'s@example.com','name':'Student','password_hash':generate_password_hash('password123'),'must_change_password':1}):
   response=self.post('/api/login',{'portal':'student','email':'s@example.com','password':'password123'})
   self.assertEqual(response.json['next'],'/first-password.html')
 def test_coordinator_assignment_requires_assigned_visiting_lecturer(self):
  self.signin('hod')
  with patch.object(backend,'course_access',return_value={'course_code':'ICT 1407','academic_year':'26/27'}),patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},{'type':'Lecturer'},None]),patch.object(backend,'execute') as ex:
   self.assertEqual(self.post('/api/coordinators',{'course':'ICT 1407~26/27','email':'l@example.com','visiting':'v@example.com'}).status_code,400);ex.assert_not_called()
 def test_assigned_coordinator_can_access_the_exact_offering(self):
  with backend.app.test_request_context('/'):
   backend.session.update(role='lecturer',email='staff@example.com')
   with patch.object(backend,'query',side_effect=[{'course_code':'ICT 1407','academic_year':'26/27'},{'email':'staff@example.com'}]) as query:
    backend.course_access('ICT 1407~26/27');self.assertIn('module_coordinator',query.call_args.args[0]);self.assertEqual(query.call_args.args[1][3:],('staff@example.com','ICT 1407','26/27'))
 def test_demo_cannot_be_assigned_to_theory(self):
  self.signin('hod')
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},{'type':'Demonstrator'}]),patch.object(backend,'course_access',return_value={'course_code':'ICT 1407','academic_year':'26/27'}),patch.object(backend,'execute') as ex:
   self.assertEqual(self.post('/api/assignments',{'email':'d@example.com','course':'ICT 1407~26/27'}).status_code,400);ex.assert_not_called()
 def medical_save(self,role,new_status,special_allowed,normal_allowed=True,current_status=0,reason=None):
  self.signin(role);old={'email':'s@example.com','attendance_status':current_status,'absent_reason':reason}
  payload={'course':'ICT 1407~26/27','session':'2026-01-01|1','mode':'update','statuses':{'ICT/2024/001':new_status},'originals':{'ICT/2024/001':backend.attendance_status(old)}}
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},[old]]),patch.object(backend,'selected_session',return_value=({'course_code':'ICT 1407','academic_year':'26/27'},date(2026,1,1),1)),patch.object(backend,'roster',return_value=[{'email':'s@example.com','reg_number':'ICT/2024/001'}]),patch.object(backend,'medical_rules',return_value={'normal':normal_allowed,'special':special_allowed}),patch.object(backend,'execute') as ex,patch.object(backend,'db'):
   result=self.post('/api/attendance',payload)
   return result,list(ex.call_args_list)
 def test_special_medical_only_ar_after_period_and_audited(self):
  for role,after,expected in [('lecturer',True,403),('hod',True,403),('ar',False,403),('ar',True,200)]:
   result,calls=self.medical_save(role,'special',after)
   self.assertEqual(result.status_code,expected)
   if expected!=200:self.assertFalse(calls)
   else:
    self.assertEqual(calls[0].args[1][-2:],(0,'SMC'))
    self.assertIn('attendance_audit',calls[1].args[0]);self.assertEqual(calls[1].args[1][-2:],('Mr Staff','staff@example.com'))
 def test_normal_medical_late_or_present_is_rejected(self):
  self.assertEqual(self.medical_save('lecturer','medical',False,normal_allowed=False)[0].status_code,400)
  self.assertEqual(self.medical_save('ar','special',True,current_status=1)[0].status_code,400)
 def test_lecturer_cannot_undo_ar_special_medical(self):
  self.assertEqual(self.medical_save('lecturer','absent',True,reason='SMC')[0].status_code,403)
 def test_ar_cannot_mark_present(self):
  response,calls=self.medical_save('ar','present',True)
  self.assertEqual(response.status_code,403);self.assertFalse(calls)
 def test_medical_period_boundary(self):
  with patch.object(backend,'query',return_value={'end_date':date.today()}):
   rules=backend.medical_rules({'course_code':'X','academic_year':'26/27','study_year':1,'semester_number':1},date.today()-timedelta(days=14))
   self.assertTrue(rules['normal']);self.assertFalse(rules['special'])
  with patch.object(backend,'query',return_value={'end_date':date.today()-timedelta(days=1)}):
   rules=backend.medical_rules({'course_code':'X','academic_year':'26/27','study_year':1,'semester_number':1},date.today()-timedelta(days=15))
   self.assertFalse(rules['normal']);self.assertTrue(rules['special'])
 def test_student_cannot_view_another_module_history(self):
  self.signin('student')
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},None]):
   self.assertEqual(self.client.get('/api/my-sessions?course=OTHER~26/27').status_code,403)

class NewReportTests(ReportTests):
 def test_ar_full_detailed_export_has_separate_component_sheets(self):
  with self.client.session_transaction() as s:s['role']='ar'
  response=self.get('/api/report.xlsx?academic_year=26/27&batch=23/24')
  self.assertEqual(response.status_code,200)
  from openpyxl import load_workbook
  book=load_workbook(io.BytesIO(response.data))
  sheet=book['ICT 1305(T) 26-27'];rows=list(sheet.values)
  self.assertIn('2099-01-01 · W1',rows[0]);self.assertEqual(rows[1][2:7],('P','P','P','P','A'))
  self.assertEqual(len(rows),3)
 def test_scholarship_report_separates_students_and_batch(self):
  response=self.get('/api/report?academic_year=26/27&batch=24/25&type=scholarship')
  self.assertEqual(response.status_code,200);self.assertEqual(response.json['kind'],'scholarship')
  self.assertEqual(len(response.json['rows']),1);self.assertEqual(response.json['rows'][0]['batch'],'24/25')
 def test_student_prediction_uses_remaining_fourteen_sessions(self):
  with self.client.session_transaction() as s:s.update(role='student',email='a')
  response=self.get('/api/my-attendance')
  self.assertEqual(response.status_code,200)
  row=next(r for r in response.json['rows'] if r['course_code']=='ICT 1305')
  self.assertEqual(row['remaining'],9);self.assertEqual(row['maximum'],92.86)
  self.conn.execute("UPDATE student_class_session SET attendance_status=0 WHERE email='a'")
  for week in range(7,11):
   self.conn.execute("INSERT INTO class_session(course_code,academic_year,date,week_number) VALUES ('ICT 1305','26/27',?,?)",(f'2099-01-{week:02}',week))
   self.conn.execute("INSERT INTO student_class_session VALUES ('b','ICT 1305',?,?,1,NULL)",(f'2099-01-{week:02}',week))
  row=next(r for r in self.get('/api/my-attendance').json['rows'] if r['course_code']=='ICT 1305')
  self.assertEqual(row['prediction'],'Cannot reach threshold')
 def test_detail_preview_contains_actual_session_statuses(self):
  response=self.get('/api/report-view?academic_year=26/27&batch=23/24')
  self.assertEqual(response.status_code,200)
  row=next(r for r in response.json['rows'] if r['reg']=='ICT/2024/001' and r['course_code']=='ICT 1305')
  self.assertIn('2099-01-05 W5: absent',row['sessions'])
 def test_batch_sql_formula(self):
  for registration,expected in [('ICT/2024/146','23/24'),('ASP/2023/001','22/23'),('ASB/2025/222','24/25'),('bad',None)]:
   self.conn.execute('UPDATE student SET reg_number=? WHERE email=?',(registration,'a'))
   sql='SELECT '+backend.BATCH_SQL+' AS batch FROM student s WHERE email=?'
   self.assertEqual(self.conn.execute(sql.replace('RIGHT(','RIGHT_STR('),('a',)).fetchone()['batch'],expected)

if __name__=='__main__':unittest.main()
