/** The mark reads as a shelf seen in perspective — three bars receding. */
export function Mark({ className = "size-7" }: { className?: string }) {
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-[0.5rem] bg-[linear-gradient(135deg,var(--agent-1),var(--agent-2))] ${className}`}
    >
      <svg viewBox="0 0 24 24" fill="none" className="size-[58%]" aria-hidden="true">
        <path d="M4 8.5 12 5l8 3.5-8 3.5-8-3.5Z" fill="white" fillOpacity=".95" />
        <path d="M4 13l8 3.5 8-3.5" stroke="white" strokeOpacity=".7" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M4 17.5 12 21l8-3.5" stroke="white" strokeOpacity=".45" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}
