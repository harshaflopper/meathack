"""
Hard Task: Incident Response — Cascading failure root-cause analysis
Capacity: 150 tokens | Cycles: 35
Scenario: 25 structured JSON production logs showing cascading failure:
          slow query → pool exhaustion → health check failure → OOMKill → node eviction
Goal: Root-cause analysis, identify chain of events, escalate with evidence
"""
from tasks.base import Task


def get_hard_task() -> Task:
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

    return Task(
        name="incident_response_hard",
        difficulty="hard",
        attention_capacity=150,
        max_cycles=35,
        inputs=base_logs,
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
