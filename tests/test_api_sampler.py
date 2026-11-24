import unittest, tempfile, csv
from pathlib import Path
from unittest.mock import patch
import api_sampler as m
class API(unittest.TestCase):
 def row(self):return {**dict.fromkeys(m.FIELDS,''),'prompt':'Real user question','id':'r1','qid':'q1','attempt':'1','engine':'OpenAI:test:web_search','surface':'API','region':'US','language':'en-US','batch':'test'}
 def response(self):return {'status':'completed','id':'resp_test','model':'test','output':[{'type':'web_search_call','status':'completed'},{'type':'message','role':'assistant','content':[{'type':'output_text','text':'example answer','annotations':[{'type':'url_citation','url':'https://example.org/'},{'type':'url_citation','url':'https://example.org/'},{'type':'url_citation','url':'javascript:bad'}]}]}]}
 def test_scope_and_cost(self):
  r=self.row();self.assertEqual(len(m.select_rows([r],'test',1)),1)
  with self.assertRaises(ValueError):m.select_rows([{**r,'surface':'Web'}],'test',1)
  with self.assertRaises(ValueError):m.select_rows([r],'test',51)
 def test_no_brand_or_private_profile_sent(self):
  b=m.request_body(self.row(),'test',512);self.assertEqual(b['input'],'Real user question');self.assertFalse(b['store']);self.assertEqual(b['tool_choice'],'required')
 def test_parse_real_annotations_not_guess(self):
  r=m.parse_response(self.response(),self.row());self.assertEqual(r['status'],'成功');self.assertEqual(r['citation'],'未知');self.assertEqual(r['sources'],'https://example.org/');self.assertEqual(r['search'],'是')
 def test_no_search_and_incomplete_are_failures(self):
  resp=self.response();resp['output']=resp['output'][1:];self.assertEqual(m.parse_response(resp,self.row())['status'],'失败');resp=self.response();resp['status']='incomplete';self.assertEqual(m.parse_response(resp,self.row())['status'],'失败')
 def test_dryrun_no_network(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'tasks.csv'
   with f.open('w',newline='') as out:
    w=csv.DictWriter(out,m.FIELDS);w.writeheader();w.writerow(self.row())
   with patch.object(m,'call',side_effect=AssertionError('network forbidden')):
    self.assertEqual(m.main([str(f),'--model','test']),0)
    with self.assertRaises(ValueError):m.main([str(f),'--model','test','--execute'])
 def test_formula_safety(self):self.assertEqual(m.neutral(' =2+3'),"' =2+3")
if __name__=='__main__':unittest.main()
