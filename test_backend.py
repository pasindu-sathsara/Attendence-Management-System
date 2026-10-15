import unittest
from unittest.mock import patch
import app as backend

class BackendTests(unittest.TestCase):
 def setUp(self):
  backend.app.config['TESTING']=True
  self.client=backend.app.test_client()
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
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},rows]),patch.object(backend,'selected_session',return_value=({},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]),patch.object(backend,'execute') as execute:
   self.assertEqual(self.post('/api/attendance',payload).status_code,400);execute.assert_not_called()
 def test_stale_update_rejected(self):
  payload,rows=self.attendance_request(original='present')
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},rows]),patch.object(backend,'selected_session',return_value=({},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]),patch.object(backend,'execute') as execute:
   self.assertEqual(self.post('/api/attendance',payload).status_code,409);execute.assert_not_called()
 def test_mc_saved_as_absent_reason(self):
  payload,rows=self.attendance_request()
  with patch.object(backend,'query',side_effect=[{'email':'staff@example.com'},rows]),patch.object(backend,'selected_session',return_value=({},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]),patch.object(backend,'execute') as execute,patch.object(backend,'db') as db:
   self.assertEqual(self.post('/api/attendance',payload).status_code,200)
   self.assertEqual(execute.call_args.args[1][:2],(0,'MC'));db.return_value.commit.assert_called_once()
 def test_incomplete_class_rejected(self):
  payload,rows=self.attendance_request();payload['statuses']={}
  with patch.object(backend,'query',return_value={'email':'staff@example.com'}),patch.object(backend,'selected_session',return_value=({},'2026-10-12',1)),patch.object(backend,'roster',return_value=[{'reg_number':'R1','email':'s@example.com'}]):
   self.assertEqual(self.post('/api/attendance',payload).status_code,400)

if __name__=='__main__':unittest.main()
