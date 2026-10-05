"""
Out-of-Band Notification Hub.
Dispatches Windows Toast notifications and external alert webhooks.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationHub:
    """Dispatches notifications when agent requires intervention or completes long-running tasks."""

    def __init__(self, telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None) -> None:
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

    def notify_windows_toast(self, title: str, message: str) -> None:
        """Send native Windows 10/11 Toast notification via PowerShell WinRT."""
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
        $textNodes = $xml.GetElementsByTagName('text')
        $textNodes.Item(0).AppendChild($xml.CreateTextNode('{title}')) | Out-Null
        $textNodes.Item(1).AppendChild($xml.CreateTextNode('{message}')) | Out-Null

        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Steward')
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        $notifier.Show($toast)
        """
        try:
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logger.debug("Failed to emit Windows Toast notification: %s", e)

    async def notify_task_complete(self, session_id: str, title: str) -> None:
        """Trigger alert when agent finishes autonomous plan."""
        msg = f"Task completed for session {session_id}: {title}"
        logger.info("[NOTIFICATION] %s", msg)
        self.notify_windows_toast("Steward: Task Complete", msg)

    async def notify_approval_needed(self, session_id: str, tool_name: str, reason: str) -> None:
        """Trigger urgent alert when user clearance is required."""
        msg = f"Security approval required for {tool_name}: {reason}"
        logger.warning("[APPROVAL NEEDED] %s", msg)
        self.notify_windows_toast("Steward: Approval Needed", msg)
