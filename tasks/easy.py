"""
Easy Task: Email Triage
Capacity: 1500 tokens | Cycles: 15
Scenario: 10 realistic corporate emails (spam, HR, security alerts, CEO urgent)
Goal: Identify critical action items, mark important emails
"""
from tasks.base import Task


def get_easy_task() -> Task:
    return Task(
        name="email_triage_easy",
        difficulty="easy",
        attention_capacity=1500,
        max_cycles=15,
        inputs=[
            (
                '{"from": "promotions@shopmart.com", "subject": "Flash Sale 80% Off!", '
                '"body": "Limited time offer on all electronics. Use code SAVE80.", '
                '"timestamp": "2024-03-15T08:12:00Z", "priority": "low", "category": "spam"}'
            ),
            (
                '{"from": "hr@company.com", "subject": "Office Closure Notice", '
                '"body": "The downtown office will be closed Friday March 22 for maintenance. '
                'Remote work approved. Contact facilities@company.com for questions.", '
                '"timestamp": "2024-03-15T08:30:00Z", "priority": "medium", "category": "hr"}'
            ),
            (
                '{"from": "newsletter@techdigest.io", "subject": "Weekly Tech Roundup", '
                '"body": "Top stories: AI breakthroughs, new chip architecture, quantum computing update. '
                'Read more at techdigest.io/weekly", '
                '"timestamp": "2024-03-15T09:00:00Z", "priority": "low", "category": "newsletter"}'
            ),
            (
                '{"from": "ceo@company.com", "subject": "URGENT: Client Escalation - Acme Corp", '
                '"body": "The Acme Corp deal is at risk. Their CTO wants a call TODAY at 3 PM EST. '
                'Prepare the Q4 metrics dashboard and join the bridge line: +1-555-0191. '
                'This is our largest account — do not miss this.", '
                '"timestamp": "2024-03-15T09:15:00Z", "priority": "critical", "category": "executive"}'
            ),
            (
                '{"from": "jira@atlassian.net", "subject": "JIRA-4521 assigned to you", '
                '"body": "Bug report: Login page CSS broken on Safari 17. Priority: P3. '
                'Assigned by: dev-lead@company.com. Due: March 25.", '
                '"timestamp": "2024-03-15T09:20:00Z", "priority": "medium", "category": "task"}'
            ),
            (
                '{"from": "security@company.com", "subject": "Security Alert: Unusual Login", '
                '"body": "We detected a login from IP 185.220.101.42 (TOR exit node) to your account '
                'at 03:42 UTC. If this was not you, reset your password immediately at '
                'https://sso.company.com/reset", '
                '"timestamp": "2024-03-15T09:45:00Z", "priority": "high", "category": "security"}'
            ),
            (
                '{"from": "spam@lottery-winner.xyz", "subject": "You Won $5,000,000!!!", '
                '"body": "Congratulations! Send your bank details to claim your prize.", '
                '"timestamp": "2024-03-15T10:00:00Z", "priority": "low", "category": "spam"}'
            ),
            (
                '{"from": "devops@company.com", "subject": "Deploy v2.14.3 Complete", '
                '"body": "Production deploy succeeded. Changelog: bugfix for payment gateway timeout, '
                'updated rate limiter config. Rollback tag: v2.14.2", '
                '"timestamp": "2024-03-15T10:15:00Z", "priority": "low", "category": "devops"}'
            ),
            (
                '{"from": "finance@company.com", "subject": "Expense Report Reminder", '
                '"body": "Q1 expense reports are due by March 31. Submit via Concur. '
                'Late submissions will not be reimbursed until Q3.", '
                '"timestamp": "2024-03-15T10:30:00Z", "priority": "medium", "category": "finance"}'
            ),
            (
                '{"from": "cto@company.com", "subject": "RE: URGENT: Client Escalation - Acme Corp", '
                '"body": "Adding context: Acme Corp is threatening to switch to competitor. '
                'Revenue impact: $2.4M/year. We need the uptime SLA numbers from last quarter. '
                'I already pinged the SRE team.", '
                '"timestamp": "2024-03-15T10:45:00Z", "priority": "critical", "category": "executive"}'
            ),
        ],
        final_question=(
            "Identify the most critical action items from this inbox and what must be done immediately."
        ),
        expected_answers=[
            "3 PM",
            "Acme Corp",
            "security alert",
            "password",
        ],
        important_ids=[3, 5, 9],
        partial_milestones={
            "found_urgent_email": ["acme", "ceo", "urgent", "client escalation"],
            "found_security_alert": ["security", "unusual login", "tor", "reset password"],
            "found_followup": ["cto", "revenue", "competitor", "sla"],
        },
    )
