from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class GitHubActionsWorkflowTests(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_ci_workflow_uses_node24_capable_actions(self):
        content = self._read("ci.yml")

        self.assertIn("actions/checkout@v5", content)
        self.assertIn("actions/setup-python@v6", content)
        self.assertIn("astral-sh/setup-uv@v7", content)
        self.assertIn("actions/setup-node@v6", content)
        self.assertIn("./.github/actions/test-cf-worker", content)

    def test_scheduled_push_workflow_uses_node24_capable_actions(self):
        content = self._read("scheduled-push.yml")

        self.assertIn("actions/checkout@v5", content)
        self.assertIn("actions/setup-python@v6", content)
        self.assertIn("astral-sh/setup-uv@v7", content)

    def test_worker_release_workflow_uses_node24_capable_actions(self):
        content = self._read("worker-release.yml")

        self.assertIn("actions/checkout@v5", content)
        self.assertIn("actions/setup-node@v6", content)
        self.assertIn("./.github/actions/test-cf-worker", content)
        self.assertIn("releases/cloudflare-worker/_worker.js", content)

    def test_docker_publish_workflow_uses_node24_capable_actions(self):
        content = self._read("docker-publish.yml")

        self.assertIn("actions/checkout@v5", content)
        self.assertIn("docker/setup-qemu-action@v4", content)
        self.assertIn("docker/setup-buildx-action@v4", content)
        self.assertIn("docker/login-action@v4", content)
        self.assertIn("docker/metadata-action@v6", content)
        self.assertIn("docker/build-push-action@v7", content)


if __name__ == "__main__":
    unittest.main()
