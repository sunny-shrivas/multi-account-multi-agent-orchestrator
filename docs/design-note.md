# Design Note: Multi-Account, Multi-Agent Orchestrator

## 1. Objective

The goal of this project is to coordinate multiple AI Workers to complete a larger plan while keeping execution controlled, observable, and verifiable.

The Master Orchestrator coordinates task execution, tracks dependencies, assigns work to available Workers, handles failures, and verifies deliverables before marking tasks complete.

The prototype includes a deterministic plan parser, a common Worker interface, mock Workers for repeatable testing, and integrations for OpenAI and Anthropic Claude. Successful live-provider execution has not been demonstrated in this submission.

## 2. Requirements and Design Decisions

| Requirement | Design approach |
|---|---|
| Multiple AI accounts | Account Manager loads Worker configurations |
| Written project plan | Deterministic parser converts plan items into tasks |
| Task dependencies | Explicit dependency information and dependency graph |
| Worker assignment | Scheduler assigns eligible tasks |
| Isolated execution | Separate Worker workspaces and path restrictions |
| Structured results | Shared `WorkerResult` schema |
| Failure handling | Retry and reassignment logic |
| Output verification | Verification Gate checks artifacts and acceptance criteria |
| Run history | Structured run logging with sensitive-field redaction |
| Testing | Happy-path and failure-scenario tests |

## 3. Architecture

The system is organized into these main areas:

1. **Plan Parser:** Converts supported written plan formats into task objects. It does not use an LLM to infer task breakdowns.
2. **Account Manager:** Loads Worker configurations and resolves credentials from environment variables.
3. **Master Orchestrator:** Coordinates task execution and verification.
4. **Dependency Graph and Scheduler:** Tracks prerequisites, selects eligible tasks, and manages assignment and retries.
5. **Workers:** Execute tasks and return standardized results.
6. **Verification and Reporting:** Checks deliverables and reports planned versus completed work.

The architecture diagram is maintained in [architecture.md](architecture.md).

## 4. Plan Parsing and Master Orchestration

The Master acts as the control plane. It coordinates work rather than blindly accepting a Worker's completion claim.

The current plan-ingestion flow is:

1. Receive a written project plan.
2. Parse supported numbered, bulleted, or line-separated task items.
3. Construct task objects with available acceptance criteria and dependency information.
4. Validate task references, acceptance-criteria references, and dependency cycles.
5. Build the execution graph.
6. Find tasks whose prerequisites have been verified.
7. Assign eligible tasks to available Workers.
8. Collect structured Worker results.
9. Verify the resulting artifacts.
10. Accept valid output or retry/reassign rejected work.
11. Produce a plan-versus-delivered report.

The parser is deterministic. It does not independently reason about a high-level goal, invent missing subtasks, or infer dependencies using an LLM. Plans requiring complex decomposition should provide explicit task details, acceptance criteria, and dependencies.

A task must not be marked complete merely because a Worker returns a successful status.

## 5. Scheduling and Dependencies

The dependency graph prevents tasks from executing before their prerequisites are verified.

The Scheduler selects eligible tasks and assigns them to available Workers. When a Worker fails or its output is rejected, retry or reassignment can occur within the configured limits.

If a prerequisite remains unresolved, dependent tasks should remain blocked. If retries are exhausted or no suitable Worker is available, the system should report unresolved work rather than claim full completion.

## 6. Account Management and Worker Abstraction

Worker definitions are loaded from configuration. The Account Manager supports configured mock Workers and provider-specific implementations for OpenAI and Anthropic.

Provider credentials are resolved from environment variables rather than hard-coded into source files.

The common Worker interface allows the Master to coordinate different Worker types without relying on provider-specific response formats.

Live-provider execution requires valid credentials, network access, and sufficient provider quota. Successful live execution has not been demonstrated as part of this submission because API credits were unavailable.

## 7. Worker Result Contract

Each Worker returns a structured `WorkerResult` containing:

