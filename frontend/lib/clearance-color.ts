import { Clearance } from "@/lib/types/chat";

export function clearanceBadgeClasses(c: Clearance): string {
  switch (c) {
    case "public":
      return "bg-public text-public-foreground border-public-border";
    case "restricted":
      return "bg-restricted text-restricted-foreground border-restricted-border";
    case "secret":
      return "bg-secret text-secret-foreground border-secret-border";
    case "top_secret":
      return "bg-top-secret text-top-secret-foreground border-top-secret-border";
  }
}

export function clearanceLabel(c: Clearance): string {
  switch (c) {
    case "public": return "PUBLIC";
    case "restricted": return "RESTRICTED";
    case "secret": return "SECRET";
    case "top_secret": return "TOP SECRET";
  }
}

/** Dot color for the badge's leading dot. Matches the fg color for contrast. */
export function clearanceDotClasses(c: Clearance): string {
  switch (c) {
    case "public": return "bg-public-foreground";
    case "restricted": return "bg-restricted-foreground";
    case "secret": return "bg-secret-foreground";
    case "top_secret": return "bg-top-secret-foreground";
  }
}
