#!/usr/bin/env python3
"""FreeGEO site doctor. Local evidence by default; explicit public URL fetch only.
MIT. This is a technical preflight, not an indexing/ranking verdict.
"""
import argparse, http.client, ipaddress, json, re, socket, ssl, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
MAX_BYTES=2_000_000
AGENTS=('Googlebot','bingbot','OAI-SearchBot','GPTBot')

class HTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.title=[];self.h1=[];self.metas=[];self.canonical=[];self.lang='';self.text=[];self.jsonld=[];self.stack=[];self.hidden=0;self.head=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang','') or ''
        if tag=='meta': self.metas.append((str(a.get('name') or '').lower(),str(a.get('content') or '')))
        if tag=='link' and 'canonical' in str(a.get('rel') or '').lower().split(): self.canonical.append(str(a.get('href') or ''))
        if tag=='script' and str(a.get('type') or '').lower()=='application/ld+json':self.jsonld.append('')
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}: self.stack.append((tag,tag in {'script','style','template','noscript','head'} or 'hidden' in a, tag=='script' and str(a.get('type') or '').lower()=='application/ld+json'))
        if tag=='h1':self.h1.append('')
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):
        tags=[x[0] for x in self.stack]
        if 'title' in tags:self.title.append(data)
        if 'h1' in tags and self.h1:self.h1[-1]+=data
        if self.stack and self.stack[-1][2]:self.jsonld[-1]+=data
        if not any(x[1] for x in self.stack):self.text.append(data)

# Robots matching: longest matching path, allow wins ties, case-sensitive paths.
# Treat malformed directives conservatively; does not emulate proprietary crawler extensions.
def robots_policy(text,agent,path):
    groups=[]; agents=[]; rules=[];seen_rule=False
    def flush():
        if agents:groups.append((agents[:],rules[:]))
    for raw in text.splitlines():
        line=raw.split('#',1)[0].strip()
        if ':' not in line:continue
        k,v=(x.strip() for x in line.split(':',1));k=k.lower()
        if k=='user-agent':
            if seen_rule:flush();agents=[];rules=[];seen_rule=False
            if v:agents.append(v.lower())
        elif k in ('allow','disallow') and agents:
            seen_rule=True
            if v and v.startswith('/'):rules.append((k,v))
    flush();matches=[]
    a=agent.lower();specific=[(aa,rr) for aa,rr in groups if a in aa];selected=specific or [(aa,rr) for aa,rr in groups if '*' in aa]
    for _,rr in selected:
        for k,v in rr:
            # Limit complexity; ambiguous encoding is explicitly reported rather than inferred.
            if len(v)>500 or v.count('*')>12:continue
            end=v.endswith('$');base=v[:-1] if end else v
            pattern=base if end else base+'*'
            # Bounded greedy wildcard matching; no regex backtracking.
            def match(pattern,text):
                i=j=0;star=-1;retry=0
                while i<len(text):
                    if j<len(pattern) and pattern[j]==text[i] and pattern[j]!='*':i+=1;j+=1
                    elif j<len(pattern) and pattern[j]=='*':star=j;retry=i;j+=1
                    elif star>=0:retry+=1;i=retry;j=star+1
                    else:return False
                return all(c=='*' for c in pattern[j:])
            if match(pattern,path):matches.append((len(base.replace('*','')),k=='allow',v))
    if not matches:return {'decision':'未发现匹配限制','rule':None}
    _,allowed,rule=max(matches,key=lambda x:(x[0],x[1]));return {'decision':'Allow' if allowed else 'Disallow','rule':rule}

