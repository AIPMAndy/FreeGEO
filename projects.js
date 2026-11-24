/* Versioned local project library; atomic snapshots; no destructive project switching. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./workflow'):root.Workflow);if(typeof module==='object'&&module.exports)module.exports=api;else root.Projects=api;})(globalThis,W=>{
'use strict';const key='freegeo-project-library-v1',legacy='freegeo-workspace-v1',LIMIT=4*1024*1024;
function validate(lib){if(!lib||lib.version!==1||!Array.isArray(lib.projects)||lib.projects.length<1||lib.projects.length>30)throw Error('项目库格式错误或超出30项目上限');const ids=new Set();for(const p of lib.projects){if(!p||typeof p.id!=='string'||!p.id||p.id.length>120||ids.has(p.id))throw Error('项目 ID 无效或重复');ids.add(p.id);const err=W.validate(p.data);if(err.length)throw Error(err.slice(0,8).join('\n'));}if(!ids.has(lib.active))throw Error('活跃项目不存在');return lib;}
function initial(d){const id=W.uid();return {version:1,active:id,projects:[{id,data:W.upgrade(d)}]};}
function read(storage,blank){let raw=null,source=key;try{raw=storage.getItem(key);if(raw!==null)return{lib:validate(JSON.parse(raw)),raw:null,error:''};source=legacy;raw=storage.getItem(legacy);return{lib:initial(raw!==null?JSON.parse(raw):blank),raw:null,error:''};}catch(e){return{lib:initial(blank),raw,error:`项目库无法读取（${source}）：${e.message}。请先下载原始备份。`};}}
function write(storage,lib){validate(lib);const text=JSON.stringify(lib);if(text.length>LIMIT)throw Error('项目库超出4MB上限，请导出备份；当前数据仍在内存');storage.setItem(key,text);return true;}
function active(lib){return lib.projects.find(p=>p.id===lib.active).data;}
function update(lib,d){return validate({...lib,projects:lib.projects.map(p=>p.id===lib.active?{...p,data:d}:p)});}
function add(lib,d){const id=W.uid();return validate({...lib,active:id,projects:[...lib.projects,{id,data:W.upgrade(d)}]});}
function select(lib,id){return validate({...lib,active:id});}
return {key,legacy,validate,read,write,active,update,add,select,initial};});
