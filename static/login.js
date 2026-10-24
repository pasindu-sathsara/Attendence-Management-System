const portal=document.body.dataset.portal;
$('login-form').onsubmit=async e=>{e.preventDefault();$('sign-in').disabled=true;try{const r=await api('/api/login',{...formObject(e.target),portal});location.href=r.next;}catch(err){message('login-message',err.message,true);$('sign-in').disabled=false;}};