- `task_id`
- `worker_id`
- `status`
- `files_changed`
- `notes`
- `error`

This contract standardizes Worker outcomes and gives the Master the information needed for orchestration and verification.

Malformed or incomplete results should be rejected through schema validation rather than silently treated as successful output.

## 8. Workspace Isolation and File Safety

Workers should only modify files within their assigned workspaces. The prototype includes workspace path restrictions and controlled file operations.

The workspace guard is an application-level restriction, not a complete security boundary. A compromised Worker process could require stronger operating-system controls to prevent access outside its workspace.

For production, I would use dedicated processes or containers, restricted filesystem mounts, non-privileged users, resource limits, and separate Git worktrees or branches when parallel Git-based development is required.

## 9. Verification Gate

The Verification Gate checks Worker results and generated artifacts against configured acceptance criteria.

The prototype performs deterministic checks such as:

- Whether expected artifacts exist.
- Whether paths remain within permitted workspaces.
- Whether output files are non-empty.
- Whether configured acceptance-criteria text is present.

Rejected output can trigger a retry or reassignment. Only verified tasks should unlock their dependent tasks.

These checks do not prove that arbitrary code is correct, secure, or semantically complete. Production verification should add relevant unit tests, static analysis, type checking, security scanning, and independent semantic review where appropriate.

## 10. Failure Handling

The prototype includes failure-handling behavior exercised through mock Workers and tests.

### Worker crash or failure

The failure should be returned as a structured result. The task must not be marked verified, and retry or reassignment should follow the Scheduler's policy.

### Quota exhaustion

A quota failure should not count as task completion. The Scheduler should attempt an eligible alternative Worker when possible. If none is available, the task and affected dependencies should remain unresolved.

### Rejected output

If the Verification Gate rejects a Worker's output, the Master should retain the rejection reason and allow retry or reassignment within the configured limit.

### No available Worker

The system should report that execution is blocked rather than present an incomplete plan as successful.

## 11. Security Guardrails

The prototype includes several defensive controls:

- Environment-based credential configuration.
- Workspace path restrictions.
- Checks for selected dangerous command patterns.
- Sensitive-field redaction in logs.
- Structured execution results and failure reporting.

The command guard uses pattern-based checks and is not a comprehensive command sandbox. It may not detect every dangerous command, shell variation, or indirect execution technique.

### Production security improvements

A production version should include:

- A managed secret vault or operating-system keychain.
- Least-privilege credentials and tool permissions.
- Process or container sandboxing.
- Filesystem and network allowlists.
- Explicit authorization for destructive operations.
- Audit trails for privileged actions.
- Security testing against prompt injection and tool misuse.

## 12. Prompt-Injection Defence

Repository files, READMEs, issue descriptions, and Worker-generated content must be treated as untrusted input. Instructions found inside such content must not override authorized system policies.

The application should separate trusted orchestration instructions from untrusted task data. Tool permissions must be enforced outside the language model, because prompt wording alone is not a security boundary.

The current workspace and command checks reduce some risks but do not provide complete prompt-injection protection.

## 13. Provider Terms and Account Compliance

The design must respect the terms of service, usage limits, and account policies of each AI provider.

The system should not assume that multiple personal subscriptions can be pooled, shared, or automated in every manner. Before using a provider integration, its current terms and automation policies must be reviewed.

A production deployment should use authorized API access or other explicitly permitted integration methods, apply rate limits, and avoid credential sharing that violates provider policies.

## 14. Logging and Auditability

The run logger records relevant execution events, such as task assignment, failures, and verification outcomes.

Logs should help answer:

- Which Worker received a task?
- Did execution succeed or fail?
- Why was output rejected?
- Was the task retried or reassigned?
- Which tasks remain unresolved?

Sensitive values such as API keys must not be written to logs. Production logging should also use retention limits, access controls, correlation IDs, and tamper-resistant storage where required.

## 15. Testing Strategy

The test suite covers successful execution and failure handling. The current suite contains 94 passing tests.

