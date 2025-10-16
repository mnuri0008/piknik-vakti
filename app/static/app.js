
const $ = (q, el=document)=>el.querySelector(q);
const $$= (q, el=document)=>Array.from(el.querySelectorAll(q));

let FILTER = 'all';
let nickname = '';

const socket = io({ transports: ['websocket'] });

socket.on('hello', ()=>{});
socket.on('presence', (p)=>{ console.log('presence', p); });
socket.on('state', (state)=>{ render(state); });

function fmtAmount(a,u){ if(u==='adet') return `${a} ${u}`; return `${a} ${u}`; }

function render(state){
  // users
  $('#users').textContent = `👥 ${state.users.length}/10`;
  // categories dropdown
  const catSel = $('#category');
  catSel.innerHTML = '';
  (state.categories||[]).forEach(c=>{
    const opt=document.createElement('option'); opt.value=c; opt.textContent=c; catSel.appendChild(opt);
  });
  // items
  const ul = $('#list'); ul.innerHTML='';
  (state.items||[]).filter(it=>{
    if(FILTER==='all') return true;
    if(['needed','claimed','brought'].includes(FILTER)) return it.status===FILTER;
    // category filter
    return it.category===FILTER;
  }).forEach(it=>{
    const li = document.createElement('li'); li.className='item';
    const badge = it.status==='brought'?'<span class="badge ok">Getirildi</span>':it.status==='claimed'?'<span class="badge warn">Ayrılan</span>':'<span class="badge need">Eksik</span>';
    li.innerHTML = `
      <div class="left">
        <span class="title">${it.title} — <span class="meta">${fmtAmount(it.amount, it.unit)} • ${it.category}</span></span>
        <span class="meta">${it.who?('@'+it.who):''}</span>
      </div>
      <div class="right">
        ${badge}
        <button class="del">Sil</button>
      </div>`;
    li.addEventListener('click', async e=>{
      if(!nickname) return;
      if(e.detail===1){ setTimeout(async ()=>{ if(e.detail===1){ await fetch('/api/items/'+it.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'claimed', who:nickname})}); } }, 160); }
      if(e.detail===2){ await fetch('/api/items/'+it.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'brought', who:nickname})}); }
    });
    li.querySelector('.del').addEventListener('click', async e=>{
      e.stopPropagation();
      await fetch('/api/items/'+it.id,{method:'DELETE'});
    });
    ul.appendChild(li);
  });

  // activate filter state
  $$('.chip').forEach(x=>x.classList.remove('active'));
  const btn = $$('.chip').find(x=>x.dataset.f===FILTER); if(btn) btn.classList.add('active');
}

document.addEventListener('DOMContentLoaded', async ()=>{
  // join
  $('#joinBtn').addEventListener('click', async ()=>{
    const name = $('#nick').value.trim();
    if(!name) return;
    const r = await fetch('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    const j = await r.json();
    if(!r.ok){ alert(j.error || 'katılım hatası'); return; }
    nickname = name;
    socket.emit('join', {name});
  });

  // add item
  $('#addBtn').addEventListener('click', async ()=>{
    if(!nickname){ alert('Önce bir takma ad ile katıl.'); return; }
    const title = $('#title').value.trim();
    const category = $('#category').value;
    const amount = parseFloat($('#amount').value||'0');
    const unit = $('#unit').value;
    if(!title) return;
    await fetch('/api/items', {method:'POST',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({title, category, amount, unit, who:nickname})});
    $('#title').value=''; $('#amount').value='';
  });

  // filters
  $$('.chip').forEach(c=>c.addEventListener('click', ()=>{
    FILTER = c.dataset.f; render(window.__STATE||{items:[]});
  }));

  // initial data
  const cs = await (await fetch('/api/categories')).json();
  const catSel = $('#category'); catSel.innerHTML='';
  (cs.categories||[]).forEach(c=>{ const o=document.createElement('option'); o.value=c; o.textContent=c; catSel.appendChild(o); });

  const items = await (await fetch('/api/items')).json();
  window.__STATE = {items:items.items||[], categories:cs.categories||[], users:[]};
});
