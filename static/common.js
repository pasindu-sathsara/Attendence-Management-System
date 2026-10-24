const $=id=>document.getElementById(id);
async function api(url,body){
 const options=body===undefined?{}:{method:'POST',headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content}};
 if(body instanceof FormData)options.body=body;
 else if(body!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
 const response=await fetch(url,options);
 let result;try{result=await response.json();}catch(error){throw new Error('Unable to load data. Check the server and sign in again.');}
 if(!response.ok)throw new Error(result.error||'Request failed');return result;
}
function fillSelect(id,rows,value,label,placeholder='Select'){const el=$(id);el.replaceChildren(new Option(placeholder,''));rows.forEach(r=>el.add(new Option(label(r),value(r))));}
function tableRows(body,rows,columns){body.replaceChildren();rows.forEach(r=>{const tr=document.createElement('tr');columns.forEach(fn=>{const td=document.createElement('td');const value=fn(r);if(value instanceof Node)td.append(value);else td.textContent=value??'—';tr.append(td);});body.append(tr);});if(!rows.length){const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=columns.length;td.className='empty';td.textContent='No records to display.';tr.append(td);body.append(tr);}}
function message(id,text,error=false){$(id).textContent=text;$(id).classList.toggle('error',error);}
function formObject(form){return Object.fromEntries(new FormData(form));}
function percentage(row){return row.percentage==null?'—':Number(row.percentage).toFixed(2)+'%';}
function pager(id,result,load){const el=$(id);el.replaceChildren();const span=document.createElement('span');span.textContent=`${result.total} records · Page ${result.page} of ${result.pages}`;el.append(span);for(const [label,offset] of [['Previous',-1],['Next',1]]){const b=document.createElement('button');b.className='secondary';b.textContent=label;b.disabled=offset<0?result.page<=1:result.page>=result.pages;b.onclick=()=>load(result.page+offset);el.append(b);}}
function debounce(fn){let timer;return (...args)=>{clearTimeout(timer);timer=setTimeout(()=>fn(...args),250);};}
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
if($('logout'))$('logout').onclick=async()=>{try{const role=document.body.dataset.role;await api('/api/logout',{});location.href=role==='student'?'/UI.html':'/staff-login.html';}catch(e){alert(e.message);}};

document.querySelectorAll('[data-eye]').forEach(button=>button.onclick=()=>{const input=$(button.dataset.eye);input.type=input.type==='password'?'text':'password';button.setAttribute('aria-label',input.type==='password'?'Show password':'Hide password');button.setAttribute('aria-pressed',input.type==='text');});
function moduleLabel(code){return /\([TP]\)$/.test(code)?code:code+'(T)';}

function submissionType(kind){return {normal:'Medical (MC)',special:'Special Medical (SMC)',excuse:'Excuse Letter'}[kind] || 'Document';}
