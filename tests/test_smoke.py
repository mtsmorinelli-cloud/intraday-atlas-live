import ast, json, pathlib, unittest
class SmokeTests(unittest.TestCase):
 def test_scanner_syntax(self):
  ast.parse(pathlib.Path("scanner.py").read_text(encoding="utf-8"))
 def test_news_config(self):
  x=json.loads(pathlib.Path("config/news_events.json").read_text(encoding="utf-8"))
  self.assertIn("events",x)
 def test_dashboard(self):
  x=pathlib.Path("index.html").read_text(encoding="utf-8")
  self.assertIn("scantable",x)
  self.assertIn("Intraday Atlas",x)
if __name__=="__main__":unittest.main()
