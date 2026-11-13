'use strict';
const palette=['#164d75','#d17a26','#298376','#9467bd','#c34e5a','#6493aa','#97633b','#769435','#b25592','#5470bf','#ba9c27','#40899a','#9b8cbe','#956d77','#6a8970','#576878','#b8a26c'];
const money=new Intl.NumberFormat('es-CL',{maximumFractionDigits:0});
let current=null;
function legend(id,labels,colors){const root=document.getElementById(id);root.replaceChildren();labels.forEach((text,i)=>{const item=document.createElement('span'),swatch=document.createElement('i');swatch.className='swatch';swatch.style.background=colors[i%colors.length];item.append(swatch,document.createTextNode(text));root.append(item);});}
function plot(canvas,series,stacked){
 const width=Math.max(canvas.clientWidth,260),height=330,dpr=window.devicePixelRatio||1;canvas.width=width*dpr;canvas.height=height*dpr;
 const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);const left=85,right=20,top=20,bottom=45,w=width-left-right,h=height-top-bottom;
 const n=series[0].values.length,raw=series.flatMap(s=>s.values),min=stacked?0:Math.min(...raw)*.97,max=stacked?1:Math.max(...raw)*1.03;
 const x=i=>left+(n===1?w/2:i/(n-1)*w),y=v=>top+h-(v-min)/(max-min||1)*h;
 ctx.font='11px system-ui';ctx.fillStyle='#546779';
 for(let i=0;i<=4;i++){const value=min+(max-min)*i/4;ctx.strokeStyle='#e2e7ed';ctx.beginPath();ctx.moveTo(left,y(value));ctx.lineTo(width-right,y(value));ctx.stroke();ctx.fillText(stacked?`${Math.round(value*100)} %`:money.format(value/1000000)+' M',5,y(value)+4);}
 const baseline=Array(n).fill(0);
 series.forEach((s,k)=>{ctx.beginPath();if(stacked){const upper=s.values.map((v,i)=>baseline[i]+v);upper.forEach((v,i)=>i?ctx.lineTo(x(i),y(v)):ctx.moveTo(x(i),y(v)));for(let i=n-1;i>=0;i--)ctx.lineTo(x(i),y(baseline[i]));ctx.closePath();ctx.fillStyle=palette[k%palette.length];if(n===1){ctx.fillRect(left,y(upper[0]),w,y(baseline[0])-y(upper[0]));}else{ctx.fill();}upper.forEach((v,i)=>baseline[i]=v);}else{s.values.forEach((v,i)=>i?ctx.lineTo(x(i),y(v)):ctx.moveTo(x(i),y(v)));ctx.strokeStyle=palette[k];ctx.lineWidth=2.5;ctx.stroke();if(n===1){ctx.beginPath();ctx.arc(x(0),y(s.values[0]),4,0,Math.PI*2);ctx.fillStyle=palette[k];ctx.fill();}}});
 ctx.fillStyle='#546779';ctx.fillText(series[0].dates[0],left,height-15);const last=series[0].dates[n-1];ctx.fillText(last,width-right-ctx.measureText(last).width,height-15);
}
function render(data){
 const summaries=document.getElementById('summaries'),weights=document.getElementById('weights');summaries.replaceChildren();weights.replaceChildren();
 const nonempty=data.portfolios.filter(p=>p.points.length);document.getElementById('values').hidden=!nonempty.length;
 if(!nonempty.length){document.getElementById('value-legend').replaceChildren();return;}
 plot(document.getElementById('values'),nonempty.map(p=>({values:p.points.map(v=>Number(v.value)),dates:p.points.map(v=>v.date)})),false);
 legend('value-legend',nonempty.map(p=>p.name),palette);
 for(const p of nonempty){const box=document.createElement('div');box.className='metric';const title=document.createElement('span'),value=document.createElement('strong'),change=document.createElement('small');title.textContent=p.name+' · '+p.points.at(-1).date;value.textContent='USD '+money.format(Number(p.points.at(-1).value));change.textContent=((Number(p.points.at(-1).value)/Number(p.points[0].value)-1)*100).toFixed(2)+' % en el rango consultado';box.append(title,value,change);summaries.append(box);
 const section=document.createElement('section');section.className='card';const heading=document.createElement('h2');heading.textContent='Composición · '+p.name;const canvas=document.createElement('canvas');canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Áreas apiladas de los pesos de '+p.name);const key=document.createElement('div');key.className='legend';key.id='weights-legend-'+p.id;section.append(heading,canvas,key);weights.append(section);const names=Object.keys(p.points[0].weights);plot(canvas,names.map(name=>({values:p.points.map(v=>Number(v.weights[name])),dates:p.points.map(v=>v.date)})),true);legend(key.id,names,palette);
 }
}
async function load(event){if(event)event.preventDefault();const status=document.getElementById('status'),button=document.getElementById('submit');button.disabled=true;status.className='';status.textContent='Consultando API…';const params=new URLSearchParams({fecha_inicio:document.getElementById('start').value,fecha_fin:document.getElementById('end').value}),url='/api/evolution/?'+params;document.getElementById('api-link').href=url;
 try{const response=await fetch(url);const data=await response.json();if(!response.ok)throw Error(data.error||'Error al consultar la API');current=data;render(data);const count=data.portfolios[0]?.points.length||0;status.textContent=count?`${count} fechas · ${data.portfolios.length} portafolios · datos cargados desde la base de datos`:'No hay precios en el rango solicitado.';}catch(error){current=null;document.getElementById('summaries').replaceChildren();document.getElementById('weights').replaceChildren();document.getElementById('values').hidden=true;document.getElementById('value-legend').replaceChildren();status.className='error';status.textContent=error.message;}finally{button.disabled=false;}}
document.getElementById('filters').addEventListener('submit',load);window.addEventListener('resize',()=>{if(current)render(current);});load();

