# UptimeRobot Setup Guide

Manual configuration for continuous monitoring of gautamsachdeva.com via [UptimeRobot](https://uptimerobot.com/) (free plan).

## Account Setup

1. Sign up at https://uptimerobot.com/ (free — 50 monitors, 5-minute intervals)
2. Verify your email
3. Add alert contacts (email address for notifications)

## HTTP Monitors (8 total)

Create the following HTTP(S) monitors with **5-minute intervals**:

| # | Friendly Name | URL | Type |
|---|---|---|---|
| 1 | GS - Homepage | `https://gautamsachdeva.com/` | HTTP(S) |
| 2 | GS - Events | `https://gautamsachdeva.com/events/` | HTTP(S) |
| 3 | GS - Contact | `https://gautamsachdeva.com/contact/` | HTTP(S) |
| 4 | GS - Get Updates | `https://gautamsachdeva.com/get-updates/` | HTTP(S) |
| 5 | GS - Books | `https://gautamsachdeva.com/books/` | HTTP(S) |
| 6 | GS - Podcasts | `https://gautamsachdeva.com/podcasts/` | HTTP(S) |
| 7 | GS - Support | `https://gautamsachdeva.com/support-the-teaching/` | HTTP(S) |
| 8 | GS - WP REST API | `https://gautamsachdeva.com/wp-json/` | HTTP(S) |

### Settings for each monitor:
- **Monitoring Interval:** 5 minutes
- **Monitor Timeout:** 30 seconds
- **Alert Contacts:** Select your email contact
- **HTTP Method:** HEAD (faster) or GET

## SSL Monitor (1 total)

| Friendly Name | URL | Alert Days |
|---|---|---|
| GS - SSL Certificate | `https://gautamsachdeva.com/` | 30, 14, 7 days before expiry |

**Note:** UptimeRobot's free plan includes SSL monitoring. Set alerts at 30, 14, and 7 days before expiry.

## Keyword Monitor (1 total)

| Friendly Name | URL | Keyword | Type |
|---|---|---|---|
| GS - Support Page Content | `https://gautamsachdeva.com/support-the-teaching/` | `Bank Transfer` | Keyword (exists) |

This verifies the Support the Teaching page still shows bank transfer details. If the keyword disappears (page broken or content removed), you'll be alerted.

## Alert Contacts

Add the following alert contacts under **My Settings > Alert Contacts**:

1. **Email** — your primary email address
2. *(Optional)* **Webhook** — for future Slack/Discord integration

## Verification Checklist

After setup, verify:
- [ ] All 8 HTTP monitors show "Up" status
- [ ] SSL monitor shows certificate details and expiry date
- [ ] Keyword monitor shows "Up" (keyword found)
- [ ] Test alerts by pausing and resuming a monitor
- [ ] Email notifications arrive within 5 minutes of a detected issue

## Maintenance

- **Monthly:** Review the UptimeRobot dashboard for any recurring downtime patterns
- **When adding new pages:** Create a new HTTP monitor for the page
- **SSL renewal:** UptimeRobot will alert at 30/14/7 days — renew before expiry
