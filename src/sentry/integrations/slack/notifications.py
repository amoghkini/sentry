from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from copy import copy
from typing import Any

import orjson
import sentry_sdk
from slack_sdk.errors import SlackApiError

from sentry.integrations.mixins import NotifyBasicMixin
from sentry.integrations.notifications import get_context, get_integrations_by_channel_by_recipient
from sentry.integrations.slack.client import SlackClient
from sentry.integrations.slack.message_builder import SlackBlock
from sentry.integrations.slack.message_builder.base.block import BlockSlackMessageBuilder
from sentry.integrations.slack.message_builder.notifications import get_message_builder
from sentry.integrations.types import ExternalProviders
from sentry.models.integrations.integration import Integration
from sentry.notifications.additional_attachment_manager import get_additional_attachment
from sentry.notifications.notifications.base import BaseNotification
from sentry.notifications.notify import register_notification_provider
from sentry.shared_integrations.exceptions import ApiError
from sentry.silo.base import SiloMode
from sentry.tasks.integrations.slack import post_message, post_message_control
from sentry.types.actor import Actor
from sentry.utils import metrics

logger = logging.getLogger("sentry.notifications")
SLACK_TIMEOUT = 5


class SlackNotifyBasicMixin(NotifyBasicMixin):
    def send_message(self, channel_id: str, message: str) -> None:
        payload = {"channel": channel_id, "text": message}
        client = self.get_client()

        if isinstance(client, SlackClient):
            try:
                client.post("/chat.postMessage", data=payload, json=True)
            except ApiError as e:
                message = str(e)
                if message not in ["Expired url", "channel_not_found"]:
                    logger.exception(
                        "slack.slash-notify.response-error",
                        extra={"error": message},
                    )
        else:
            try:
                client.chat_postMessage(channel=channel_id, text=message)
            except SlackApiError as e:
                error = str(e)
                message = error.split("\n")[0]
                if "Expired url" not in message and "channel_not_found" not in message:
                    logger.exception(
                        "slack.slash-response.error",
                        extra={"error": error},
                    )


def _get_attachments(
    notification: BaseNotification,
    recipient: Actor,
    shared_context: Mapping[str, Any],
    extra_context_by_actor: Mapping[Actor, Mapping[str, Any]] | None,
) -> SlackBlock:
    extra_context = (
        extra_context_by_actor[recipient] if extra_context_by_actor and recipient else {}
    )
    context = get_context(notification, recipient, shared_context, extra_context)
    cls = get_message_builder(notification.message_builder)
    attachments = cls(notification, context, recipient).build()
    return attachments


def _notify_recipient(
    notification: BaseNotification,
    recipient: Actor,
    attachments: SlackBlock,
    channel: str,
    integration: Integration,
    shared_context: Mapping[str, Any],
) -> None:
    with sentry_sdk.start_span(op="notification.send_slack", description="notify_recipient"):
        # Make a local copy to which we can append.
        local_attachments = copy(attachments)

        text = notification.get_notification_title(ExternalProviders.SLACK, shared_context)

        blocks = []
        if text:
            blocks.append(BlockSlackMessageBuilder.get_markdown_block(text))
        attachment_blocks = local_attachments.get("blocks")
        if attachment_blocks:
            for attachment in attachment_blocks:
                blocks.append(attachment)
        if len(blocks) >= 2 and blocks[1].get("block_id"):
            # block id needs to be in the first block
            blocks[0]["block_id"] = blocks[1]["block_id"]
            del blocks[1]["block_id"]
        additional_attachment = get_additional_attachment(integration, notification.organization)
        if additional_attachment:
            for block in additional_attachment:
                blocks.append(block)
        if (
            not text
        ):  # if there isn't a notification title, try using message description as fallback
            text = notification.get_message_description(recipient, ExternalProviders.SLACK)
        payload = {
            "channel": channel,
            "unfurl_links": False,
            "unfurl_media": False,
            "text": text if text else "",
            "blocks": orjson.dumps(blocks).decode(),
        }
        callback_id = local_attachments.get("callback_id")
        if callback_id:
            # callback_id is now at the same level as blocks, rather than within attachments
            if isinstance(callback_id, str):
                payload["callback_id"] = callback_id
            else:
                payload["callback_id"] = orjson.dumps(local_attachments.get("callback_id")).decode()

        post_message_task = post_message
        if SiloMode.get_current_mode() == SiloMode.CONTROL:
            post_message_task = post_message_control

        log_params = {
            "notification": str(notification),
            "recipient": recipient.id,
            "channel_id": channel,
        }
        post_message_task.apply_async(
            kwargs={
                "integration_id": integration.id,
                "payload": payload,
                "log_error_message": "slack.notify_recipient.fail",
                "log_params": log_params,
            }
        )
    # recording data outside of span
    notification.record_notification_sent(recipient, ExternalProviders.SLACK)


@register_notification_provider(ExternalProviders.SLACK)
def send_notification_as_slack(
    notification: BaseNotification,
    recipients: Iterable[Actor],
    shared_context: Mapping[str, Any],
    extra_context_by_actor: Mapping[Actor, Mapping[str, Any]] | None,
) -> None:
    """Send an "activity" or "alert rule" notification to a Slack user or team, but NOT to a channel directly.
    Sending Slack notifications to a channel is in integrations/slack/actions/notification.py"""
    with sentry_sdk.start_span(
        op="notification.send_slack", description="gen_channel_integration_map"
    ):
        data = get_integrations_by_channel_by_recipient(
            notification.organization, recipients, ExternalProviders.SLACK
        )

    for recipient, integrations_by_channel in data.items():
        with sentry_sdk.start_span(op="notification.send_slack", description="send_one"):
            with sentry_sdk.start_span(op="notification.send_slack", description="gen_attachments"):
                attachments = _get_attachments(
                    notification,
                    recipient,
                    shared_context,
                    extra_context_by_actor,
                )

            for channel, integration in integrations_by_channel.items():
                _notify_recipient(
                    notification=notification,
                    recipient=recipient,
                    attachments=attachments,
                    channel=channel,
                    integration=integration,
                    shared_context=shared_context,
                )

    metrics.incr(
        f"{notification.metrics_key}.notifications.sent",
        instance=f"slack.{notification.metrics_key}.notification",
        skip_internal=False,
    )