def audit(html,url='',status=None,headers=None,robots=None,robots_status=None):
    if len(html)>MAX_BYTES:raise ValueError('HTML 超过限制')
    parser=HTML();parser.feed(html);headers={k.lower():str(v) for k,v in (headers or {}).items()};items=[]
    def item(priority,code,observed,action,accept):items.append(dict(priority=priority,code=code,observed=observed,action=action,accept=accept))
    if status is None:item('待核验','http','未提供实际 HTTP 响应','运行显式 --live --url，或提供真实状态码与 HTTP 响应头。','最终公开页面 2xx；异常跳转与错误页已处理。')
    elif not 200<=status<300:item('P0','http',f'HTTP {status}','确认错误页、认证、重定向或服务器故障；如果页面应公开，修复正常响应。','实际最终 URL 返回预期的成功响应。')
    else:item('通过','http',f'HTTP {status}（本次请求）','保持公开页面正常服务；不同抓取端仍可能不同。','按需复测。')
    if not ''.join(parser.title).strip():item('P1','title','未找到非空 title','添加与页面真实任务匹配的唯一标题。','查看源代码确认非空、准确的 title。')
    desc=[v for k,v in parser.metas if k=='description' and v.strip()]
    if not desc:item('P2','description','未找到非空 description','添加真实、简洁的页面摘要；不要堆关键词。','摘要与页面能力一致。')
    if not any(x.strip() for x in parser.h1):item('P1','h1','未找到非空 H1','提供用户可读的主要标题。','主标题可见，能够说明页面目标。')
    robots_meta=[f'{k}: {v}' for k,v in parser.metas if k in ('robots','googlebot','bingbot','oai-searchbot')];xrobots=headers.get('x-robots-tag','');directive='; '.join(robots_meta+[xrobots])
    if re.search(r'\b(noindex|none)\b',directive,re.I):item('P0','noindex',directive,'确认是否有意限制索引；仅对希望公开搜索的页面移除对应限制，勿公开私密页。','对应 HTML/meta 和实际 HTTP 头不再误设禁止索引。')
    if len(parser.canonical)>1:item('P1','canonical','多个 canonical: '+str(parser.canonical),'保留一个真实的规范目标。','源代码中只有正确规范 URL。')
    elif parser.canonical and url:
        target=urljoin(url,parser.canonical[0]); u,t=urlsplit(url),urlsplit(target)
        if t.scheme not in ('http','https') or t.netloc!=u.netloc or t.path.rstrip('/')!=u.path.rstrip('/'):
            item('P1','canonical',target,'核对跨域或不同路径 canonical 是否有意；不要自动改掉正确的重复页关系。','确认实际索引目标，且该目标可访问。')
    elif not parser.canonical:item('P2','canonical','未声明','若存在重复 URL 或参数页，明确规范页；不是每个页面都必须设置。','重复页策略一致。')
    if not parser.lang:item('P2','lang','缺少 HTML lang','声明真实页面语言，改善可访问性。','html lang 与正文语言一致。')
    n=len(re.sub(r'\s+',' ',' '.join(parser.text)).strip())
    if n<100:item('P1','body',f'源代码正文近似 {n} 字符','检查是否只有 JS 空壳、加载错误或登录墙；对需公开内容提供可访问的主体文本。','真实访客和允许的抓取方式均能读取主要内容；不得用隐藏文本作弊。')
    for block in parser.jsonld:
        try:
            v=json.loads(block)
            if not isinstance(v,(dict,list)):raise ValueError('not object/array')
        except (ValueError,TypeError):item('P1','jsonld','存在无法解析的 JSON-LD','修复语法或移除无效标记；确保标记与可见真实内容一致。','所有 JSON-LD 块均可解析且按需通过官方验证器。')
    if robots is None:item('待核验','robots','未取得实际域名根 robots.txt','核对域名根路径 /robots.txt 和目标 URL 的抓取权限；训练与搜索是不同用途。','记录搜索爬虫规则和实际可抓取证据。')
    else:
        u=urlsplit(url); path=(u.path or '/')+('?' + u.query if u.query else '')
        if robots_status is not None and robots_status!=200:item('待核验','robots_status',f'robots.txt HTTP {robots_status}','核对状态码与各平台官方处理逻辑；不要假定允许或阻止。','取得根规则或确认平台处理行为。')
        else:
            for a in AGENTS:
                r=robots_policy(robots,a,path)
                if r['decision']=='Disallow':item('P1' if a!='GPTBot' else '信息','robots_'+a,f"{a}: {r['decision']} {r['rule']}",'确认是否有意限制该用途；GPTBot 是训练相关，不等于搜索索引。','业务与隐私策略一致，误阻的公开搜索页面已复核。')
                else:item('信息','robots_'+a,f"{a}: {r['decision']} {r['rule'] or ''}",'规则检查不保证真实抓取或索引。','使用平台官方站长数据核实。')
    if not any(x['priority'] in ('P0','P1') for x in items):item('信息','baseline','当前证据未发现列出的严重技术风险','继续检查真实用户问题、可引用事实和官方索引数据。','完成基线与复测；无风险不代表排名更高。')
    order={'P0':0,'P1':1,'P2':2,'待核验':3,'信息':4,'通过':5};items.sort(key=lambda x:order[x['priority']]);return {'url':url,'http_status':status,'title':''.join(parser.title).strip(),'body_chars_approx':n,'findings':items,'limitations':['静态 HTML 近似诊断，不执行 JavaScript、登录或 CAPTCHA','robots 只近似匹配常见规则；编码和平台细节须人工核实','HTTP 可访问、索引资格和 AI 引用不是同一件事','不会自动更改或发布网站']}

