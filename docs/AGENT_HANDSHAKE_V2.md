# AgentHandshakeV2 API Documentation

## Overview

AgentHandshakeV2 is ConComplyAi's production REST API for multi-agent compliance workflows. It provides cryptographic audit chains with SHA-256 proof hashing and supports integration with Procore, Excel/CSV uploads, and email forwarding.

**Version:** 2.0  
**Base URL:** `https://api.concomplai.com/v2`  
**Protocol:** REST/JSON  
**Authentication:** Bearer token (contact support@concomplai.com)

---

## Key Features

- ✅ **Immediate AuditProof Hash Return** - Get SHA-256 hash instantly for tracking
- ✅ **Multi-Source Integration** - Procore webhooks, CSV drops, email forwarding
- ✅ **Async Processing** - Non-blocking document validation
- ✅ **Cryptographic Audit Trail** - Immutable decision chain per NYC Local Law 144
- ✅ **Production-Grade Versioning** - Handshake version 2.0 with backward compatibility

---

## Endpoints

### POST /handshake

Create an AgentHandshakeV2 for compliance document processing.

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_system` | enum | Yes | PROCORE_COI_PULL, EXCEL_CSV_DROP, EMAIL_FORWARD, MANUAL_UPLOAD |
| `project_id` | string | Yes | Unique project identifier |
| `document_type` | string | No | Document type (default: COI) |
| `contractor_name` | string | No | Contractor/company name |
| `document_url` | string | Conditional | URL to document (required if no `documents`) |
| `documents` | array | Conditional | Batch documents (required if no `document_url`) |
| `permit_number` | string | No | NYC DOB permit number |
| `metadata` | object | No | Additional context |
| `target_agent` | enum | No | Target agent (default: Guard) |

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether handshake was accepted |
| `message` | string | Human-readable status |
| `audit_proof_hash` | string | SHA-256 hash for tracking |
| `handshake_id` | string | Unique handshake identifier |
| `handshake_version` | string | Protocol version (2.0) |
| `project_id` | string | Project identifier |
| `source_system` | enum | Source system |
| `target_agent` | enum | Agent assigned |
| `timestamp` | datetime | Creation timestamp |
| `estimated_processing_time_seconds` | int | Est. completion time |
| `documents_queued` | int | Number of docs queued |

---

## Integration Examples

### Example 1: Procore Webhook Integration

**Procore → ConComplyAi Flow:**
1. Contractor uploads COI to Procore
2. Procore sends webhook to ConComplyAi
3. ConComplyAi creates handshake and returns audit proof hash
4. Guard agent validates COI asynchronously
5. Results posted back to Procore via their API

**Request:**
```json
{
  "source_system": "PROCORE_COI_PULL",
  "project_id": "PROCORE-12345",
  "document_type": "COI",
  "contractor_name": "ABC Construction Corp",
  "document_url": "https://procore.com/documents/abc_coi_2026.pdf",
  "permit_number": "121234567",
  "metadata": {
    "procore_project_id": "12345",
    "procore_company_id": "678",
    "procore_document_id": "doc-789"
  },
  "target_agent": "Guard"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Handshake accepted. Document queued for Guard agent processing.",
  "audit_proof_hash": "a3f7c9e1d5b2f8a4c6e9d3b7f1a5c8e2d4b6f9a3c5e7d1b3f5a7c9e1d3b5f7",
  "handshake_id": "HANDSHAKE-PROCORE_COI_PULL-20260206143000",
  "handshake_version": "2.0",
  "project_id": "PROCORE-12345",
  "source_system": "PROCORE_COI_PULL",
  "target_agent": "Guard",
  "timestamp": "2026-02-06T14:30:00.000Z",
  "estimated_processing_time_seconds": 30,
  "documents_queued": 1
}
```

---

### Example 2: Excel/CSV Batch Upload

**CSV → ConComplyAi Flow:**
1. GC exports contractor list to CSV
2. CSV uploaded to ConComplyAi portal
3. System creates handshakes for each row
4. All COIs processed through Guard agent
5. Results exported as report

**CSV Format:**
```csv
contractor_name,document_path,permit_number,address
ABC Construction,/uploads/abc_coi.pdf,121234567,"123 Main St, Manhattan"
XYZ Builders,/uploads/xyz_coi.pdf,121234568,"456 Park Ave, Brooklyn"
DEF Concrete,/uploads/def_coi.pdf,121234569,"789 Broadway, Queens"
```

**Request (for each row):**
```json
{
  "source_system": "EXCEL_CSV_DROP",
  "project_id": "CSV-BATCH-2026-02-06-001",
  "document_type": "COI",
  "contractor_name": "ABC Construction",
  "document_url": "/uploads/abc_coi.pdf",
  "permit_number": "121234567",
  "metadata": {
    "batch_id": "2026-02-06-001",
    "address": "123 Main St, Manhattan",
    "csv_row_number": 1
  },
  "target_agent": "Guard"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Handshake accepted. Document queued for Guard agent processing.",
  "audit_proof_hash": "b4c8d2e6f0a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3",
  "handshake_id": "HANDSHAKE-EXCEL_CSV_DROP-20260206143015",
  "handshake_version": "2.0",
  "project_id": "CSV-BATCH-2026-02-06-001",
  "source_system": "EXCEL_CSV_DROP",
  "target_agent": "Guard",
  "timestamp": "2026-02-06T14:30:15.000Z",
  "estimated_processing_time_seconds": 30,
  "documents_queued": 1
}
```

---

### Example 3: Complete Scout → Guard → Fixer Chain

This example shows the full multi-agent handshake chain for a high-value opportunity discovered by Scout.

**Step 1: Scout Discovers Opportunity**
```json
{
  "agent": "Scout",
  "handshake": {
    "handshake_version": "2.0",
    "source_agent": "Scout",
    "target_agent": "Guard",
    "project_id": "SCOUT-121234567-20260206",
    "source_system": "API_DIRECT",
    "decision_hash": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
    "parent_handshake_id": null,
    "transition_reason": "opportunity_discovered",
    "timestamp": "2026-02-06T14:30:00.000Z",
    "metadata": {
      "permit_number": "121234567",
      "job_type": "NB",
      "estimated_project_cost": 5000000,
      "opportunity_score": 0.85
    }
  }
}
```

**Step 2: Guard Validates COI**
```json
{
  "agent": "Guard",
  "handshake": {
    "handshake_version": "2.0",
    "source_agent": "Guard",
    "target_agent": "Fixer",
    "project_id": "SCOUT-121234567-20260206",
    "source_system": "API_DIRECT",
    "decision_hash": "2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3",
    "parent_handshake_id": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
    "transition_reason": "deficiency_found",
    "timestamp": "2026-02-06T14:30:15.000Z",
    "metadata": {
      "compliance_status": "PENDING_FIX",
      "deficiencies": [
        "Missing Waiver of Subrogation",
        "GL Aggregate $2,000,000 below minimum $4,000,000"
      ],
      "citations": [
        "NYC SCA Bulletin 2024-03",
        "AIA A201-2017 §11.1"
      ]
    }
  }
}
```

**Step 3: Fixer Drafts Remediation Email**
```json
{
  "agent": "Fixer",
  "handshake": {
    "handshake_version": "2.0",
    "source_agent": "Fixer",
    "target_agent": null,
    "project_id": "SCOUT-121234567-20260206",
    "source_system": "API_DIRECT",
    "decision_hash": "3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4",
    "parent_handshake_id": "2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3",
    "transition_reason": "remediation_email_drafted",
    "timestamp": "2026-02-06T14:30:30.000Z",
    "metadata": {
      "email_subject": "COI Update Required: ABC Construction - DOB Job #121234567",
      "broker_name": "XYZ Insurance Agency",
      "deficiency_count": 2,
      "correction_link": "https://concomplai.com/upload?doc_id=COI-20260206-1234"
    }
  }
}
```

**Audit Chain Verification:**
```
Scout (1a2b...) → Guard (2b3c...) → Fixer (3c4d...)
                 ↓                ↓
         parent_handshake_id  parent_handshake_id
