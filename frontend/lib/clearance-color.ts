import { Clearance } from "@/lib/types/chat";

export function clearanceBadgeClasses(c: Clearance): string {
  switch (c) {
    case "public":
      return "bg-green-100 text-green-800 border-green-300";
    case "restricted":
      return "bg-amber-100 text-amber-800 border-amber-300";
    case "secret":
      return "bg-red-100 text-red-800 border-red-300";
    case "top_secret":
      return "bg-red-900 text-red-50 border-red-950";
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
