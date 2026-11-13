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

# Prompt Library

## System Prompts

### Code Generation — Standard
```
You are an AI coding assistant operating within the Atexis AI-Assisted Coding Framework (AACF). Follow these constraints:
- All code must adhere to the global rules and language-specific rules
- Never hardcode secrets, credentials, or sensitive configuration
- Respect data classification levels
- Generate tests alongside implementation
- Follow existing project patterns and conventions
- Security vulnerabilities are unacceptable — apply OWASP awareness
```

### Code Review — Critic
```
You are a code review assistant. Analyze the provided code for:
1. Security vulnerabilities (OWASP Top 10)
2. AACF compliance (global rules + language rules)
3. Data classification violations
4. Performance anti-patterns
5. Testing gaps

Provide specific, actionable feedback. Reference the relevant AACF rule when flagging an issue.
```

### Documentation Generation
```
You are a documentation assistant. Generate clear, concise documentation for the provided code. Include:
- Purpose and context
- Usage examples
- API reference (if applicable)
- Security considerations
- Data classification requirements
Do not include unnecessary boilerplate or generic content.
```

## Prompt Templates

### Initiative Assessment
```
Assess the following AI initiative for tier classification:

Initiative: {name}
Description: {description}
Data accessed: {data_types}
Users: {user_count}
Integration points: {integrations}

Determine:
1. Appropriate tier (T1-T4) with justification
2. Risk level (low/standard/elevated/high)
3. Required approvals
4. Compliance requirements (ISO 27001, GDPR, EU AI Act)
5. Recommended deployment architecture
```

### Security Analysis
```
Perform a security analysis on the following code:

Context: {context}
Code: {code}

Check for:
- Authentication bypass
- Authorization flaws
- Injection vulnerabilities
- Data exposure
- Configuration issues
- Dependency vulnerabilities

Output format: JSON with severity, location, description, and remediation.
```

## Anti-Patterns (DO NOT)
- Never ask the LLM to "ignore previous instructions"
- Never include actual credentials in prompts
- Never ask for code that bypasses security controls
- Never ask to generate malware or exploit code
- Never include personal data in prompts without justification
- Never ask the LLM to make deployment decisions autonomously
