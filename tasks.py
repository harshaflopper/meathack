import random
from typing import Dict, Any, List

class Task:
    def __init__(
        self,
        name: str,
        difficulty: str,
        attention_capacity: int,
        max_cycles: int,
        inputs: List[str],
        final_question: str,
        expected_answers: List[str],
        config_bugs: Dict[str, str] = None,
        services: Dict[str, str] = None,
        important_ids: List[int] = None,
        partial_milestones: Dict[str, List[str]] = None,
    ):
        self.name = name
        self.difficulty = difficulty
        self.attention_capacity = attention_capacity
        self.max_cycles = max_cycles
        self.inputs = inputs
        self.final_question = final_question
        self.expected_answers = expected_answers
        self.config_bugs = config_bugs or {}
        self.services = services or {}
        self.important_ids = important_ids or []
        self.partial_milestones = partial_milestones or {}

    def grade(self, answer: str, justifications: List[str]) -> float:
        ans_lower = answer.lower()
        matches = sum(1 for exp in self.expected_answers if exp.lower() in ans_lower)
        total = len(self.expected_answers)

        if total == 0:
            return 0.0

        correctness = matches / total

        has_justification = len(justifications) > 0

        if correctness >= 0.8 and has_justification:
            return 1.0
        elif correctness >= 0.8 and not has_justification:
            return 0.5
        elif correctness >= 0.4 and has_justification:
            return 0.3 + (correctness * 0.5)
        elif correctness > 0:
            return correctness * 0.4
        return 0.0


