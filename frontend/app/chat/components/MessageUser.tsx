export function MessageUser({ query }: { query: string }) {
  return (
    <div className="self-end max-w-[75%] bg-slate-800 text-slate-100 rounded-2xl rounded-br-md px-4 py-2 text-sm">
      {query}
    </div>
  );
}
