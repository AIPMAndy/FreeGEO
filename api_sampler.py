#!/usr/bin/env python3
"""FreeGEO optional official OpenAI Responses API sampling. Default dry run, never auto-spend."""
import argparse,csv,datetime,io,json,os,re,sys,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit
ENDPOINT='https://api.openai.com/v1/responses'
FIELDS=['prompt','attempt','id','qid','engine','surface','region','language','date','batch','status','search','mention','recommend','citation','sources','evidence']
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def load_csv(path):
    p=Path(path)
    if p.stat().st_size>10*1024*1024:raise ValueError('Input CSV exceeds 10MB')
    with p.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or not set(FIELDS).issubset(reader.fieldnames):raise ValueError('Use the complete FreeGEO CSV template')
        rows=list(reader)
    if not rows or len(rows)>5000:raise ValueError('Expected 1–5000 rows')
    ids=set()
    for r in rows:
        if None in r or any(r.get(k) is None for k in FIELDS):raise ValueError('Malformed CSV row')
        if not r['id'] or r['id'] in ids or not r['prompt'].strip() or len(r['prompt'])>12000:raise ValueError('Invalid/duplicate ID or prompt')
        ids.add(r['id'])
        if r['status'] or r['date'] or r['evidence']:raise ValueError('Use an unfilled sampling template, not prior observations')
        if not all(r[k].strip() for k in ('qid','engine','surface','region','language','batch')):raise ValueError('Missing sampling conditions')
    return rows

def select_rows(rows,model,limit):
    expected='OpenAI:'+model+':web_search'
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,100}',model):raise ValueError('Invalid model name')
    if not 1<=limit<=50:raise ValueError('Request limit must be 1–50')
    selected=[r for r in rows if r['surface']=='API' and r['engine']==expected]
    if not selected:raise ValueError('No matching rows; use engine '+expected+' and surface API in FreeGEO')
    for r in selected:
        if not re.fullmatch(r'[A-Z]{2}',r['region']):raise ValueError('Region must be ISO two-letter country code')
        if not re.fullmatch(r'[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{2,8})*',r['language']):raise ValueError('Language must be a BCP-47 style tag')
    return selected[:limit]

def request_body(r,model,tokens):
    # Conditions are explicit and unchanged between batches. Do not send private project facts or brand labels.
    return {'model':model,'input':r['prompt'],'instructions':'Respond in '+r['language']+'. Answer the question naturally. Cite sources used.','tools':[{'type':'web_search','user_location':{'type':'approximate','country':r['region']},'search_context_size':'medium'}],'tool_choice':'required','max_output_tokens':tokens,'store':False}

def safe_url(u):
    try:
        x=urlsplit(u);return x.scheme in ('https','http') and bool(x.hostname) and not x.username and not x.password and not any(c.isspace() for c in u)
    except (ValueError,TypeError,AttributeError):return False

def parse_response(resp,row):
    r={k:row.get(k,'') for k in FIELDS};r.update(date=datetime.date.today().isoformat(),status='失败',search='未知',mention='未知',recommend='未知',citation='未知',sources='',evidence='')
    if not isinstance(resp,dict):r['evidence']='API response format invalid';return r
    items=resp.get('output') or [];parts=[];urls=[];searched=False
    for item in items:
        if not isinstance(item,dict):continue
        if item.get('type')=='web_search_call' and item.get('status')=='completed':searched=True
        if item.get('type')!='message' or item.get('role')!='assistant':continue
        for content in item.get('content') or []:
            if not isinstance(content,dict) or content.get('type')!='output_text':continue
            if isinstance(content.get('text'),str):parts.append(content['text'])
            for ann in content.get('annotations') or []:
                if isinstance(ann,dict) and ann.get('type')=='url_citation' and safe_url(ann.get('url')):urls.append(ann['url'])
    text='\n'.join(parts).strip();sources='\n'.join(dict.fromkeys(urls))
    if resp.get('status')!='completed' or not text or not searched or len(text)>17000 or len(sources)>19000:
        r['evidence']='API未完成、无实际搜索/回答或记录超限；不得计入有效样本。原始响应见 JSONL。';return r
    r.update(status='成功',search='是',sources=sources,evidence='API response ID: '+str(resp.get('id',''))[:150]+'\nModel: '+str(resp.get('model',''))[:150]+'\n请人工核验提及、推荐、引用（未知不等于否）。\n'+text)
    return r

def neutral(s):
    s=str(s or '')
    return "'"+s if re.match(r'^[\s\ufeff]*[=+\-@]|^[\t\r\n]',s) else s

def call(body,key):
    opener=urllib.request.build_opener(NoRedirect())
    req=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    with opener.open(req,timeout=90) as response:
        b=response.read(4*1024*1024+1)
        if len(b)>4*1024*1024:raise ValueError('API response exceeds limit')
        return json.loads(b)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('template');p.add_argument('--model',required=True);p.add_argument('--max-requests',type=int,default=3);p.add_argument('--max-output-tokens',type=int,default=2048);p.add_argument('--execute',action='store_true');p.add_argument('--accept-cost',action='store_true');p.add_argument('--output');a=p.parse_args(argv)
    if not 256<=a.max_output_tokens<=4096:raise ValueError('Output token limit must be 256–4096')
    rows=select_rows(load_csv(a.template),a.model,a.max_requests)
    print(json.dumps({'mode':'execute' if a.execute else 'dry-run','endpoint':ENDPOINT,'requests':len(rows),'max_output_tokens_per_request':a.max_output_tokens,'warning':'Web search and input/output tokens may incur provider charges. Request cap is not a dollar cap. API results differ from ChatGPT Web. Only prompt and sampling conditions are sent.'},ensure_ascii=False),file=sys.stderr)
    if not a.execute:return 0
    if not a.accept_cost or not a.output:raise ValueError('Execution requires --accept-cost and --output; review cost and remove private data before running')
    key=os.environ.get('OPENAI_API_KEY')
    if not key:raise ValueError('Set OPENAI_API_KEY in local environment (never paste into FreeGEO website)')
    out=Path(a.output);raw=out.with_suffix(out.suffix+'.raw.jsonl')
    if out.exists() or raw.exists():raise ValueError('Output already exists; choose a new output path to avoid overwrite')
    with out.open('x',encoding='utf-8-sig',newline='') as f,raw.open('x',encoding='utf-8') as rf:
        writer=csv.DictWriter(f,FIELDS);writer.writeheader();f.flush()
        for row in rows:
            stop=False
            try:resp=call(request_body(row,a.model,a.max_output_tokens),key);result=parse_response(resp,row);entry={'id':row['id'],'response':resp}
            except urllib.error.HTTPError as e:
                entry={'id':row['id'],'error':'HTTP '+str(e.code)};result=parse_response(None,row);result['evidence']='API HTTP '+str(e.code)+'; 未自动重试';stop=True
            except (OSError,ValueError,urllib.error.URLError) as e:
                entry={'id':row['id'],'error':type(e).__name__};result=parse_response(None,row);result['evidence']='API请求失败（'+type(e).__name__+'），未自动重试；可能已产生费用';stop=True
            rf.write(json.dumps(entry,ensure_ascii=False)+'\n');rf.flush();writer.writerow({k:neutral(result[k]) for k in FIELDS});f.flush()
            if stop:print('Stopped after error; prior results preserved; remaining slots not executed.',file=sys.stderr);break
    print('Saved '+str(out)+' and '+str(raw)+'. Review labels before import.',file=sys.stderr);return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,csv.Error) as e:print(str(e),file=sys.stderr);sys.exit(1)
