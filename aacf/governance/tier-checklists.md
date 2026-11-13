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

# Tier Governance Checklists

## T1 — Self-Service (IDE Tools)

### Before Use
- [ ] Tool is in the approved AI Tool Registry
- [ ] User has completed required training module
- [ ] Tool operates in air-gapped mode (no internet access)
- [ ] No confidential data is processed

### During Use
- [ ] Code generated respects AACF global rules
- [ ] No sensitive data is passed as prompts
- [ ] Outputs are reviewed before committing

### Compliance
- [ ] No additional review required
- [ ] Usage logged via IDE telemetry

---

## T2 — IS-Approved (Internal Tools)

### Before Deployment
- [ ] Initiative registered in IdAI with business justification
- [ ] IS review completed and approved
- [ ] Risk assessment classifies as LOW or STANDARD
- [ ] Training completed for all intended users
- [ ] Tool registered in AI Tool Registry

### During Operation
- [ ] Running on shared VM (IT-provisioned)
- [ ] Audit logging active
- [ ] Rate limiting configured
- [ ] Data classification: Internal or below only
- [ ] Monthly usage review scheduled

### Compliance
- [ ] ISO 27001 controls mapped
- [ ] GDPR: no personal data without DPIA
- [ ] Quarterly review flagged in IdAI

---

## T3 — IS + Data (Data Warehouse Access)

### Before Deployment
- [ ] Initiative registered in IdAI with detailed justification
- [ ] IS review + Data team review completed
- [ ] Risk assessment classifies as ELEVATED or below
- [ ] Data classification review: which DW tables accessed?
- [ ] DPIA completed if personal data involved
- [ ] Training completed (including data handling module)
- [ ] Access restricted to onshore team only

### During Operation
- [ ] Running on dedicated VM with DW access
- [ ] Column-level access control configured
- [ ] All queries logged with full audit trail
- [ ] DLP scanning on all outputs
- [ ] Data export restrictions enforced
- [ ] Weekly access review by data owner

### Compliance
- [ ] ISO 27001 full compliance
- [ ] GDPR: DPIA approved, consent verified
- [ ] EU AI Act: risk category determined
- [ ] Quarterly IS review + annual penetration test

---

## T4 — Production (IS + IT Joint)

### Before Deployment
- [ ] Full lifecycle review by IS, IT, and business owner
- [ ] Risk assessment: HIGH risk accepted with mitigations
- [ ] Production architecture review completed
- [ ] Disaster recovery plan documented and tested
- [ ] Security penetration test passed
- [ ] Data classification: all levels with appropriate controls
- [ ] Onshore-only development and administration
- [ ] Full DPIA, EU AI Act Article 27 registration

### During Operation
- [ ] Running on production infrastructure (Hyper-V or cloud)
- [ ] 24/7 monitoring with automated alerting
- [ ] Failover and redundancy configured
- [ ] Backup schedule verified
- [ ] Incident response plan active
- [ ] Change management process for all updates
- [ ] Real-time anomaly detection

### Compliance
- [ ] ISO 27001 full certification scope
- [ ] GDPR full compliance with documented DPO oversight
- [ ] EU AI Act: high-risk registration complete
- [ ] Monthly IS review + quarterly external audit
- [ ] DR test executed semi-annually