def get_tasks() -> List[Task]:
    # =========================================================================
    # EASY TASK: Email Triage — Identify & mark the critical emails
    # =========================================================================
    easy = Task(
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

    # =========================================================================
    # MEDIUM TASK: Config Debugging — Fix the broken staging deployment
    # =========================================================================
    medium = Task(
        name="config_debugging_medium",
        difficulty="medium",
        attention_capacity=300,
        max_cycles=20,
        inputs=[
            (
                '[File: .env.staging]\n'
                'DATABASE_URL=postgresql://app_user:s3cret@10.0.2.14:5432/appdb\n'
                'REDIS_HOST=localhost\n'
                'REDIS_PORT=6379\n'
                'LOG_LEVEL=debug\n'
                'API_RATE_LIMIT=100\n'
                'SESSION_TTL=3600'
            ),
            (
                '[File: docker-compose.staging.yml]\n'
                'services:\n'
                '  api:\n'
                '    image: app-api:2.14.3\n'
                '    ports: ["8080:8080"]\n'
                '    env_file: .env.staging\n'
                '    depends_on: [redis, postgres]\n'
                '  redis:\n'
                '    image: redis:7-alpine\n'
                '    ports: ["6379:6379"]\n'
                '    networks: [backend]\n'
                '  postgres:\n'
                '    image: postgres:15\n'
                '    networks: [backend]'
            ),
            (
                '[Log: api-server 2024-03-15T14:02:11Z] INFO  Starting API server v2.14.3\n'
                '[Log: api-server 2024-03-15T14:02:11Z] INFO  Connecting to Redis at localhost:6379\n'
                '[Log: api-server 2024-03-15T14:02:12Z] ERROR ConnectionRefusedError: '
                'Connection refused at localhost:6379 — retrying (1/3)\n'
                '[Log: api-server 2024-03-15T14:02:15Z] ERROR ConnectionRefusedError: '
                'Connection refused at localhost:6379 — retrying (2/3)\n'
                '[Log: api-server 2024-03-15T14:02:18Z] FATAL Max retries exceeded. Redis unavailable.'
            ),
            (
                '[File: config/redis.py]\n'
                'import os\n'
                'import redis\n'
                '\n'
                'REDIS_HOST = os.getenv("REDIS_HOST", "localhost")\n'
                'REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))\n'
                '\n'
                'cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)\n'
                '\n'
                'def ping():\n'
                '    try:\n'
                '        return cache.ping()\n'
                '    except redis.ConnectionError as e:\n'
                '        raise SystemExit(f"Redis connection failed: {e}")'
            ),
            (
                '[File: config/nginx.conf]\n'
                'upstream api_backend {\n'
                '    server api:8080;\n'
                '}\n'
                'server {\n'
                '    listen 80;\n'
                '    location / {\n'
                '        proxy_pass http://api_backend;\n'
                '        proxy_set_header Host $host;\n'
                '    }\n'
                '    location /health {\n'
                '        return 200 "OK";\n'
                '    }\n'
                '}'
            ),
            (
                '[Log: docker-network 2024-03-15T14:01:55Z] INFO  Network "backend" created\n'
                '[Log: docker-network 2024-03-15T14:01:56Z] INFO  Container "redis" attached to '
                '"backend" network with IP 172.18.0.3\n'
                '[Log: docker-network 2024-03-15T14:01:56Z] INFO  Container "postgres" attached to '
                '"backend" network with IP 172.18.0.4\n'
                '[Log: docker-network 2024-03-15T14:01:57Z] WARN  Container "api" is NOT attached '
                'to "backend" network — using default bridge'
            ),
            (
                '[Runbook: Redis Connectivity Troubleshooting]\n'
                '1. Verify REDIS_HOST in .env matches the Docker service name (should be "redis", '
                'not "localhost" in containerized deployments)\n'
                '2. Ensure both api and redis containers share the same Docker network\n'
                '3. Check firewall rules: port 6379 must be open within the network\n'
                '4. Test with: docker exec api redis-cli -h redis ping'
            ),
        ],
        final_question=(
            "Fix the issue causing the API server to fail connecting to Redis on staging. "
            "What specific configuration changes are needed?"
        ),
        expected_answers=[
            "REDIS_HOST",
            "localhost",
            "redis",
            "network",
        ],
        config_bugs={
            "REDIS_HOST": "localhost",
            "correct_value": "redis",
            "api_network": "missing backend network",
        },
        services={
            "api": "crashed",
            "redis": "running",
            "postgres": "running",
            "nginx": "running",
        },
        partial_milestones={
            "found_config_bug": ["redis_host", "localhost", ".env"],
            "found_network_issue": ["network", "backend", "not attached"],
            "found_logs": ["connectionrefused", "connection refused", "retrying"],
        },
    )

    # =========================================================================
    # HARD TASK: Incident Response — Cascading failure root-cause analysis
    # =========================================================================
    hard_inputs = []

    # Simulate 30 log entries — realistic structured logs
    base_logs = [
        '{"ts": "2024-03-15T14:00:00Z", "service": "lb", "level": "INFO", '
        '"msg": "Health check passed", "node": "alpha", "latency_ms": 12, "req_id": "r-001"}',

        '{"ts": "2024-03-15T14:00:30Z", "service": "api-alpha", "level": "INFO", '
        '"msg": "Request processed", "endpoint": "/api/v2/orders", "status": 200, '
        '"latency_ms": 45, "req_id": "r-002"}',

        '{"ts": "2024-03-15T14:01:00Z", "service": "db-primary", "level": "INFO", '
        '"msg": "Connection pool stats", "active": 12, "idle": 38, "max": 50, "req_id": "r-003"}',

        '{"ts": "2024-03-15T14:01:30Z", "service": "api-alpha", "level": "INFO", '
        '"msg": "Request processed", "endpoint": "/api/v2/users", "status": 200, '
        '"latency_ms": 38, "req_id": "r-004"}',

        '{"ts": "2024-03-15T14:02:00Z", "service": "lb", "level": "WARN", '
        '"msg": "Health check timeout", "node": "alpha", "timeout_ms": 5000, '
        '"consecutive_failures": 1, "req_id": "r-005"}',

        '{"ts": "2024-03-15T14:02:30Z", "service": "db-primary", "level": "WARN", '
        '"msg": "Slow query detected", "query": "SELECT * FROM orders WHERE status=pending", '
        '"duration_ms": 3200, "rows_scanned": 1450000, "req_id": "r-006"}',

        '{"ts": "2024-03-15T14:03:00Z", "service": "api-alpha", "level": "WARN", '
        '"msg": "Request latency spike", "endpoint": "/api/v2/orders", "latency_ms": 4800, '
        '"req_id": "r-007"}',

        '{"ts": "2024-03-15T14:03:30Z", "service": "db-primary", "level": "ERROR", '
        '"msg": "Connection pool exhausted", "active": 50, "idle": 0, "max": 50, '
        '"waiting": 14, "req_id": "r-008"}',

        '{"ts": "2024-03-15T14:04:00Z", "service": "lb", "level": "WARN", '
        '"msg": "Health check timeout", "node": "alpha", "timeout_ms": 5000, '
        '"consecutive_failures": 2, "req_id": "r-009"}',

        '{"ts": "2024-03-15T14:04:30Z", "service": "api-alpha", "level": "ERROR", '
        '"msg": "Database transaction timeout", "operation": "insert_order", '
        '"timeout_ms": 10000, "req_id": "r-010"}',

        '{"ts": "2024-03-15T14:05:00Z", "service": "api-alpha", "level": "ERROR", '
        '"msg": "Circuit breaker OPEN for db-primary", "failures": 15, '
        '"threshold": 10, "req_id": "r-011"}',

        '{"ts": "2024-03-15T14:05:30Z", "service": "api-beta", "level": "INFO", '
        '"msg": "Request processed", "endpoint": "/api/v2/users", "status": 200, '
        '"latency_ms": 42, "req_id": "r-012"}',

        '{"ts": "2024-03-15T14:06:00Z", "service": "lb", "level": "ERROR", '
        '"msg": "Health check FAILED", "node": "alpha", "consecutive_failures": 3, '
        '"action": "marking_unhealthy", "req_id": "r-013"}',

        '{"ts": "2024-03-15T14:06:30Z", "service": "api-alpha", "level": "ERROR", '
        '"msg": "OOMKilled by container runtime", "memory_usage_mb": 2048, '
        '"memory_limit_mb": 2048, "req_id": "r-014"}',

        '{"ts": "2024-03-15T14:07:00Z", "service": "lb", "level": "WARN", '
        '"msg": "All traffic rerouted to beta", "reason": "alpha_unhealthy", '
        '"req_id": "r-015"}',

        '{"ts": "2024-03-15T14:07:30Z", "service": "api-beta", "level": "WARN", '
        '"msg": "Request latency spike under increased load", "latency_ms": 2100, '
        '"req_id": "r-016"}',

        '{"ts": "2024-03-15T14:08:00Z", "service": "db-primary", "level": "ERROR", '
        '"msg": "Disk I/O saturation", "iops": 15000, "max_iops": 12000, '
        '"disk_util_pct": 98, "req_id": "r-017"}',

        '{"ts": "2024-03-15T14:08:30Z", "service": "monitoring", "level": "ALERT", '
        '"msg": "PagerDuty triggered", "severity": "SEV1", '
        '"title": "Cascading failure: alpha down, beta degraded", "req_id": "r-018"}',

        '{"ts": "2024-03-15T14:09:00Z", "service": "db-primary", "level": "ERROR", '
        '"msg": "Replication lag exceeding threshold", "lag_seconds": 45, '
        '"threshold_seconds": 10, "req_id": "r-019"}',

        '{"ts": "2024-03-15T14:09:30Z", "service": "api-beta", "level": "ERROR", '
        '"msg": "Database transaction timeout", "operation": "get_user_profile", '
        '"timeout_ms": 10000, "req_id": "r-020"}',

        '{"ts": "2024-03-15T14:10:00Z", "service": "lb", "level": "CRITICAL", '
        '"msg": "Node alpha evicted from cluster", "reason": "consecutive_health_failures", '
        '"uptime_before_eviction": "47h22m", "req_id": "r-021"}',

        '{"ts": "2024-03-15T14:10:30Z", "service": "k8s-scheduler", "level": "INFO", '
        '"msg": "Pod alpha rescheduled on node-3", "prev_node": "node-1", '
        '"reason": "OOMKilled + health_failure", "req_id": "r-022"}',

        '{"ts": "2024-03-15T14:11:00Z", "service": "db-primary", "level": "WARN", '
        '"msg": "Connection pool recovering", "active": 35, "idle": 15, "max": 50, '
        '"req_id": "r-023"}',

        '{"ts": "2024-03-15T14:11:30Z", "service": "api-alpha", "level": "INFO", '
        '"msg": "Service restarted on node-3", "version": "2.14.3", "req_id": "r-024"}',

        '{"ts": "2024-03-15T14:12:00Z", "service": "lb", "level": "INFO", '
        '"msg": "Node alpha re-registered", "health": "passing", "req_id": "r-025"}',
    ]

    hard_inputs = base_logs

    hard = Task(
        name="incident_response_hard",
        difficulty="hard",
        attention_capacity=150,
        max_cycles=35,
        inputs=hard_inputs,
        final_question=(
            "Perform root-cause analysis of the cascading failure that led to Node Alpha's eviction. "
            "Identify the chain of events, fix the root cause, and escalate with a summary."
        ),
        expected_answers=[
            "slow query",
            "connection pool",
            "health check",
            "OOMKilled",
            "transaction timeout",
        ],
        services={
            "api-alpha": "crashed",
            "api-beta": "degraded",
            "db-primary": "overloaded",
            "lb": "running",
        },
        partial_milestones={
            "found_slow_query": ["slow query", "1450000", "rows_scanned"],
            "found_pool_exhausted": ["pool exhausted", "connection pool", "active: 50"],
            "found_health_failure": ["health check", "consecutive_failures", "marking_unhealthy"],
            "found_oom": ["oomkilled", "memory_usage"],
            "found_cascade": ["rerouted", "beta", "increased load"],
        },
    )

    return [easy, medium, hard]
