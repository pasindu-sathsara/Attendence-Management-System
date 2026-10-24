import unittest
from unittest.mock import patch
import app as backend

class BackendTests(unittest.TestCase):
 def setUp(self):
  backend.app.config['TESTING']=True
  self.client=backend.app.test_client()
  rules=patch.object(backend,'medical_rules',return_value={'normal':True,'special':False});rules.start();self.addCleanup(rules.stop)
 def login_session(self,role='lecturer'):
  with self.client.session_transaction() as s:s.update(role=role,email='staff@example.com',csrf='test-token',name='Staff')
 def post(self,path,payload):return self.client.post(path,json=payload,headers={'X-CSRF-Token':'test-token'})
 def test_private_page_redirects(self):
  self.assertEqual(self.client.get('/dashboard.html').status_code,302)
 def test_csrf_required(self):
  self.assertEqual(self.client.post('/api/attendance',json={}).status_code,403)
 def test_lecturer_cannot_manage(self):
  self.login_session()
  self.assertEqual(self.client.get('/manage-system.html').status_code,403)
  self.assertEqual(self.post('/api/assignments',{}).status_code,403)
 def test_student_cannot_mark(self):
  self.login_session('student');self.assertEqual(self.post('/api/attendance',{}).status_code,403)
 def test_pages_render_for_roles(self):
  for role,path in [('hod','/manage-system.html'),('lecturer','/dashboard.html'),('student','/student-dashboard.html')]:
   self.login_session(role)
   with patch.object(backend,'query',return_value={'email':'staff@example.com'}):
    r=self.client.get(path);self.assertEqual(r.status_code,200);self.assertNotIn(b'{{',r.data)
 def test_no_public_project_files(self):
  for p in ['/config.json','/app.py','/.session-secret']:self.assertEqual(self.client.get(p).status_code,404)
 def test_own_attendance_uses_session_identity(self):
  self.login_session('student')
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},{'name':'Student','reg_number':'R1'},[]]) as q:
   self.assertEqual(self.client.get('/api/my-attendance?email=another@example.com').status_code,200)
   self.assertEqual(q.call_args_list[-1].args[1],('staff@example.com',))
 def attendance_request(self,status='medical',mode='update',old_status=0,reason=None,original='absent'):
  self.login_session()
  payload={'course':'1201','session':'2026-10-12|1','mode':mode,'statuses':{'R1':status},'originals':{'R1':original}}
  rows=[{'email':'s@example.com','attendance_status':old_status,'absent_reason':reason}]
  return payload,rows
 def test_mc_rejects_saved_present(self):
  payload,rows=self.attendance_request(old_status=1,original='present')
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},rows]),patch.object(backend,'selected_session',return_value=({'course_code':'1201','academic_year':'26/27'},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]),patch.object(backend,'execute') as execute:
   self.assertEqual(self.post('/api/attendance',payload).status_code,400);execute.assert_not_called()
 def test_stale_update_rejected(self):
  payload,rows=self.attendance_request(original='present')
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},rows]),patch.object(backend,'selected_session',return_value=({'course_code':'1201','academic_year':'26/27'},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]),patch.object(backend,'execute') as execute:
   self.assertEqual(self.post('/api/attendance',payload).status_code,409);execute.assert_not_called()
 def test_mc_saved_as_absent_reason(self):
  payload,rows=self.attendance_request()
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},rows]),patch.object(backend,'selected_session',return_value=({'course_code':'1201','academic_year':'26/27'},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]),patch.object(backend,'execute') as execute,patch.object(backend,'db') as db:
   self.assertEqual(self.post('/api/attendance',payload).status_code,200)
   self.assertEqual(execute.call_args_list[0].args[1][-2:],(0,'MC'));db.return_value.commit.assert_called_once()
 def test_incomplete_class_rejected(self):
  payload,rows=self.attendance_request();payload['statuses']={}
  with patch.object(backend,'query',return_value={'email':'staff@example.com'}),patch.object(backend,'selected_session',return_value=({'course_code':'1201','academic_year':'26/27'},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]):
   self.assertEqual(self.post('/api/attendance',payload).status_code,400)

