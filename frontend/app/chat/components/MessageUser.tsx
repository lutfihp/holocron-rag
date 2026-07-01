export function MessageUser({ query }: { query: string }) {
  return (
    <div className="self-end max-w-[75%] bg-foreground text-background rounded-lg rounded-br-md px-4 py-2 text-sm">
      {query}
    </div>
  );
}
