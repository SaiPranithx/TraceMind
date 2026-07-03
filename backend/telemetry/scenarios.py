"""
Incident scenario catalogue.

Each Scenario is a self-contained description of one failure mode: which
service it hits, what the metric anomaly looks like, what the smoking-gun
log line says, and what a *correct* root-cause diagnosis should mention
(used later by the eval harness in Week 3 to score the Synthesis Agent).

Keeping this as data (not hardcoded into the agents) is what lets the same
agent code run against 8+ different incidents instead of one hardcoded demo.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    id: str
    service: str
    fault_type: str                 # machine-readable signature name
    display_name: str               # human label, e.g. "Memory leak"
    metric_name: str                # Prometheus metric under investigation
    baseline: float                 # steady-state value before the incident
    peak: float                     # value at the moment of the alert
    unit: str
    trend: str                      # "linear_climb" | "step_spike" | "sawtooth"
    log_event: str                  # machine-readable log signature name
    log_line: str                   # the smoking-gun line the Log Agent should find
    root_cause_keywords: tuple      # words/phrases a correct report should contain
    recommended_actions: tuple = field(default_factory=tuple)


SCENARIOS: list[Scenario] = [
    Scenario(
        id="memory-leak-checkout",
        service="checkout-service",
        fault_type="memory_leak_signature",
        display_name="Memory leak",
        metric_name="container_memory_usage_bytes",
        baseline=512,
        peak=3800,
        unit="MB",
        trend="linear_climb",
        log_event="oom_killer_event",
        log_line="Killed process 8842 (node) total-vm:4192880kB, anon-rss:3801024kB",
        root_cause_keywords=("memory leak", "oom", "heap", "connection pool"),
        recommended_actions=(
            "Roll back to the previous stable release",
            "Patch the connection/resource release logic",
            "Add a heap-usage alert threshold at 75% capacity",
        ),
    ),
    Scenario(
        id="cpu-spike-recommendations",
        service="recommendation-service",
        fault_type="cpu_saturation_signature",
        display_name="CPU saturation",
        metric_name="container_cpu_usage_percent",
        baseline=35,
        peak=99,
        unit="%",
        trend="step_spike",
        log_event="hot_loop_warning",
        log_line="WARN ranking_worker: retry loop exceeded 50k iterations for user_id=88213, aborting",
        root_cause_keywords=("cpu", "hot loop", "retry", "infinite loop"),
        recommended_actions=(
            "Add a max-retry circuit breaker to the ranking worker",
            "Roll back the last ranking-model deploy",
            "Add CPU-saturation paging before requests start timing out",
        ),
    ),
    Scenario(
        id="pool-exhaustion-payment",
        service="payment-service",
        fault_type="connection_pool_exhaustion_signature",
        display_name="DB connection pool exhaustion",
        metric_name="db_connection_pool_in_use",
        baseline=8,
        peak=100,
        unit="connections",
        trend="linear_climb",
        log_event="pool_timeout_error",
        log_line="ERROR HikariPool-1 - Connection is not available, request timed out after 30000ms",
        root_cause_keywords=("connection pool", "exhaustion", "timeout", "database"),
        recommended_actions=(
            "Increase pool size as a stopgap and page the on-call DBA",
            "Audit recent code paths for unclosed connections",
            "Add pool-utilization alerting at 80%",
        ),
    ),
    Scenario(
        id="disk-io-inventory",
        service="inventory-service",
        fault_type="disk_io_saturation_signature",
        display_name="Disk I/O saturation",
        metric_name="disk_io_await_ms",
        baseline=4,
        peak=850,
        unit="ms",
        trend="linear_climb",
        log_event="slow_query_warning",
        log_line="WARN slow_query: SELECT * FROM stock_ledger took 8421ms (index scan fallback)",
        root_cause_keywords=("disk i/o", "slow query", "index", "storage"),
        recommended_actions=(
            "Add the missing index on stock_ledger",
            "Move the nightly reindex job off peak hours",
            "Alert on disk await time above 200ms",
        ),
    ),
    Scenario(
        id="upstream-timeout-shipping",
        service="shipping-service",
        fault_type="upstream_dependency_timeout_signature",
        display_name="Upstream dependency timeout",
        metric_name="upstream_error_rate_percent",
        baseline=0.2,
        peak=64,
        unit="%",
        trend="step_spike",
        log_event="circuit_breaker_open",
        log_line="ERROR CircuitBreaker[carrier-api] state changed to OPEN after 12 consecutive timeouts",
        root_cause_keywords=("upstream", "timeout", "circuit breaker", "carrier"),
        recommended_actions=(
            "Confirm carrier-api status page / open a vendor ticket",
            "Fail over to the backup carrier integration",
            "Lower the circuit breaker trip threshold to fail faster",
        ),
    ),
    Scenario(
        id="deploy-regression-auth",
        service="auth-service",
        fault_type="query_regression_signature",
        display_name="Deploy-introduced N+1 query",
        metric_name="p99_latency_ms",
        baseline=120,
        peak=4400,
        unit="ms",
        trend="step_spike",
        log_event="query_count_warning",
        log_line="WARN session_loader: issued 214 queries to resolve 1 request (expected <5)",
        root_cause_keywords=("n+1", "query", "deploy", "latency"),
        recommended_actions=(
            "Roll back the v3.2.0 auth-service deploy",
            "Add eager-loading to the session resolver",
            "Add a query-count budget to CI",
        ),
    ),
    Scenario(
        id="cache-stampede-catalog",
        service="catalog-service",
        fault_type="cache_stampede_signature",
        display_name="Cache stampede",
        metric_name="cache_hit_rate_percent",
        baseline=97,
        peak=11,
        unit="%",
        trend="step_spike",
        log_event="cache_miss_burst",
        log_line="WARN redis_client: 40213 cache misses in 5s window following key expiry burst",
        root_cause_keywords=("cache", "stampede", "expiry", "redis"),
        recommended_actions=(
            "Stagger TTLs to avoid synchronized key expiry",
            "Add request coalescing / locking on cache miss",
            "Warm the cache before the nightly TTL reset",
        ),
    ),
    Scenario(
        id="disk-full-notifications",
        service="notifications-service",
        fault_type="disk_full_signature",
        display_name="Disk full",
        metric_name="disk_usage_percent",
        baseline=61,
        peak=100,
        unit="%",
        trend="linear_climb",
        log_event="no_space_left_error",
        log_line="ERROR write failed: No space left on device (/var/log/notifications)",
        root_cause_keywords=("disk full", "no space", "log rotation"),
        recommended_actions=(
            "Clear or rotate oversized log files immediately",
            "Add log rotation with size caps",
            "Alert on disk usage above 85%",
        ),
    ),
]


def get_scenario(scenario_id: str) -> Scenario:
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    raise KeyError(f"Unknown scenario id: {scenario_id}")
