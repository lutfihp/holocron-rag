import type { AuditEvent } from "@/lib/types/audit";

export function AuditEventDetail({ event }: { event: AuditEvent }) {
  const typeBadge =
    event.event_type === "refusal"
      ? "bg-amber-100 text-amber-900"
      : event.event_type === "response"
      ? "bg-emerald-100 text-emerald-900"
      : "bg-gray-100 text-gray-700";
  return (
    <div className="border rounded p-3 bg-white space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className={`uppercase font-semibold px-2 py-0.5 rounded ${typeBadge}`}>
          {event.event_type}
        </span>
        <span className="font-mono text-gray-500">{event.created_at}</span>
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
          <code className="bg-gray-100 px-1 rounded">{event.refusal_ref}</code>
        </p>
      )}
      {event.retrieved_ids.length > 0 && (
        <p className="text-xs text-gray-600">
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
        <p className="text-xs text-gray-600">latency: {event.latency_ms} ms</p>
      )}
    </div>
  );
}
