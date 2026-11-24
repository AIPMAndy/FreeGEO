import unittest,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from site_doctor import audit,robots_policy,public_ip,fetch
class DoctorTests(unittest.TestCase):
 def test_html_real_blockers(self):
  r=audit('<html><head><meta name="robots" content="noindex"><script type="application/ld+json">oops</script></head><body><script>hidden</script></body></html>','https://example.com/a',200,{'X-Robots-Tag':'none'},'User-agent: OAI-SearchBot\nDisallow: /a',200)
  codes={x['code']:x['priority'] for x in r['findings']};self.assertEqual(codes['noindex'],'P0');self.assertEqual(codes['jsonld'],'P1');self.assertEqual(codes['robots_OAI-SearchBot'],'P1');self.assertEqual(r['body_chars_approx'],0)
 def test_no_evidence_is_not_pass(self):
  r=audit('<title>Test</title><h1>Test</h1>');self.assertTrue(any(x['priority']=='待核验' and x['code']=='http' for x in r['findings']))
 def test_http_error_and_canonical(self):
  r=audit('<title>X</title><link rel="canonical" href="/other"><h1>X</h1>','https://example.com/a',503);codes={x['code']:x['priority'] for x in r['findings']};self.assertEqual(codes['http'],'P0');self.assertEqual(codes['canonical'],'P1')
 def test_robots_specific_and_tie(self):
  t='User-agent: *\nDisallow: /\nUser-agent: OAI-SearchBot\nDisallow: /tool\nAllow: /tool/public\nDisallow: /tool/public\n'
  self.assertEqual(robots_policy(t,'OAI-SearchBot','/tool/public')['decision'],'Allow');self.assertEqual(robots_policy(t,'OAI-SearchBot','/tool/a')['decision'],'Disallow');self.assertEqual(robots_policy(t,'Googlebot','/other')['decision'],'Disallow')
 def test_wildcard_and_end(self):
  t='User-agent: *\nDisallow: /*.pdf$\n';self.assertEqual(robots_policy(t,'Googlebot','/abc.pdf')['decision'],'Disallow');self.assertEqual(robots_policy(t,'Googlebot','/abc.pdf?x')['decision'],'未发现匹配限制')
 def test_non_200_robots_not_assume_allow(self):
  r=audit('<h1>x</h1>','https://example.com',200,{},'forbidden',403);self.assertTrue(any(x['code']=='robots_status' and x['priority']=='待核验' for x in r['findings']))
 def test_ssrf_blocked(self):
  for u in ['file:///etc/passwd','http://localhost:8080','http://user:pass@example.com','http://127.0.0.1','http://169.254.169.254']:
   with self.assertRaises(ValueError):fetch(u)
 def test_mixed_dns_rejected(self):
  with patch('socket.getaddrinfo',return_value=[(0,0,0,'',('1.1.1.1',443)),(0,0,0,'',('127.0.0.1',443))]):
   with self.assertRaises(ValueError):public_ip('test.example',443)
if __name__=='__main__':unittest.main()
