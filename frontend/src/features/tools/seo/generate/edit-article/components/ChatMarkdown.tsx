'use client';

import React, { type ComponentPropsWithoutRef } from 'react';
import ReactMarkdown, { type Components, type ExtraProps } from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema, type Options as RehypeSanitizeOptions } from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';

import { cn } from '@/utils/cn';

interface ChatMarkdownProps {
  content: string;
  className?: string;
}

const sanitizeSchema: RehypeSanitizeOptions = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code ?? []), ['className']],
    span: [...(defaultSchema.attributes?.span ?? []), ['className']],
    pre: [...(defaultSchema.attributes?.pre ?? []), ['className']],
    div: [...(defaultSchema.attributes?.div ?? []), ['className']],
  },
};

const markdownComponents: Components = {
  code(componentProps) {
    const { inline, className, children, ...props } = componentProps as ComponentPropsWithoutRef<'code'> &
      ExtraProps & {
        inline?: boolean;
      };

    if (inline) {
      return (
        <code
          className={cn(
            'rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[13px] font-medium text-slate-900',
            className
          )}
          {...props}
        >
          {children}
        </code>
      );
    }

    return (
      <div className="group relative my-4 w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-950/95 text-slate-100 shadow-inner">
        <pre className="overflow-x-auto p-4 text-sm leading-7">
          <code className={cn('block font-mono', className)} {...props}>
            {children}
          </code>
        </pre>
      </div>
    );
  },
  a({ children, href, ...props }) {
    if (!href) {
      return <span {...props}>{children}</span>;
    }

    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-blue-600 underline-offset-4 transition-colors hover:text-blue-500"
        {...props}
      >
        {children}
      </a>
    );
  },
  table({ children, ...props }) {
    return (
      <div className="my-4 overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full border-collapse text-left text-sm" {...props}>
          {children}
        </table>
      </div>
    );
  },
  th({ children, ...props }) {
    return (
      <th className="border-b border-slate-200 bg-slate-100 px-3 py-2 text-left font-semibold text-slate-700" {...props}>
        {children}
      </th>
    );
  },
  td({ children, ...props }) {
    return (
      <td className="border-b border-slate-100 px-3 py-2 align-top text-slate-600 last:border-r-0" {...props}>
        {children}
      </td>
    );
  },
  blockquote({ children, ...props }) {
    return (
      <blockquote
        className="border-l-4 border-blue-200 bg-blue-50/60 px-4 py-2 text-sm font-medium italic text-slate-700"
        {...props}
      >
        {children}
      </blockquote>
    );
  },
  ul({ children, ...props }) {
    return (
      <ul className="my-3 space-y-2 pl-5 [list-style-type:disc]" {...props}>
        {children}
      </ul>
    );
  },
  ol({ children, ...props }) {
    return (
      <ol className="my-3 space-y-2 pl-5 [list-style-type:decimal]" {...props}>
        {children}
      </ol>
    );
  },
  p({ children, ...props }) {
    return (
      <p className="my-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700" {...props}>
        {children}
      </p>
    );
  },
};

export default function ChatMarkdown({ content, className }: ChatMarkdownProps) {
  return (
    <div
      className={cn(
        'prose prose-slate max-w-none text-sm leading-relaxed prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-h4:text-base prose-h5:text-sm prose-h6:text-sm prose-p:my-2 prose-p:text-slate-700 prose-li:marker:text-slate-400 prose-strong:text-slate-900 prose-code:text-[13px] prose-code:font-medium',
        'prose-pre:m-0 prose-pre:bg-transparent prose-headings:font-semibold prose-headings:text-slate-800',
        'break-words [text-wrap:pretty]',
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
