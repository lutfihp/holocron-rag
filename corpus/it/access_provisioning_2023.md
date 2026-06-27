---
title: System Access Provisioning Standard
classification: restricted
department: it
version: "4.1"
effective_date: 2023-05-22
lineage_id: it-access-provisioning
---

# System Access Provisioning Standard

## 1. Purpose

This Standard defines how system access scopes are granted, modified, and
revoked across Imperial information systems. It applies to all Imperial
personnel and to authorized vendor service accounts. It is restricted to
personnel involved in access administration, compliance, and security
operations.

## 2. Provisioning Tiers

Imperial information systems are organized into four access tiers,
mapped to the standard classification ladder.

| Tier | Map to classification | Standard provisioning latency |
|---|---|---|
| Tier 1 (general) | public | 1 standard day |
| Tier 2 (operational) | restricted | 5 standard days |
| Tier 3 (sensitive) | secret | 14 standard days |
| Tier 4 (compartmented) | top_secret | 30+ standard days |

Tier 4 access is administered under separate compartment-specific
standards not within scope of this document.

## 3. Standard Provisioning Workflow

All non-emergency access requests follow the seven-step workflow:

1. **Request initiation.** Submitted by the personnel member's direct
   supervisor in the Imperial Personnel Information System.
2. **Role justification.** Free-text justification mapping the request to
   a specific duty assignment.
3. **Supervisor concurrence.** Required for all tiers above Tier 1.
4. **Department approval.** Director-level approval for Tier 3+.
5. **Security pre-screen.** Conducted by the Office of Internal Security
   for Tier 3+; verifies clearance posture matches request.
6. **Provisioning execution.** Performed by the IT Provisioning Team.
7. **Notification and acknowledgment.** Personnel member acknowledges
   receipt and reviews scope for accuracy.

## 4. Emergency Provisioning

Emergency provisioning is permitted when an operational requirement makes
the standard workflow infeasible.

- **Authorized approvers:** Director tier and above, in the requesting
  personnel member's chain of command.
- **Maximum duration:** 72 standard hours, non-renewable. Conversion to
  permanent access requires the standard workflow.
- **Documentation:** the approving Director files a written
  justification within 24 standard hours of provisioning.
- **Audit:** all emergency provisioning is reviewed monthly by the IT
  Provisioning Team and quarterly by the Office of Internal Security.

## 5. Standing Roles and Templates

To reduce provisioning latency, the IT Provisioning Team maintains
standard role templates aligned to common positions:

| Template | Tier | Common positions covered |
|---|---|---|
| garrison-employee | 1 | General duty Employee |
| garrison-manager | 2 | Garrison-tier Manager |
| engineering-restricted | 2 | Engineering Employee, Manager |
| logistics-restricted | 2 | Procurement, Fleet Operations |
| security-sensitive | 3 | Office of Internal Security |
| executive-sensitive | 3 | Director-tier and above |

Template grants are pre-approved up to the template's tier; deviations
require the standard workflow.

## 6. Reviews and Revocation

- **Quarterly entitlement review:** every access scope is reviewed by the
  IT Provisioning Team for continued necessity.
- **Annual access certification:** the personnel member's Manager
  re-certifies each Tier 2+ scope.
- **Separation revocation:** all access revoked within 30 standard
  minutes of confirmed separation.
- **Reassignment revocation:** scopes tied to the prior assignment are
  revoked within 5 standard days of effective reassignment.

## 7. Vendor Service Accounts

Vendor service accounts (used by approved external contractors) are
managed under the same tiering. Additional requirements:

- **Sponsoring Director:** must be named on the request
- **Expiration:** maximum 12 standard months, renewal required
- **Activity logging:** enhanced logging at all tiers
- **Out-of-band authentication:** required at Tier 2 and above

## 8. Metrics

The IT Provisioning Team reports the following monthly to the Director
of IT Services:

- Median provisioning latency by tier
- Emergency provisioning count and conversion rate to permanent access
- Open access requests aged beyond standard latency
- Revocation latency at separation

---

**Approved by:** Director of IT Services, Vela Sarn
**Co-approved by:** Director of Internal Security, Ren Jorr
**Effective:** Stardate 7843.18 / 2023-05-22
**Supersedes:** System Access Provisioning Standard v4.0 (2021-05-22)
**Next scheduled review:** 2025-05-22
