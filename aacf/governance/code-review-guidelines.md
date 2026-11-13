<!-- ═══ AACF VERSION CHECK — AGENTS READ FIRST ═══
This file belongs to a downloaded snapshot of the ATEXIS AI Framework, version 2.0.0.
Before relying on it, verify the snapshot is current:
1. Call the aacf_fetch MCP tool (endpoint http://10.117.139.1:8200/mcp, streamable-http,
   header 'Authorization: Bearer <key>' or 'X-Api-Key: <key>'):
   aacf_fetch({"path": "VERSION"})
2. If the returned version differs from 2.0.0, this snapshot is OUTDATED. Fetch ALL
   framework files fresh via aacf_fetch (start with aacf_fetch({"path": "", "list_dir": true})
   and walk the tree), or ask the user to re-download the framework ZIP from the IdAI
   portal (/propose/framework). Do not mix files from different versions.
3. If you CANNOT reach the aacf_fetch MCP, you MUST tell the user: you cannot reach the
   AACF MCP and may be working with an outdated version of the framework. Then proceed
   with this file as-is.
Verify once per session, not per file.
═══ -->

# Code Review Guidelines

## Purpose
All T2+ code (human-written or AI-generated) must pass peer review before deployment. AI-generated code receives the same scrutiny as human-written code.

## Review Process

### Submitter Responsibilities
1. Self-review before requesting peer review
2. Ensure all tests pass locally
3. Include description of what changed and why
4. Flag any AI-generated sections explicitly
5. Confirm AACF compliance (rules, security, classification)

### Reviewer Responsibilities
1. Verify correctness (does it do what it claims?)
2. Check security (OWASP Top 10, input validation, auth)
3. Verify AACF compliance (follows templates and rules)
4. Check data handling (classification-appropriate)
5. Assess performance (no N+1 queries, no unbounded loops)
6. Validate tests (adequate coverage, meaningful assertions)

## Review Checklist

### Security
- [ ] No hardcoded credentials or secrets
- [ ] Input validation on all endpoints
- [ ] Authorization checks present
- [ ] No SQL injection vectors
- [ ] No XSS vectors
- [ ] Sensitive data not logged
- [ ] SSRF prevention for URL handling

### Code Quality
- [ ] Follows language-specific rules (.mdc files)
- [ ] Error handling present and appropriate
- [ ] No dead code or unused imports
- [ ] Naming is clear and consistent
- [ ] Complex logic has comments explaining WHY

### Data Handling
- [ ] Respects data classification level
- [ ] Personal data handling is GDPR-compliant
- [ ] Audit logging for data access
- [ ] No data leakage via error messages

### AI-Specific Checks
- [ ] AI-generated code has been understood (not blindly accepted)
- [ ] No hallucinated APIs or non-existent functions
- [ ] Dependencies actually exist and are compatible
- [ ] Business logic is correct (not just syntactically valid)

## Approval Requirements

| Tier | Approvers Required | Max Review Time |
|------|--------------------|-----------------|
| T1 | 0 (self-service) | N/A |
| T2 | 1 peer reviewer | 2 business days |
| T3 | 1 peer + 1 IS | 3 business days |
| T4 | 2 peers + 1 IS + 1 IT | 5 business days |

## Escalation
If a reviewer identifies a critical security issue:
1. Block the review immediately
2. Notify IS team
3. Do not merge until IS provides clearance
