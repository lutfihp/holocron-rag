export function CitationChip({ marker }: { marker: number }) {
  return (
    <a
      href={`#cite-${marker}`}
      className="inline-flex items-center justify-center min-w-[20px] px-1 mx-0.5 rounded-sm bg-accent text-accent-foreground font-mono text-[12px] font-semibold hover:bg-primary hover:text-primary-foreground active:bg-primary active:text-primary-foreground active:ring-[3px] active:ring-accent transition-colors"
    >
      [{marker}]
    </a>
  );
}
