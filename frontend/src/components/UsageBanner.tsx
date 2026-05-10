import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, CurrentUsage } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

export default function UsageBanner() {
  const { data: runtimeConfig } = useQuery({
    queryKey: ["runtime-config"],
    queryFn: api.getConfig,
    staleTime: Infinity,
  });
  const billingEnabled = runtimeConfig?.billing_enabled !== false;

  const { data: usage } = useQuery<CurrentUsage>({
    queryKey: ["currentUsage"],
    queryFn: api.getCurrentUsage,
    refetchInterval: 60000,
    staleTime: 30000,
    enabled: billingEnabled,
  });

  if (!billingEnabled) return null;
  if (!usage || usage.usage_percent < 80) return null;

  const pct = usage.usage_percent;

  // 100%+: hard limit
  if (pct >= 100) {
    return (
      <div className="sticky top-0 z-10 px-4 py-3 bg-red-500/10 border-b border-red-500/30 flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>Monthly limit reached. Upgrade to continue.</span>
        <Link
          to="/pricing"
          className="ml-auto text-xs font-medium underline hover:no-underline"
        >
          View plans
        </Link>
      </div>
    );
  }

  // 80-99%: yellow warning
  return (
    <div className="sticky top-0 z-10 px-4 py-3 bg-yellow-500/10 border-b border-yellow-500/30 flex items-center gap-2 text-sm text-yellow-600 dark:text-yellow-400">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>You've used {pct.toFixed(0)}% of your monthly tokens.</span>
      <Link
        to="/usage"
        className="ml-auto text-xs font-medium underline hover:no-underline"
      >
        View usage
      </Link>
    </div>
  );
}
