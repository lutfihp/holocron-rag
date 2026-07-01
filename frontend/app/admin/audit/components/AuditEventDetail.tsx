import type { AuditEvent } from "@/lib/types/audit";

export function AuditEventDetail({ event }: { event: AuditEvent }) {
  const typeBadge =
    event.event_type === "refusal"
      ? "bg-restricted text-restricted-foreground"
      : event.event_type === "response"
      ? "bg-public text-public-foreground"
      : "bg-muted text-muted-foreground";
  return (
    <div className="border border-border rounded-md p-3 bg-card space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className={`uppercase font-semibold px-2 py-0.5 rounded-sm ${typeBadge}`}>
          {event.event_type}
        </span>
        <span className="font-mono text-muted-foreground">{event.created_at}</span>
      </div>
      {event.query_text && (
        <p className="text-sm">
          <span className="font-semibold">Query:</span> {event.query_text}
        </p>
      )}
      {event.response_text && (
        <p className="text-sm">
          <span className="font-semibold">Response:</span> {event.response_text}
        </p>
      )}
      {event.refusal_ref && (
        <p className="text-sm">
          <span className="font-semibold">Refusal ref:</span>{" "}
          <code className="bg-muted px-1 rounded-sm">{event.refusal_ref}</code>
        </p>
      )}
      {event.retrieved_ids.length > 0 && (
        <p className="text-xs text-muted-foreground">
          retrieved: {event.retrieved_ids.length} | withheld:{" "}
          {event.withheld_ids.length}
        </p>
      )}
      {event.conflicts_found && event.conflicts_found.count > 0 && (
        <p className="text-xs">
          <span className="font-semibold">Conflicts:</span>{" "}
          {event.conflicts_found.subjects.join(", ")}
        </p>
      )}
      {event.latency_ms !== null && (
        <p className="text-xs text-muted-foreground">latency: {event.latency_ms} ms</p>
      )}
    </div>
  );
}
