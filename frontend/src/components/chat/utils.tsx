import { memo, useState } from "react";
import { Check, Copy } from "lucide-react";

export const extractSqlBlocks = (content: string): string[] => {
  const sqlRegex = /```sql\s*([\s\S]*?)```/gi;
  const matches: string[] = [];
  let match;
  while ((match = sqlRegex.exec(content)) !== null) {
    matches.push(match[1].trim());
  }
  return matches;
};

export const stripSqlBlocks = (content: string): string => {
  return content.replace(/```sql\s*[\s\S]*?```\s*/gi, "").trim();
};

export const CopyButton = memo(function CopyButton({
  text,
  label = "Copy",
  className = "",
}: {
  text: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className={`flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors ${className}`}
      title="Copy to clipboard"
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      <span>{copied ? "Copied" : label}</span>
    </button>
  );
});

export const downloadCsv = (rows: Record<string, any>[], filename: string) => {
  if (!rows || rows.length === 0) return;
  const headers = Object.keys(rows[0]);
  const escape = (val: any): string => {
    if (val === null || val === undefined) return "";
    const s = String(val);
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const csv = [
    headers.join(","),
    ...rows.map((row) => headers.map((h) => escape(row[h])).join(",")),
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const CollapsibleSqlContent = memo(function CollapsibleSqlContent({
  queries,
}: {
  queries: string[];
}) {
  const [copied, setCopied] = useState(false);
  const allSql = queries.join("\n\n");
  const handleCopy = () => {
    navigator.clipboard.writeText(allSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="mt-2 p-3 bg-muted/30 rounded-lg border border-border">
      <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto">{allSql}</pre>
      <button
        onClick={handleCopy}
        className="mt-2 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        title="Copy SQL to clipboard"
      >
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        {copied ? "Copied" : "Copy all"}
      </button>
    </div>
  );
});

export const ASSISTANT_PROSE_CLASSES =
  "[&>*]:mb-4 [&>*:last-child]:mb-0 [&_p]:leading-relaxed [&_p]:mb-4 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:mb-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:mb-4 [&_table]:w-full [&_table]:border-collapse [&_table]:my-5 [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1.5 [&_th]:bg-muted/50 [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1.5 [&_strong]:font-semibold [&_code]:bg-muted/50 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-muted/50 [&_pre]:p-3 [&_pre]:rounded [&_pre]:overflow-x-auto [&_pre]:text-xs [&_pre]:my-5";
