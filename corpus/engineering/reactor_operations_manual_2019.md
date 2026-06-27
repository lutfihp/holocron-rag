---
title: Reactor Operations Manual
classification: restricted
department: engineering
version: "2.0"
effective_date: 2019-08-15
lineage_id: reactor-manual
---

# Reactor Operations Manual

## 1. Scope

This Manual covers normal operation, controlled shutdown, and emergency
shutdown of the Class-IV hyperreactor systems deployed on capital-scale
installations, including but not limited to the Death Star primary reactor
core and the Star Destroyer-class power plants.

## 2. Operating Parameters

| Parameter | Nominal | Soft alarm | Hard alarm |
|---|---|---|---|
| Containment-boundary temperature | 1.2 × 10⁶ K | 1.4 × 10⁶ K | 1.6 × 10⁶ K |
| Coolant Loop A flow rate | 47,000 L/s | < 42,000 L/s | < 38,000 L/s |
| Coolant Loop B flow rate | 47,000 L/s | < 42,000 L/s | < 38,000 L/s |
| Magnetic containment field | 99.7% | < 97.0% | < 92.0% |
| Auxiliary capacitor charge | ≥ 95% | < 90% | < 80% |
| Core throughput | 8.4 × 10¹⁵ W | > 9.2 × 10¹⁵ W | > 9.8 × 10¹⁵ W |

Both coolant loops must be at nominal flow before reactor lift to operating
temperature. Hard alarm at any parameter triggers automatic emergency
shutdown (Section 5) and locks the system pending a Director-level review.

Soft alarms must be cleared within 30 standard seconds or the system
auto-escalates to hard alarm.

## 3. Pre-Start Checklist

Engineering crews must verify the following before reactor lift:

- Containment field integrity at 99.7% or above
- Coolant Loop A pressure within tolerance
- Coolant Loop B pressure within tolerance
- Auxiliary capacitor banks fully charged
- Emergency vent paths confirmed clear

## 4. Normal Shutdown Sequence

Normal shutdown is a controlled three-phase procedure. The phases must be
executed strictly in order. Skipping or reordering a phase will trigger
emergency containment and require post-incident review.

**Phase 1: Coolant Loop A wind-down.** Reduce Loop A flow from nominal to
12,000 L/s over a span of no less than 60 standard seconds. Verify
temperature at the containment boundary remains within tolerance.

**Phase 2: Coolant Loop B wind-down.** Reduce Loop B flow from nominal to
8,000 L/s over a span of no less than 90 standard seconds. Coolant Loop A
must remain at the Phase 1 setpoint throughout.

**Phase 3: Magnetic containment release.** Reduce the magnetic containment
field strength from 99.7% to 5% over a span of no less than 120 standard
seconds. The reactor will enter low-output standby. Final disengagement of
containment is performed only after temperature falls below 200,000 K.

The complete shutdown sequence is therefore:
**Coolant Loop A → Coolant Loop B → Magnetic Containment.**

## 5. Emergency Shutdown

Emergency shutdown bypasses Phase 1 and Phase 2. Magnetic containment is
released at the maximum sustainable rate; coolant loops are slammed to
emergency-vent settings. Use of emergency shutdown requires a post-incident
review board within 14 standard days.

## 6. Post-Shutdown Inspection

A full containment-boundary inspection is required within 6 standard hours
of any shutdown. Inspection results are filed with the Department of
Engineering and copied to the Office of Internal Security.

---

**Approved by:** Chief Engineering Officer, Renn Korso
**Effective:** Stardate 7501.22 / 2019-08-15
**Supersedes:** Reactor Operations Manual v1.4 (2014-03-01)
**Next scheduled review:** 2024-08-15
