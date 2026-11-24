#!/usr/bin/env python3
"""Offline combined-access-log analysis. User-agent claims, not authenticated crawler identities."""
import argparse,json,re,sys
from collections import Counter
from urllib.parse import urlsplit
from pathlib import Path
# Never export client IP, referrer, raw UA, or query string. Common combined access log only.
PAT=re.compile(r'^\S+ \S+ \S+ \[([^\]]+)\] "([A-Z]+) ([^" ]+) HTTP/[^" ]+" (\d{3}) \S+ "[^"\n]*" "([^"\n]*)"\s*$')
BOTS={'OAI-SearchBot':'搜索相关声明','GPTBot':'训练相关声明','ChatGPT-User':'用户触发访问声明','Googlebot':'搜索相关声明','bingbot':'搜索相关声明','PerplexityBot':'搜索相关声明','ClaudeBot':'训练相关声明','Claude-SearchBot':'搜索相关声明','Claude-User':'用户触发访问声明'}
def summarize(lines):
 counts=Counter(); totals=Counter(); rejected=0; unclassified=0; scanned=0; matched=0
 for line in lines:
  scanned+=1
  if scanned>1000000:raise ValueError('Maximum 1 million lines')
  if len(line)>16384:rejected+=1;continue
  m=PAT.match(line.rstrip('\n\r'))
  if not m:rejected+=1;continue
  _,method,target,status,ua=m.groups()
  found=[b for b in BOTS if re.search(r'(?<![\w-])'+re.escape(b)+r'(?![\w-])',ua,re.I)]
  if not found:unclassified+=1;continue
  if len(found)!=1:rejected+=1;continue
  b=found[0];matched+=1;totals[(b,status)]+=1
  # Path may contain private identifiers; by default only aggregate status, no path output.
 return {'lines':scanned,'claimed_crawler_lines':matched,'other_lines':unclassified,'unparsed_or_ambiguous':rejected,'rows':[{'user_agent_claim':b,'purpose_hint':BOTS[b],'http_status':int(s),'requests':n} for (b,s),n in sorted(totals.items())],'limitations':['User-Agent can be spoofed; verify origin via platform-published IP/DNS methods before calling this genuine crawler traffic.','Request counts are not unique visits, index counts, answer citations, or recommendation rate.','Common combined log format only; malformed lines are counted separately. No IP, referrer, paths, query strings, or raw UA are exported.']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('log');a=p.parse_args();f=Path(a.log)
 if f.stat().st_size>100*1024*1024:raise ValueError('Maximum 100MB log size')
 with f.open(encoding='utf-8',errors='replace') as src:print(json.dumps(summarize(src),ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(1)
