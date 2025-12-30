---
name: slack-message
description: Post messages to Slack channels via webhook. Use when you need to send notifications, alerts, or messages to Slack from automated workflows.
license: MIT
compatibility: Requires SLACK_WEBHOOK_URL environment variable or webhook_url parameter
metadata:
  author: YoruLabs
  version: "1.0"
---

# Slack Message Skill

Send messages to Slack channels using incoming webhooks.

## Prerequisites

You need a Slack Incoming Webhook URL. To get one:

1. Go to your Slack workspace's App Directory
2. Search for "Incoming Webhooks" and add it
3. Choose a channel and copy the webhook URL
4. Either set `SLACK_WEBHOOK_URL` environment variable or pass it as a parameter

## Available Scripts

- `post.py` - Post a message to Slack

## How to Use

### Basic Usage

```
execute_skill_script("slack-message", "post.py", {
    "message": "Hello from Skills MCP!"
})
```

### With Webhook URL

```
execute_skill_script("slack-message", "post.py", {
    "webhook_url": "https://hooks.slack.com/services/...",
    "message": "Deployment completed successfully! ✅"
})
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | The message text to post |
| `webhook_url` | string | No | Slack webhook URL (or set SLACK_WEBHOOK_URL env var) |
| `channel` | string | No | Override the default channel |
| `username` | string | No | Override the bot username |

### Example Response

**Success:**
```json
{
  "status": "success",
  "message": "Message posted to Slack successfully",
  "timestamp": "2024-12-30T12:00:00"
}
```

**Error (no webhook):**
```json
{
  "status": "error",
  "message": "No webhook_url provided and SLACK_WEBHOOK_URL not set"
}
```

## Security Notes

- Never commit webhook URLs to version control
- Use environment variables for sensitive credentials
- Webhook URLs should be treated as secrets
