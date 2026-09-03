"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// Hand-mapped element styling instead of the Tailwind typography plugin
// (not installed in this project) — keeps this to one small dependency
// (react-markdown + remark-gfm) rather than pulling in a whole prose
// stylesheet for what's mostly short product-shopping replies.
const components: Components = {
  p: (props) => <p className="mb-2 leading-relaxed last:mb-0" {...props} />,
  ul: (props) => <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0" {...props} />,
  ol: (props) => <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0" {...props} />,
  li: (props) => <li className="leading-relaxed" {...props} />,
  strong: (props) => <strong className="font-semibold text-foreground" {...props} />,
  a: (props) => (
    <a className="text-primary underline underline-offset-2" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  pre: (props) => <pre className="mb-2 overflow-x-auto rounded-md bg-muted p-2 text-xs last:mb-0" {...props} />,
  code: (props) => <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]" {...props} />,
  // The model sometimes writes ![Image](url) into its prose, which renders as
  // a full-width duplicate of a photo already shown in the product card.
  // Product imagery belongs to the gallery, so drop it here entirely.
  img: () => null,
  h1: (props) => <h3 className="mt-3 mb-1 text-base font-semibold first:mt-0" {...props} />,
  h2: (props) => <h3 className="mt-3 mb-1 text-base font-semibold first:mt-0" {...props} />,
  h3: (props) => <h4 className="mt-2 mb-1 text-sm font-semibold first:mt-0" {...props} />,
};

export function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