### Happy path

A written plan is parsed into tasks, eligible Workers execute the work, the Verification Gate accepts valid output, dependencies progress, and the report reflects delivered work.

### Failure tests

- Worker failure triggers the expected retry or reassignment behavior.
- Quota exhaustion does not falsely complete a task.
- Bad Worker output is rejected and must pass verification before acceptance.

Additional tests cover areas such as malformed Worker results, dependency validation, workspace traversal attempts, sensitive-log redaction, retry limits, and the absence of eligible Workers.

The tests validate the prototype's implemented behavior; they do not establish production-level security or reliability.

## 16. Handling Conflicting File Changes

Separate workspaces reduce the risk of Workers directly overwriting each other's changes.

For production, each Worker could work on an isolated Git branch or worktree. A controlled integration stage would identify overlapping file changes, attempt safe merges, and request human resolution when conflicts cannot be resolved safely.

Any merged output must be verified again. Automated conflict resolution is a proposed extension, not a claim about the current prototype.

## 17. Scaling from Four Workers to Twenty

The Account Manager and Scheduler are designed around registered Workers rather than a hard-coded number of accounts.

At a larger scale, likely bottlenecks include provider quotas, rate limits, concurrency limits, verification throughput, cost, and task dependencies.

Potential improvements include bounded concurrency, quota-aware assignment, retry backoff, fair scheduling, persistent task state, metrics, and centralized monitoring.

The prototype demonstrates multi-Worker orchestration using mock Workers. It has not been benchmarked with twenty live accounts.

## 18. Human-in-the-Loop Policy

Routine task planning, code generation, safe retries, and deterministic checks can run autonomously within defined permissions.

Human approval should be required for high-impact or irreversible operations, security exceptions, and spending beyond approved limits unless an explicitly authorized policy governs them.

If approval is not received, the system should keep the protected action blocked while allowing unrelated, safe work to continue.

A complete approval workflow is a proposed production extension. The Master coordinates execution but does not replace human accountability.

## 19. Plan-versus-Delivered Reporting

The final report should compare the original plan with verified results.

It should identify:

- Tasks completed and verified.
- Tasks that failed or were rejected.
- Tasks that were retried or reassigned.
- Tasks blocked by unresolved dependencies.
- Expected artifacts that were not delivered.
- Verification outcomes and relevant failure reasons.

The report should not describe unverified work as completed.

## 20. Known Limitations

The current prototype has the following limitations:

1. Live-provider execution has not been demonstrated in this submission.
2. Plan parsing is deterministic and does not provide LLM-based task decomposition.
3. Verification is primarily deterministic rather than a comprehensive semantic correctness assessment.
4. Workspace and command guards are not equivalent to a hardened operating-system sandbox.
5. Automated Git conflict resolution is not implemented.
6. A complete human-approval workflow is not implemented.
7. Production-scale performance with twenty live accounts has not been measured.
8. Provider compliance depends on the specific integration method and applicable terms.

These limitations distinguish demonstrated functionality from future design proposals.

## 21. Production-Hardening Roadmap

A reasonable next phase would prioritize:

1. Stronger process and filesystem isolation.
2. Persistent task state and recovery after interruptions.
3. More robust quota-aware scheduling and bounded retry policies.
4. Independent artifact verification and automated test execution.
5. Git-based integration with conflict detection.
6. A risk-based human-approval workflow.
7. Centralized observability and cost tracking.
8. A review of provider terms and approved authentication methods.
9. More flexible, optionally LLM-assisted planning with explicit validation of generated tasks and dependencies.

## 22. Conclusion

The prototype demonstrates the core orchestration pattern: the plan parser converts supported written plans into tasks, the Master coordinates execution, Workers perform assigned work, and a Verification Gate checks deliverables before acceptance.

Its central design principle is that completion must be based on evidence, not merely on a Worker or Master claiming success. The next stage is to strengthen planning, isolation, verification, recovery, and approval controls before treating the system as production-ready.
