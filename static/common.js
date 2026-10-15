async function api(url,body){
 const options=body===undefined?{}:{method:'POST',headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content}};
 if(body instanceof FormData)options.body=body;
 else if(body!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
 const response=await fetch(url,options);const result=await response.json();if(!response.ok)throw new Error(result.error||'Request failed');return result;
}
function fillSelect(id,rows,value,label,placeholder){const el=document.getElementById(id);el.replaceChildren(new Option(placeholder||'Select', ''));rows.forEach(r=>el.add(new Option(label(r),value(r))));}
function tableRows(body,rows,columns){body.replaceChildren();rows.forEach(r=>{const tr=document.createElement('tr');columns.forEach(fn=>{const td=document.createElement('td');td.textContent=fn(r);tr.append(td);});body.append(tr);});if(!rows.length){const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=columns.length;td.className='empty';td.textContent='No records to display.';tr.append(td);body.append(tr);}}
function percentage(r){return r.total?(100*r.present/r.total).toFixed(1)+'%':'—';}
document.querySelectorAll('a[href="UI.html"]').forEach(link=>{if(document.body.dataset.role) {link.textContent='Sign Out';link.addEventListener('click',async e=>{e.preventDefault();try{await api('/api/logout',{});location.href='/UI.html';}catch(err){alert(err.message);}});}});
