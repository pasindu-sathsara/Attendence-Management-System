let options={courses:[]},report=null,reportQuery='',generation=0;
let selectedStudents=new Set();
const hod=['hod','ar'].includes(document.body.dataset.role);
function invalidate(){generation++;selectedStudents.clear();$('student-selection').hidden=true;$('download').disabled=true;$('view-report').disabled=true;$('report-results').hidden=true;reportQuery='';message('report-message','');}
function modules(){const old=$('report-course').value;const rows=options.courses.filter(c=>{const [year,study,semester]=c.semester.split('|');return year===$('report-year').value&&(!$('report-study').value||study===$('report-study').value)&&(!$('report-semester').value||semester===$('report-semester').value);});fillSelect('report-course',rows,r=>r.code,r=>r.label,hod?'All modules':'Select assigned module');if(rows.some(r=>r.code===old))$('report-course').value=old;invalidate();}
const columns={students:[['Reg No',r=>r.reg],['Name',r=>r.name],['Present',r=>r.present],['Absent',r=>r.absent],['Total Sessions',r=>r.total],['Attendance %',percentage],['Eligibility',r=>r.eligibility]],modules:[['Module',r=>moduleLabel(r.course_code)],['Study Year',r=>r.study_year],['Semester',r=>r.semester_number],['Students',r=>r.students],['Total Sessions',r=>r.total],['Present',r=>r.present],['Absent',r=>r.absent],['Average Attendance %',percentage]]};
columns.scholarship=[['Reg No',r=>r.reg],['Name',r=>r.name],['Batch',r=>r.batch],['Present',r=>r.present],['Absent',r=>r.absent],['MC',r=>r.medical],['Special Medical',r=>r.special],['Student Sessions',r=>r.total],['Attendance %',percentage],['Eligibility',r=>r.eligibility]];
function selectionCount(){
 $('selection-count').textContent=selectedStudents.size+' students selected';
 $('download-students').disabled=selectedStudents.size===0;
}
function selectStudent(row){
 const box=document.createElement('input');box.type='checkbox';box.checked=selectedStudents.has(row.reg);
 box.setAttribute('aria-label','Select '+row.reg);
 box.onchange=()=>{if(box.checked)selectedStudents.add(row.reg);else selectedStudents.delete(row.reg);selectionCount();};
 return box;
}
function showPage(page=1){const fields=report.kind==='scholarship'?[['Select',selectStudent],...columns.scholarship]:columns[report.kind];$('report-head').replaceChildren();fields.forEach(([name])=>{const th=document.createElement('th');th.textContent=name;$('report-head').append(th);});tableRows($('report-rows'),report.rows.slice((page-1)*10,page*10),fields.map(c=>c[1]));pager('report-pager',{total:report.rows.length,page,pages:Math.max(1,Math.ceil(report.rows.length/10))},showPage);}
for(const id of ['report-year','report-study','report-semester'])$(id).onchange=modules;for(const id of ['report-batch','report-course','report-start','report-end'])$(id).onchange=invalidate;
$('report-form').onsubmit=async e=>{e.preventDefault();invalidate();const id=generation;const query=new URLSearchParams(formObject(e.target)).toString();$('generate-report').disabled=true;try{const result=await api('/api/report?'+query);if(generation!==id)return;report=result;reportQuery=query;selectedStudents=new Set(report.kind==='scholarship'?report.rows.map(r=>r.reg):[]);$('student-selection').hidden=report.kind!=='scholarship';selectionCount();$('report-title').textContent=report.kind==='modules'?'Module Summary':report.kind==='scholarship'?'Mahapola / Bursary Attendance':'Student Attendance';$('report-description').textContent=[$('report-year').value,$('report-batch').value?'Batch '+$('report-batch').value:'All batches',$('report-course').selectedOptions[0].text].join(' · ');$('report-summary').textContent=report.kind==='modules'?`${report.rows.length} modules`:`${report.rows.length} students`;const missing=report.rows.reduce((n,r)=>n+Number(r.unmarked),0);if(missing)message('report-message',`${missing} student-session records are unmarked. Update attendance for these sessions before using the final report.`);$('report-results').hidden=false;$('download').disabled=false;$('view-report').disabled=false;showPage();}catch(err){message('report-message',err.message,true);}finally{$('generate-report').disabled=false;}};
$('download').onclick=async()=>{if(!reportQuery)return;$('download').disabled=true;try{const response=await fetch('/api/report.xlsx?'+reportQuery);if(!response.ok){const r=await response.json();throw new Error(r.error||'Export failed.');}const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='attendance-report.xlsx';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){message('report-message',e.message,true);}finally{$('download').disabled=!reportQuery;}};
(async()=>{try{options=await api('/api/options');const years=[...new Set(options.semesters.map(s=>s.id.split('|')[0]))].sort().reverse();fillSelect('report-year',years,r=>r,r=>r,'Select academic year');if(years.length)$('report-year').value=years[0];fillSelect('report-batch',options.batches,r=>r,r=>r,'All batches');modules();}catch(e){message('report-message',e.message,true);}})();

if($('report-type'))$('report-type').onchange=invalidate;if($('report-registration'))$('report-registration').oninput=invalidate;
let detailRows=[];
function detailPage(page=1){tableRows($('detail-rows'),detailRows.slice((page-1)*10,page*10),[r=>r.reg,r=>r.name,r=>moduleLabel(r.course_code),r=>r.present,r=>r.absent,r=>r.medical,r=>r.special,r=>r.total,percentage,r=>r.eligibility,r=>{const span=document.createElement('span');span.className='module-list';span.textContent=r.sessions||'No recorded sessions';return span;}]);pager('detail-pager',{total:detailRows.length,page,pages:Math.max(1,Math.ceil(detailRows.length/10))},detailPage);}
$('view-report').onclick=async()=>{try{const r=await api('/api/report-view?'+reportQuery);detailRows=r.rows;detailPage();$('report-dialog').showModal();}catch(e){message('report-message',e.message,true);}};

$('select-students').onclick=()=>{selectedStudents=new Set(report.rows.map(r=>r.reg));selectionCount();showPage();};
$('clear-students').onclick=()=>{selectedStudents.clear();selectionCount();showPage();};
$('download-students').onclick=async()=>{
 if(!reportQuery||!selectedStudents.size)return;
 const button=$('download-students');button.disabled=true;
 try{
  const response=await fetch('/api/student-reports.zip?'+reportQuery,{
   method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},
   body:JSON.stringify({registrations:[...selectedStudents]})
  });
  if(!response.ok){const result=await response.json();throw new Error(result.error||'Download failed.');}
  const url=URL.createObjectURL(await response.blob());
  const link=document.createElement('a');link.href=url;link.download='student-attendance-reports.zip';link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(error){message('report-message',error.message,true);}
 finally{button.disabled=!reportQuery||selectedStudents.size===0;}
};
