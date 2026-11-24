"""In-memory DOM integration. No network/navigation and simulated localStorage.
Not a real-origin E2E or deployment test. Requires installed Playwright/Chromium.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os,re,json
root=Path(__file__).resolve().parents[1]
html=(root/'index.html').read_text()
html=re.sub(r'<link rel="stylesheet" href="style.css">',lambda _: '<style>'+(root/'style.css').read_text()+'</style>',html)
for name in ('core.js','growth.js','workflow.js','projects.js','app.js'):
 html=html.replace(f'<script src="{name}"></script>', '<script>'+(root/name).read_text().replace('</script','<\\/script')+'</script>')
mock="<script>const testStore=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>testStore.get(k)||null,setItem:(k,v)=>testStore.set(k,v)}});</script>"
html=html.replace('<body>','<body>'+mock,1)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM'),args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(4000);errors=[];requests=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept())
 page.set_content(html,wait_until='domcontentloaded',timeout=10000)
 assert '执行计划' in page.locator('#panel').inner_text()
 page.get_by_label('品牌 / 产品名称').fill('Test <script>bad</script>');page.get_by_label('自有 URL 范围',exact=False).fill('https://example.com/tool');page.get_by_label('真实产品能力 / 服务').fill('工具');page.get_by_label('目标客户').fill('测试者');page.get_by_role('button',name='保存业务资料并更新计划').click();assert '业务资料已保存' in page.locator('#notice').inner_text()
 page.get_by_role('tab',name='问题库').click();page.get_by_label('自然语言问题').fill('如何验证 GEO？');page.get_by_label('目标人群 / 场景').fill('测试者');page.get_by_label('需求验证').select_option('已验证');page.get_by_label('用户原话、来源或待验证假设').fill('测试用例，不是真实客户证据');page.get_by_role('button',name='添加记录').click();assert '如何验证 GEO' in page.locator('table').inner_text()
 page.get_by_role('tab',name='采样计划').click();assert '生成固定采样面板' in page.locator('#panel').inner_text()
 page.get_by_role('tab',name='答案观测').click();page.get_by_label('引擎 / 模型').fill('Manual');page.get_by_label('终端（Web / App / API）').fill('Web');page.get_by_label('地区').fill('CN');page.get_by_label('语言',exact=True).fill('zh-CN');page.get_by_label('批次（如 baseline）').fill('baseline');page.get_by_label('原始回答 / 核验记录（失败可写原因）').fill('测试记录');page.get_by_label('引用自有 URL').select_option('是');page.get_by_label('答案中实际引用链接，空格/换行分隔').fill('https://attacker.example/abc');page.get_by_role('button',name='添加记录').click();assert 'Manual' in page.locator('table').inner_text()
 page.get_by_role('tab',name='概览').click();assert '自有引用率' in page.locator('#panel').inner_text();assert '0/0 · 未知 1' in page.locator('#panel').inner_text()
 page.get_by_role('tab',name='引用分析').click();assert 'attacker.example' in page.locator('table').inner_text();assert '外部' in page.locator('table').inner_text()
 page.get_by_role('tab',name='页面体检').click();page.locator('#panel textarea').fill('<html><head><title>Sample</title><meta name="robots" content="noindex"></head><body><h1>Hello</h1><img src="https://example.invalid/pixel"><script>alert(1)</script></body></html>');page.get_by_role('button',name='运行本地检查').click();assert '发现 noindex' in page.locator('#panel').inner_text();assert not any('example.invalid' in r for r in requests)
 page.get_by_role('tab',name='固定采样实验').click();page.get_by_role('button',name='锁定问题并创建采样面板').click();assert '基线 0/3' in page.locator('#panel').inner_text()
 page.get_by_role('tab',name='机会与缺口').click();assert '竞品实际引用对比' in page.locator('#panel').inner_text();page.get_by_label('竞品名称').fill('Competitor');page.get_by_label('竞品网址范围').fill('https://attacker.example/');page.get_by_role('button',name='添加竞品').click();assert 'Competitor' in page.locator('#panel').inner_text()
 page.get_by_role('tab',name='开始 · 执行计划').click();page.get_by_role('button',name='加入修复台账').first.click();page.get_by_role('tab',name='修复与验收').click();assert '任务 1 · 已验收 0' in page.locator('#panel').inner_text();page.get_by_label('任务状态').select_option('已验收');page.get_by_role('button',name='保存任务进展').click();assert '验收证据无效' in page.locator('#notice').inner_text()
 page.get_by_label('执行凭证（差异、commit、记录等）').fill('test commit');page.get_by_label('复核凭证 / 不适用理由').fill('test verification');page.get_by_label('复核者').fill('test reviewer');page.get_by_label('复核日期').fill(page.evaluate('new Date().toISOString().slice(0,10)'));page.get_by_role('button',name='保存任务进展').click();assert '任务 1 · 已验收 1' in page.locator('#panel').inner_text()
 page.get_by_role('tab',name='页面体检').click();page.get_by_label('网页 HTML 源码').fill('<html><head><meta name="robots" content="noindex"></head><body>broken</body></html>');page.get_by_role('button',name='运行本地检查').click();page.get_by_role('button',name='保存诊断并生成修复任务').click();assert '已保存本地诊断' in page.locator('#notice').inner_text()
 page.get_by_role('tab',name='修复与验收').click();assert '技术体检 · noindex' in page.locator('#panel').inner_text()
 old=page.locator('#project-select').input_value();page.get_by_role('button',name='新建空白项目').click();assert page.locator('#project-select').locator('option').count()==2;page.locator('#project-select').select_option(old);page.get_by_role('tab',name='问题库').click();assert '如何验证 GEO' in page.locator('table').inner_text()
 page.get_by_role('button',name='打开示例').click();assert 'DEMO' in page.locator('#project-name').inner_text();assert '50.0%' in page.locator('#panel').inner_text();page.get_by_role('tab',name='实验台').click();assert '33.3 pp' in page.locator('#panel').inner_text()
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'mobile overflow'
 assert not errors,errors
 browser.close()
print('DOM fixture: onboarding, profile, question, sampling UI, observation, spoofed citation, source, HTML injection, demo, experiment, multi-project, fixed panel, competitor, acceptance gates, audit tasks, mobile — PASS (mock storage; no real-origin E2E)')
