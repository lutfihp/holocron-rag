/** Two-letter initials from a dotted username like `executive.fleet` → `EF`. */
export function initials(username: string): string {
  const [head, tail] = username.split(".");
  const first = head?.[0] ?? "";
  const second = tail?.[0] ?? head?.[1] ?? "";
  return (first + second).toUpperCase() || "?";
}
