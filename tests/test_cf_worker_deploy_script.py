from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloudflareDeployScriptDocsTests(unittest.TestCase):
    def test_deploy_script_contains_expected_safety_and_deploy_steps(self):
        script = ROOT / "scripts" / "deploy-cf-worker.ps1"
        content = script.read_text(encoding="utf-8")

        self.assertIn("CLOUDFLARE_API_TOKEN", content)
        self.assertIn("npm ci", content)
        self.assertIn("npm test", content)
        self.assertIn("npx tsc --noEmit", content)
        self.assertIn("npm run check:worker", content)
        self.assertIn("wrangler secret put", content)
        self.assertIn("wrangler deploy", content)
        self.assertIn("https://$WorkerHost/", content)
        self.assertIn("Remove-Item Env:CLOUDFLARE_API_TOKEN", content)

    def test_readme_documents_one_click_deploy_and_update_flow(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("一键脚本部署", readme)
        self.assertIn("scripts/deploy-cf-worker.ps1", readme)
        self.assertIn("CLOUDFLARE_API_TOKEN", readme)
        self.assertIn("后续更新", readme)
        self.assertIn("ROCOM_API_KEY", readme)
        self.assertIn("SERVERCHAN_SENDKEY", readme)


if __name__ == "__main__":
    unittest.main()
