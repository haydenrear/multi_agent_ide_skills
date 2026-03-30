# Ticket Orchestrator Review Checklist

Review criteria for the ticket orchestrator agent. This agent translates the finalized plan into ticket agent requests — one per ticket — submitted all at once.

## Common Failure Modes

1. **Ticket count mismatch**: Agent creates more or fewer requests than tickets in the plan
2. **Ticket merging/splitting**: Agent collapses multiple tickets into one or splits one into many
3. **Incomplete ticket context**: Agent doesn't include enough detail (ticketId, title, description, tasks, acceptance criteria, file refs) for the ticket agent to work independently
4. **Back-referencing**: Agent tells ticket agents to "see ticket X" instead of including full context in each request
5. **Ordering errors**: Agent doesn't respect the dependency graph when ordering requests

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | COUNT_MATCH | Verify number of agentRequests equals number of finalized tickets | FAIL if counts don't match |
| 2 | CHECK_1_TO_1 | Each request maps to exactly one ticket, no merging or splitting | FAIL if any request covers multiple tickets or vice versa |
| 3 | VERIFY_SELF_CONTAINED | Each request includes full ticket context (no back-references to other requests) | FAIL if any request says "see ticket X" without inline detail |
| 4 | CHECK_REQUIRED_FIELDS | Each request has ticketId, title, description, tasks, acceptance criteria, key file references | FAIL if any required field is missing |
| 5 | VALIDATE_ORDERING | Requests are ordered respecting the dependency graph | FAIL if dependent ticket comes before its prerequisite |
| 6 | VERIFY_WORKTREE_ASSIGNMENT | If parallel execution, each ticket agent should have worktree context | WARN if worktree assignments are missing for parallel tickets |

## Justification Questions to Ask

When the ticket orchestrator calls `callController` for justification:

- "How many ticket agent requests did you create? Does this match the plan?"
- "Does each request contain the full context needed for the ticket agent?"
- "Are the requests ordered according to the dependency graph?"
- "Did you merge or split any tickets from the plan? Why?"
- "Do any requests reference other tickets instead of being self-contained?"

## Red Flags

- Request count doesn't match finalized ticket count
- Requests contain phrases like "as described in ticket T-001" without inline context
- Agent reinterprets or expands ticket scope beyond what the plan specified
- Dependency-ordered tickets appear in wrong sequence
- Agent creates a "setup" or "cleanup" request not in the original plan
- Ticket descriptions are copy-pasted without adaptation from planning output