class UpdatedFlowTests(BackendTests):
 def test_login_detects_hod_through_lecturer(self):
  from werkzeug.security import generate_password_hash
  with self.client.session_transaction() as state: state['csrf']='test-token'
  account={'email':'head@example.com','name':'Head','password_hash':generate_password_hash('password123')}
  with patch.object(backend,'query',side_effect=[account,{'email':'head@example.com'}]):
   response=self.post('/api/login',{'email':'head@example.com','password':'password123','portal':'staff'})
   self.assertEqual(response.status_code,200)
   with self.client.session_transaction() as state:self.assertEqual(state['role'],'hod')
 def test_registration_disabled(self):
  self.assertEqual(self.client.get('/student-register.html').status_code,302)
  self.assertEqual(self.client.get('/staff-register.html').status_code,302)
  with self.client.session_transaction() as state:state['csrf']='test-token'
  self.assertEqual(self.post('/api/register',{}).status_code,404)
 def test_lecturer_access_checks_year(self):
  self.login_session()
  course={'course_code':'ICT 1305','academic_year':'26/27','study_year':1,'semester_number':1}
  with backend.app.test_request_context('/'):
   backend.session.update(role='lecturer',email='staff@example.com')
   with patch.object(backend,'query',side_effect=[course,None]) as query:
    from werkzeug.exceptions import Forbidden
    with self.assertRaises(Forbidden):backend.course_access('ICT 1305~26/27')
    self.assertEqual(query.call_args.args[1],('staff@example.com','ICT 1305','26/27')*2)
 def test_roster_uses_exact_module_enrolment(self):
  with patch.object(backend,'query',return_value=[]) as query:
   backend.roster({'course_code':'ICT 1305','academic_year':'26/27'})
   self.assertIn('student_course',query.call_args.args[0])
   self.assertEqual(query.call_args.args[1],('ICT 1305','26/27'))
 def test_account_file_hashes_nic(self):
  from werkzeug.datastructures import FileStorage
  from werkzeug.security import check_password_hash
  from io import BytesIO
  file=FileStorage(stream=BytesIO(b'Reg_no,Email,NIC\nICT/2024/001,student@example.com,200012345678\n'),filename='accounts.csv')
  rows=backend.account_details(file)
  self.assertNotIn('nic',rows['ICT/2024/001'])
  self.assertTrue(check_password_hash(rows['ICT/2024/001']['password_hash'],'200012345678'))
 def test_actual_workbook_format(self):
  from werkzeug.datastructures import FileStorage
  from pathlib import Path
  paths=list((Path(__file__).resolve().parents[1]/'upload').glob('COMMON*23(1).xlsx'))
  if not paths:self.skipTest('Original workbook is not included in the distributable.')
  with paths[0].open('rb') as stream:
   modules=backend.workbook_rows(FileStorage(stream=stream,filename='attendance.xlsx'))
  self.assertEqual(len(modules),45)
  self.assertEqual(modules[0]['code'],'ICT 1305')
  self.assertEqual(modules[1]['code'],'ICT 1305(P)')
  self.assertGreater(len(modules[0]['students']),0)
  recovered=[r for m in modules if m['code']=='ICT 1407' for r in m['students'] if r['reg']=='ICT/2024/123']
  self.assertTrue(recovered);self.assertTrue(recovered[0]['name'])
 def test_import_requires_missing_account_details(self):
  import tempfile,json
  from pathlib import Path
  self.login_session('hod')
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'.imports').mkdir();(root/'.imports'/'token').write_text(json.dumps({'rows':[{'reg':'R1','email':''}],'semester':['26/27',1,1]}))
   with self.client.session_transaction() as state:state['import_token']='token'
   with patch.object(backend,'ROOT',root),patch.object(backend,'query',return_value={'email':'staff@example.com'}),patch.object(backend,'execute') as execute:
    self.assertEqual(self.post('/api/import-confirm',{}).status_code,400);execute.assert_not_called()
 def test_reimport_preserves_password_and_saves_module_links(self):
  import tempfile,json
  from pathlib import Path
  self.login_session('hod')
  payload={'rows':[{'reg':'R1','email':'student@example.com','name':'Student','password_hash':'unused','modules':['ICT 1305']}],'semester':['26/27',1,1],'modules':[{'code':'ICT 1305','study':1}]}
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'.imports').mkdir();(root/'.imports'/'token').write_text(json.dumps(payload))
   with self.client.session_transaction() as state:state['import_token']='token'
   with patch.object(backend,'ROOT',root),patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},[{'email':'student@example.com','reg_number':'R1'}]]),patch.object(backend,'ensure_course'),patch.object(backend,'execute') as execute,patch.object(backend,'db'):
    self.assertEqual(self.post('/api/import-confirm',{}).status_code,200)
    self.assertEqual(len(execute.call_args_list),2)
    self.assertIn('student_course',execute.call_args_list[-1].args[0])
    self.assertEqual(execute.call_args_list[-1].args[1],('student@example.com','ICT 1305','26/27'))
    self.assertFalse((root/'.imports'/'token').exists())
 def test_attendance_query_filters_module(self):
  self.login_session()
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},[],{}]) as query,patch.object(backend,'selected_session',return_value=({'course_code':'ICT 1305'},'2026-10-12',1)),patch.object(backend,'roster',return_value=[]):
   self.assertEqual(self.client.get('/api/attendance').status_code,200)
   self.assertEqual(query.call_args_list[1].args[1],('ICT 1305','2026-10-12',1))