```

Each handshake's `parent_handshake_id` points to the previous agent's `decision_hash`, creating an immutable audit trail.

---

## Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | Success | Handshake created successfully |
| 400 | Bad Request | Invalid request payload |
| 401 | Unauthorized | Missing or invalid auth token |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal server error |

---

## Rate Limits

- **Standard Tier:** 100 requests/minute
- **Premium Tier:** 500 requests/minute
- **Enterprise Tier:** Custom limits

Contact support@concomplai.com to upgrade.

---

## Authentication

All requests require a Bearer token in the Authorization header:

```bash
curl -X POST https://api.concomplai.com/v2/handshake \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @request.json
```

---

## Webhooks

Configure webhook URLs to receive processing results:

```json
{
  "webhook_url": "https://your-system.com/concomplai/results",
  "events": ["guard.completed", "fixer.completed"],
  "secret": "your_webhook_secret"
}
```

Webhook payloads include:
- `audit_proof_hash` - For correlation
- `agent_name` - Which agent completed
- `result` - Processing results
- `timestamp` - Completion time

---

## Support

**Documentation:** https://docs.concomplai.com  
**API Status:** https://status.concomplai.com  
**Support:** support@concomplai.com  
**Sales:** sales@concomplai.com  

**GitHub:** https://github.com/NickAiNYC/ConComplyAi  
**Issues:** https://github.com/NickAiNYC/ConComplyAi/issues
