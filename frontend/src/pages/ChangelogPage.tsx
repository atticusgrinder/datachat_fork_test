import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Tag } from "lucide-react";

interface ChangelogEntry {
  slug: string;
  title: string;
  date: string;
  version: string;
  tags: string[];
  body: string;
}

const TAG_STYLES: Record<string, string> = {
  feature: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300",
  fix: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  improvement: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
};

const TAG_LABELS: Record<string, string> = {
  feature: "Feature",
  fix: "Fix",
  improvement: "Improvement",
};

type FilterType = "all" | "feature" | "fix" | "improvement";

const FILTERS: { value: FilterType; label: string }[] = [
  { value: "all", label: "All" },
  { value: "feature", label: "Features" },
  { value: "fix", label: "Fixes" },
  { value: "improvement", label: "Improvements" },
];

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function ChangelogPage() {
  const [filter, setFilter] = useState<FilterType>("all");
  const location = useLocation();

  const { data, isLoading } = useQuery<{ entries: ChangelogEntry[] }>({
    queryKey: ["changelog"],
    queryFn: () => api.getChangelog(),
  });

  const entries = data?.entries ?? [];
  const filtered = filter === "all"
    ? entries
    : entries.filter((e) => e.tags.includes(filter));

  // Scroll to top on mount, or to anchor if hash present
  useEffect(() => {
    if (location.hash) {
      const el = document.getElementById(location.hash.slice(1));
      if (el) el.scrollIntoView({ behavior: "smooth" });
    } else {
      window.scrollTo(0, 0);
    }
  }, [location.hash, entries]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-10">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="flex items-center text-foreground hover:text-foreground/80 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-xl font-bold">Changelog</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-10 max-w-3xl">
        {/* Intro */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold mb-2">What's New</h2>
          <p className="text-muted-foreground">
            The latest updates and improvements to Datachat.
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap gap-2 mb-10">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="text-center py-20 text-muted-foreground">
            Loading changelog...
          </div>
        )}

        {/* Entries */}
        {!isLoading && filtered.length === 0 && (
          <div className="text-center py-20 text-muted-foreground">
            No entries found.
          </div>
        )}

        <div className="space-y-8">
          {filtered.map((entry) => (
            <article
              key={entry.slug}
              id={entry.slug}
              className="relative border rounded-lg p-6 bg-card shadow-sm scroll-mt-24"
            >
              {/* Date & version */}
              <div className="flex flex-wrap items-center gap-3 mb-3">
                <time className="text-sm text-muted-foreground">
                  {formatDate(entry.date)}
                </time>
                {entry.version && (
                  <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                    v{entry.version}
                  </span>
                )}
                {entry.tags.map((tag) => (
                  <span
                    key={tag}
                    className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                      TAG_STYLES[tag] ?? "bg-muted text-muted-foreground"
                    }`}
                  >
                    <Tag className="h-3 w-3" />
                    {TAG_LABELS[tag] ?? tag}
                  </span>
                ))}
              </div>

              {/* Title */}
              <h3 className="text-lg font-semibold mb-3">{entry.title}</h3>

              {/* Body */}
              <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {entry.body}
                </ReactMarkdown>
              </div>
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}
