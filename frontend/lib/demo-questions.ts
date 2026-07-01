export interface DemoQuestion {
  category: string;
  question: string;
  /** lucide-react icon name — resolved via lucide dynamic import at the render site. */
  icon: "shield-check" | "git-compare-arrows" | "lock" | "message-square" | "scroll-text" | "scale";
}

/** Department-keyed suggestions. First department in a user's list wins;
 * fallback used when the department has no map entry. */
const MAP: Record<string, DemoQuestion[]> = {
  hr: [
    { category: "Compliance", question: "What's the dress-code policy for off-base events?", icon: "shield-check" },
    { category: "Compliance", question: "What is the maximum age for recruitment?", icon: "scroll-text" },
    { category: "Compliance", question: "What is the remote-work policy?", icon: "message-square" },
  ],
  engineering: [
    { category: "Conflict detection", question: "What is the reactor coolant shutdown sequence?", icon: "git-compare-arrows" },
    { category: "Reference", question: "What is the reactor emergency protocol?", icon: "scroll-text" },
    { category: "Reference", question: "Who signs off on hardware change orders?", icon: "message-square" },
  ],
  security: [
    { category: "Clearance", question: "What sources are restricted for my clearance?", icon: "lock" },
    { category: "Compliance", question: "What is the insider threat escalation process?", icon: "shield-check" },
    { category: "Compliance", question: "What are the access audit cadences?", icon: "scroll-text" },
  ],
  fleet_operations: [
    { category: "Reference", question: "What is the fleet deployment sign-off chain?", icon: "scroll-text" },
    { category: "Compliance", question: "What sources are restricted for my clearance?", icon: "lock" },
    { category: "Conflict detection", question: "What is the correct coolant shutdown sequence?", icon: "git-compare-arrows" },
  ],
  procurement: [
    { category: "Conflict detection", question: "What is the credit-threshold for supplier orders?", icon: "git-compare-arrows" },
    { category: "Compliance", question: "What is the vendor onboarding sequence?", icon: "scroll-text" },
    { category: "Reference", question: "What is the current procurement approval matrix?", icon: "message-square" },
  ],
  it: [
    { category: "Reference", question: "What is the acceptable-use policy?", icon: "scroll-text" },
    { category: "Compliance", question: "What is the access provisioning workflow?", icon: "shield-check" },
    { category: "Reference", question: "What is the incident response timing?", icon: "message-square" },
  ],
};

const FALLBACK: DemoQuestion[] = [
  { category: "Compliance", question: "What's the dress-code policy for off-base events?", icon: "shield-check" },
  { category: "Conflict detection", question: "What is the correct reactor shutdown sequence?", icon: "git-compare-arrows" },
  { category: "Clearance", question: "What sources are restricted for my clearance?", icon: "lock" },
];

/** Pick a demo question set. Takes the first department that maps; falls back
 * to the generic set. Returns exactly 3 items. */
export function getDemoQuestions(departments: readonly string[]): DemoQuestion[] {
  for (const dept of departments) {
    const q = MAP[dept];
    if (q) return q;
  }
  return FALLBACK;
}
