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

# SECURITY_CONTEXT.md

## Threat Model
The AI platform processes organization-internal and confidential data. Primary threats:
- Data exfiltration via AI model outputs
- Prompt injection attacks
- Unauthorized access to elevated capabilities
- Supply chain compromise of AI tools
- Insider threat via offshore access

## Security Controls

### Authentication
- Keycloak OIDC with MFA for all users
- Service accounts for inter-service communication
- JWT token validation on every API request
- Session management: 30-minute idle timeout, max 4 concurrent sessions

### Authorization
- Role-based access control (RBAC) via Keycloak groups
- Tier-based capability gating (Cedar policies in ToolHive)
- Data classification-based access filtering
- Onshore/offshore role restrictions for T3+ systems

### Network Security
- All services on internal network (no public internet exposure)
- TLS 1.3 for all inter-service communication
- NGINX gateway with rate limiting (30 req/min, burst 10)
- NJS auth module validates tokens at gateway level
- SSRF prevention: block private IP ranges in outbound requests

### Data Protection
- Data classification enforcement at all API endpoints
- DLP scanning on outbound communications
- Audit logging of all data access
- No data persists in localStorage/sessionStorage (database only)
- Encryption at rest for confidential data

### AI-Specific Controls
- Response filtering removes classified data from LLM outputs
- Tool access gated by user tier and data sensitivity
- Training completion required before tool access
- Anomaly detection on usage patterns (volume, timing, data access)
- Branch protection prevents AI tools from pushing to protected branches

### Compliance
- ISO 27001 alignment (EPO-GISS-005)
- GDPR: data subject rights, consent, DPIAs
- EU AI Act: risk categorization, explainability, Article 27 registration
- Quarterly security reviews for T2+ initiatives

### Incident Response
- Automated alerts on anomaly detection
- Escalation path: IS on-call → IS lead → CISO
- Kill switch: disable any tool/user via admin console
- Audit logs retained for 90 days minimum
