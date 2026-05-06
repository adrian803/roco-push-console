import type { Sender } from "./common";
import {
  sendBark,
  sendGotify,
  sendNtfy,
  sendPushPlus,
  sendServerChan,
  sendWxPusher,
} from "./token";
import { sendDingTalkBot, sendFeishuBot } from "./webhook";
import { sendWecomBot, sendWecomChan } from "./wecom";

export const PROVIDER_SENDERS: Record<string, Sender> = {
  serverchan: sendServerChan,
  pushplus: sendPushPlus,
  wecomchan: sendWecomChan,
  wecom_bot: sendWecomBot,
  wxpusher: sendWxPusher,
  bark: sendBark,
  dingtalk_bot: sendDingTalkBot,
  feishu_bot: sendFeishuBot,
  ntfy: sendNtfy,
  gotify: sendGotify,
};
