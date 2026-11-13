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

# PROJECT_CONTEXT.md

## Organization
Atexis — IT department managing AI-assisted development platform.

## Platform Overview
The AI Management Platform (IdAI) provides centralized governance, deployment, and monitoring for all AI-assisted development initiatives within the organization.

## Key Systems
- **Admin Console**: Central management UI (React + FastAPI)
- **IdAI App**: Initiative governance frontend (React + shadcn/ui)
- **MCP Platform**: Model Context Protocol servers for tool integration
- **ToolHive**: Tool gateway with Cedar policy engine
- **Keycloak**: Identity and access management
- **Inference Stack**: Local LLM inference (Ollama + vLLM on RTX 4090)

## Tier System
- **T1 (Self-Service)**: IDE coding assistants, no sensitive data
- **T2 (IS-Approved)**: Internal tools, shared infrastructure
- **T3 (IS + Data)**: Data warehouse access, dedicated VMs
- **T4 (IS + IT + Production)**: Production systems, joint deployment

## Data Classification
- **Public**: No restrictions
- **Internal**: Organization-internal only
- **Confidential**: Need-to-know basis, encrypted
- **Strictly Confidential**: Maximum controls, isolated processing

## Infrastructure
- **APP024**: Primary AI inference server (RTX 4090, 60GB RAM, Ubuntu 24.04)
- **Docker**: All services containerized
- **Networking**: Internal network only, HTTPS/TLS everywhere
- **Auth**: Keycloak OIDC with role-based access

## Teams
- **IS (Information Security)**: Policy, compliance, reviews
- **IT Infrastructure**: Provisioning, networking, monitoring
- **Development**: Building and deploying AI tools
- **Business Units**: Consumers of AI capabilities
