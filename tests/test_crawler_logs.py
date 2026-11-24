import unittest,json
from crawler_logs import summarize
class Logs(unittest.TestCase):
 def line(self,ua,status='200'):return f'192.0.2.123 - - [24/Nov/2026:00:00:00 +0000] "GET /secret?q=private HTTP/1.1" {status} 12 "https://private.example/" "{ua}"\n'
 def test_claim_and_status(self):
  x=summarize([self.line('Mozilla/5.0 (compatible; OAI-SearchBot/1.0)'),self.line('GPTBot/1.2','403'),self.line('human'),'bad']);self.assertEqual(x['claimed_crawler_lines'],2);self.assertEqual(x['other_lines'],1);self.assertEqual(x['unparsed_or_ambiguous'],1);self.assertEqual(x['rows'][0]['http_status'],403)
 def test_privacy_and_spoof_limits(self):
  x=json.dumps(summarize([self.line('OAI-SearchBot/1.0')]),ensure_ascii=False);self.assertNotIn('192.0.2.123',x);self.assertNotIn('/secret',x);self.assertNotIn('private.example',x);self.assertIn('spoofed',x)
 def test_ambiguous_agent(self):self.assertEqual(summarize([self.line('GPTBot OAI-SearchBot')])['unparsed_or_ambiguous'],1)
