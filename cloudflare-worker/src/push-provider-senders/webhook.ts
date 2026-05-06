import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";
import {
  appendDingTalkSign,
  feishuSign,
} from "../push-provider-auth";

export async function sendDingTalkBot(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const webhook = await appendDingTalkSign(
    provider.config.webhook,
    provider.config.secret || ""
  );
  const payload = {
    msgtype: "markdown",
    markdown: { title: message.title, text: message.markdown },
  };
  return postJson(provider, webhook, payload, timeoutSec);
}

export async function sendFeishuBot(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const payload: Record<string, unknown> = {
    msg_type: "post",
    content: {
      post: {
        zh_cn: {
          title: message.title,
          content: [
            [{ tag: "text", text: `${message.body}\n\n${message.markdown}` }],
          ],
        },
      },
    },
  };
  const secret = (provider.config.secret || "").trim();
  if (secret) {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    payload.timestamp = timestamp;
    payload.sign = await feishuSign(secret, timestamp);
  }
  return postJson(provider, provider.config.webhook, payload, timeoutSec);
}