def public_ip(host,port):
    infos=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    ips=list(dict.fromkeys(x[4][0] for x in infos))
    if not ips or any(not ipaddress.ip_address(i).is_global or ipaddress.ip_address(i).is_multicast or ipaddress.ip_address(i).is_reserved for i in ips):raise ValueError('拒绝非公网、私有、保留或混合 DNS 地址')
    return ips[0]
class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self,host,port,ip):super().__init__(host,port,timeout=10);self.ip=ip
    def connect(self):self.sock=socket.create_connection((self.ip,self.port),self.timeout)
class PinnedHTTPS(PinnedHTTP):
    def connect(self):super().connect();self.sock=ssl.create_default_context().wrap_socket(self.sock,server_hostname=self.host)
def fetch(url,redirects=3):
    for _ in range(redirects+1):
        u=urlsplit(url)
        if len(url)>4096 or u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.port not in (None,80,443):raise ValueError('只允许显式公网 HTTP(S) URL / 80、443 端口，不允许凭证')
        port=u.port or (443 if u.scheme=='https' else 80);host=u.hostname.encode('idna').decode();ip=public_ip(host,port);conn=(PinnedHTTPS if u.scheme=='https' else PinnedHTTP)(host,port,ip)
        try:
            conn.request('GET',(u.path or '/')+('?' + u.query if u.query else ''),headers={'User-Agent':'FreeGEO-SiteDoctor/0.2 (user-initiated)','Accept-Encoding':'identity','Accept':'text/html,text/plain;q=0.9,*/*;q=0.1'});r=conn.getresponse();h={}
            for k,v in r.getheaders():h[k.lower()]=h.get(k.lower(),'')+(', ' if k.lower() in h else '')+v
            if r.status in (301,302,303,307,308) and h.get('location'):
                url=urljoin(url,h['location']);continue
            if h.get('content-encoding','identity').lower() not in ('','identity'):raise ValueError('服务器返回压缩内容；请保存解压后的 HTML 再运行离线诊断')
            b=r.read(MAX_BYTES+1)
            if len(b)>MAX_BYTES:raise ValueError('响应超过 2MB')
            m=re.search(r'charset\s*=\s*([\w-]+)',h.get('content-type',''),re.I);charset=m.group(1) if m else 'utf-8'
            try:body=b.decode(charset,'replace')
            except LookupError:body=b.decode('utf-8','replace')
            return url,r.status,h,body
        finally:conn.close()
    raise ValueError('重定向次数超过限制')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--file');p.add_argument('--url');p.add_argument('--robots-file');p.add_argument('--headers-json');p.add_argument('--status',type=int);p.add_argument('--live',action='store_true',help='明确授权访问指定公网页面及最终域名根 robots.txt（不模拟其他爬虫）');p.add_argument('--json',action='store_true');a=p.parse_args()
    if a.live:
        if not a.url or a.file:p.error('--live 需要 --url，不与 --file 同用')
        u,s,h,b=fetch(a.url);root=urlsplit(u);rstat=None;rtext=None
        try:_,rstat,_,rtext=fetch(f'{root.scheme}://{root.netloc}/robots.txt')
        except (ValueError,OSError,http.client.HTTPException):pass
        result=audit(b,u,s,h,rtext,rstat)
    else:
        if not a.file:p.error('离线模式需 --file；在线检查需显式 --live --url')
        def read(path):
            with open(path,'rb') as f:b=f.read(MAX_BYTES+1)
            if len(b)>MAX_BYTES:raise ValueError('证据文件过大')
            return b.decode('utf-8-sig','replace')
        result=audit(read(a.file),a.url or '',a.status,json.loads(read(a.headers_json)) if a.headers_json else None,read(a.robots_file) if a.robots_file else None)
    if a.json:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(f"# FreeGEO 网站技术修复单\n\n目标：{result['url'] or '本地 HTML'}\n")
        for x in result['findings']:print(f"## {x['priority']} · {x['code']}\n- 证据：{x['observed']}\n- 修复：{x['action']}\n- 验收：{x['accept']}\n")
        print('## 边界\n'+'\n'.join('- '+x for x in result['limitations']))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,http.client.HTTPException,TypeError) as e:print('检查失败：'+str(e),file=sys.stderr);sys.exit(1)
