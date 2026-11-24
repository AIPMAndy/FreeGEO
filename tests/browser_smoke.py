"""Optional local browser smoke test; requires Playwright and Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
root=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM'),args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
    page=context.new_page()
    errors=[]; requests=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.on('request',lambda req: requests.append(req.url))
    page.on('dialog',lambda dialog: dialog.accept())
    page.goto(base+'/index.html'); page.get_by_role('button',name='打开示例').click()
    assert 'DEMO' in page.locator('#project-name').inner_text()
    assert '50.0%' in page.locator('#panel').inner_text()
    page.get_by_role('tab',name='实验台').click(); assert '33.3 pp' in page.locator('#panel').inner_text()
    page.get_by_role('tab',name='页面体检').click()
    page.locator('#panel textarea').fill('<html><head><title>Sample</title><meta name="robots" content="noindex"><script type="application/ld+json">{"@type":"WebPage"}</script></head><body><h1>Hello</h1><img src="https://example.invalid/pixel"><script>alert(1)</script></body></html>')
    page.get_by_role('button',name='运行本地检查').click(); assert 'Sample' in page.locator('#panel').inner_text(); assert '发现 noindex' in page.locator('#panel').inner_text(); assert not any('example.invalid' in r for r in requests)
    page.get_by_role('button',name='新建空白项目').click(); page.get_by_label('品牌 / 产品名称').fill('FreeGEO Test');page.get_by_label('自有 URL 范围',exact=False).fill('https://example.com/tool');page.get_by_label('真实产品能力 / 服务').fill('Test');page.get_by_label('目标客户').fill('Tester');page.get_by_role('button',name='保存业务资料并更新计划').click();page.get_by_role('tab',name='问题库').click()
    page.get_by_label('自然语言问题').fill('如何使用 FreeGEO？'); page.get_by_label('目标人群 / 场景').fill('测试用户'); page.get_by_role('button',name='添加记录').click(); assert '如何使用 FreeGEO？' in page.locator('table').inner_text()
    page.get_by_role('tab',name='答案观测').click(); page.get_by_label('引擎 / 模型').fill('Manual');page.get_by_label('终端（Web / App / API）').fill('Web');page.get_by_label('地区').fill('CN');page.get_by_label('语言',exact=True).fill('zh-CN');page.get_by_label('批次（如 baseline）').fill('baseline');page.get_by_label('原始回答 / 核验记录（失败可写原因）').fill('测试原始证据');page.get_by_label('提及目标品牌').select_option('是');page.get_by_role('button',name='添加记录').click();assert 'Manual' in page.locator('table').inner_text()
    page.get_by_role('tab',name='概览').click();assert '100.0%' in page.locator('#panel').inner_text()
    with page.expect_download() as download:
        page.get_by_role('button',name='导出 JSON').click()
    exported=json.loads(Path(download.value.path()).read_text());assert len(exported['questions'])==len(exported['observations'])==1
    page.locator('#import').set_input_files(str(root/'examples/demo.json'));page.wait_for_function("document.querySelector('#project-name').textContent.includes('DEMO')")
    page.reload(); assert 'DEMO' in page.locator('#project-name').inner_text()
    # A stale tab must never overwrite a newer project library via full restore.
    key='freegeo-project-library-v1'
    old=page.evaluate('(k)=>localStorage.getItem(k)',key)
    other=context.new_page()
    other.goto(base+'/index.html')
    other.get_by_role('button',name='新建空白项目').click()
    latest=other.evaluate('(k)=>localStorage.getItem(k)',key)
    assert latest!=old
    page.locator('#import-all').set_input_files({'name':'old.json','mimeType':'application/json','buffer':old.encode()})
    page.wait_for_function("document.querySelector('#notice').textContent.includes('其他页面已经更新')")
    assert page.evaluate('(k)=>localStorage.getItem(k)',key)==latest
    other.close()
    page.reload()
    tab=page.locator('#tabs [aria-selected=true]')
    tab.focus(); page.keyboard.press('ArrowRight')
    assert page.evaluate("document.activeElement.getAttribute('aria-selected')")== 'true'
    assert page.locator('#tabs [tabindex="0"]').count()==1
    assert page.locator('#panel').get_attribute('aria-labelledby')==page.locator('#tabs [aria-selected=true]').get_attribute('id')
    page.keyboard.press('Home')
    assert page.locator('#tabs [aria-selected=true]').get_attribute('id')==page.locator('#tabs [role=tab]').first.get_attribute('id')
    for width in (360,390,1280):
        page.set_viewport_size({'width':width,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),width
    page.emulate_media(reduced_motion='reduce')
    assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior")=='auto'
    assert page.locator('#copy-wechat').evaluate("(el)=>getComputedStyle(el).transitionDuration")=='0s'
    assert page.locator('link[rel=canonical]').get_attribute('href')=='https://aipmandy.github.io/FreeGEO/'
    assert json.loads(page.locator('script[type="application/ld+json"]').text_content())['@type']=='WebApplication'
    assert page.locator('a[href="https://www.a6no1.cn/"]').count()>=1
    assert page.locator('a[href="https://metaver.vip/services"]').count()==1
    page.goto(base+'/docs/research.html');assert page.locator('h1').count()==1;assert page.locator('table').count()>=8
    assert not errors, errors
    browser.close()
print('Browser smoke: demo, experiment, offline audit, new project, question/observation, overview, export/import, reload, mobile, report — PASS')