class ImportGroupingTests(BackendTests):
 def test_programme_labels(self):
  for reg in ['ASP/2024/001','ASB/2023/002','rjt/asp/2022/003']:
   self.assertEqual(backend.student_programme(reg),'Computer Science')
  self.assertEqual(backend.student_programme('ICT/2024/001'),'ICT')
 def test_students_list_hod_only(self):
  for role in ['student','lecturer','ar']:
   self.login_session(role)
   self.assertEqual(self.client.get('/api/students').status_code,403)
 def test_modules_only_preserves_preview_without_creating_accounts(self):
  import tempfile,json
  from pathlib import Path
  self.login_session('hod')
  payload={'rows':[{'reg':'ASP/2024/001','email':''}], 'semester':['26/27',1,1], 'modules':[{'code':'COM 1301','study':1},{'code':'ICT 2301','study':2}]}
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'.imports').mkdir();stage=root/'.imports'/'token';stage.write_text(json.dumps(payload))
   with self.client.session_transaction() as state:state['import_token']='token'
   with patch.object(backend,'ROOT',root),patch.object(backend,'query',return_value={'email':'staff@example.com'}),patch.object(backend,'ensure_course') as ensure,patch.object(backend,'execute') as execute,patch.object(backend,'db') as db:
    response=self.post('/api/import-modules',{})
    self.assertEqual(response.status_code,200);self.assertEqual(response.json['count'],2)
    ensure.assert_any_call('ICT 2301',('26/27',2,1));execute.assert_not_called();db.return_value.commit.assert_called_once()
    self.assertTrue(stage.exists())
 def test_preview_groups_multiple_module_years(self):
  import tempfile,io
  from pathlib import Path
  self.login_session('hod')
  modules=[{'code':'COM 1301','study':1,'sheet':'COM1301','students':[{'reg':'ASP/2024/001','name':'Student'}]}, {'code':'COM 2301','study':2,'sheet':'COM2301','students':[{'reg':'ASP/2024/001','name':'Student'}]}]
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(backend,'ROOT',Path(folder)),patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},None]),patch.object(backend,'workbook_rows',return_value=modules):
    result=self.client.post('/api/import-preview',data={'semester':'26/27|1|1','file':(io.BytesIO(b'x'),'test.xlsx')},headers={'X-CSRF-Token':'test-token'})
    self.assertEqual(result.status_code,200);self.assertEqual(result.json['missing'],1)
    self.assertEqual(result.json['rows'][0]['study_year'],2)
    self.assertEqual(result.json['rows'][0]['programme'],'Computer Science')
 def test_duplicate_account_email_rejected(self):
  from werkzeug.datastructures import FileStorage
  from werkzeug.exceptions import BadRequest
  import io
  file=FileStorage(stream=io.BytesIO(b'Reg_no,Email,NIC\nASP/1,s@example.com,200012345678\nASB/2,s@example.com,200012345679\n'),filename='accounts.csv')
  with self.assertRaises(BadRequest):backend.account_details(file)

if __name__=='__main__':unittest.main()

