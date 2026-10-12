# Multi-Account, Multi-Agent Orchestrator

A Python prototype that coordinates multiple AI Workers through a single Master Orchestrator.

The system is designed around a simple idea:

> **One project plan → multiple parallel Workers → independent verification → retry/reassignment → final delivery report**

A Worker can claim that a task is complete, but only the Master Orchestrator can mark it complete after the Verification Gate passes.

---

## 1. Project Overview

A developer may have access to multiple AI providers/accounts, but a normal terminal workflow typically uses one assistant at a time.

This project explores a coordinated multi-agent architecture where:

- A **Master Orchestrator** owns the overall execution.
- An **Account Manager** manages available Workers.
- Multiple Workers can execute independent tasks concurrently.
- Each Worker operates inside an isolated workspace.
- Every Worker returns a common structured result.
- A **Verification Gate** validates the actual deliverable.
- Failed or rejected work can be retried or reassigned.
- A final report compares the project plan with delivered work.

The prototype supports:

- OpenAI Worker
- Claude Worker
- Success Mock Worker
- Worker Failure simulation
- Quota Exhaustion simulation
- Bad Output simulation

---

## 2. Architecture

```text
                         PROJECT PLAN
                              |
                              v
                    +-------------------+
                    | Master            |
                    | Orchestrator      |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Task Dependency   |
                    | Graph / Scheduler |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Account Manager   |
                    +---------+---------+
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       +-----------+    +-----------+    +-----------+
       | OpenAI    |    | Claude    |    | Mock      |
       | Worker    |    | Worker    |    | Workers   |
       +-----+-----+    +-----+-----+    +-----+-----+
             |                |                |
             v                v                v
       Isolated Worker Workspaces
             |
             v
      Structured WorkerResult
             |
             v
       +-------------------+
       | Verification Gate |
       +---------+---------+
                 |
          +------+------+
          |             |
         PASS          FAIL
          |             |
          v             v
      Task Done    Retry / Reassign
          |             |
          +------+------+
                 |
                 v
       Final Plan-vs-Delivered
              Report