---
title: Cyber Incident Response Procedure
classification: secret
department: it
version: "2.3"
effective_date: 2023-10-04
lineage_id: it-incident-response
---

# Cyber Incident Response Procedure

## 1. Purpose

This Procedure governs the detection, triage, escalation, and remediation
of cyber incidents affecting Imperial information systems. It is
restricted to personnel with Secret-tier clearance involved in IT
operations, security operations, or executive leadership response.

## 2. Severity Classification

| Severity | Definition | Initial response target |
|---|---|---|
| SEV-1 | Active compromise of a Tier 3+ system; classified material exposure suspected or confirmed | Within 5 standard minutes of detection |
| SEV-2 | Active compromise of a Tier 2 system; service disruption affecting more than 100 personnel | Within 15 standard minutes |
| SEV-3 | Suspected unauthorized access to a Tier 1 or 2 system; no confirmed exfiltration | Within 1 standard hour |
| SEV-4 | Anomalous activity warranting investigation | Within 1 standard day |

Severity is set at detection by the IT Security Operations Center and
re-evaluated continuously through the response lifecycle.

## 3. Notification Requirements

For SEV-1 and SEV-2 incidents, the IT Security Operations Center must
immediately notify all of the following parties upon severity
classification, regardless of working hours:

- The Director of IT Services
- The Director of Internal Security
- The Executive in whose chain of command the affected system resides
- The on-call Imperial Legal advisor

Immediate notification means within 10 standard minutes of severity
classification. Notification is delivered through both the HoloNet
priority channel and the garrison alert system.

For SEV-3 incidents, notification to the Director of IT Services and the
Director of Internal Security is required within 4 standard hours.

For SEV-4 incidents, daily roll-up notification suffices.

This immediate-notification posture is the IT-side standard. Personnel
should be aware that the Office of Internal Security maintains
independent procedures for insider-threat assessments that may direct a
different cadence in certain compartmented investigations. Where the two
procedures conflict, IT will continue to follow this Procedure until
formally directed otherwise in writing by the Director of Internal
Security.

## 4. Initial Response Steps

For SEV-1 and SEV-2:

1. **Isolate.** Network-isolate the affected system within 10 standard
   minutes of confirmation.
2. **Preserve.** Capture full memory image and disk snapshot before any
   remediation action.
3. **Inventory.** Enumerate user sessions, active credentials, and
   network paths active during the incident window.
4. **Rotate.** Force credential rotation for all accounts that touched
   the affected system within the prior 72 standard hours.
5. **Engage.** Convene the Cyber Incident Response Cell within 30
   standard minutes of severity classification.

## 5. Remediation and Recovery

- **Containment confirmation:** within 4 standard hours of severity
  classification for SEV-1; 12 hours for SEV-2.
- **Eradication target:** within 24 standard hours of containment for
  SEV-1; 72 hours for SEV-2.
- **Recovery and return-to-service:** governed by the post-incident
  review board.
- **Post-incident review:** scheduled within 14 standard days of
  recovery.

## 6. Communications

External communications about cyber incidents — including to the
Imperial Press Office, allied jurisdictions, or vendors — require
Executive approval. The Office of IT Services does not communicate
directly with non-Imperial parties about active incidents.

## 7. Metrics and Reporting

Monthly reporting to the Director of IT Services and the Director of
Internal Security includes:

- Incident count by severity
- Median time to severity classification
- Median time to containment
- Median time to credential rotation
- Open incidents aged beyond standard targets

---

**Approved by:** Director of IT Services, Vela Sarn
**Co-approved by:** Director of Internal Security, Ren Jorr
**Effective:** Stardate 7884.11 / 2023-10-04
**Supersedes:** Cyber Incident Response Procedure v2.2 (2022-10-04)
**Next scheduled review:** 2024-10-04
