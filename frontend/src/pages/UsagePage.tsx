import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { UserAvatar } from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  ArrowLeft,
  Loader2,
  TrendingUp,
  MessageSquare,
  DollarSign,
  Zap,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
} from "recharts";

const ITEMS_PER_PAGE = 15;

// Parse UTC timestamp and format in local time
const formatLocalTime = (utcString: string) => {
  const date = new Date(utcString.endsWith('Z') ? utcString : utcString + 'Z');
  return date.toLocaleString();
};

const formatTokens = (tokens: number) => {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  }
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`;
  }
  return tokens.toString();
};

const getProgressColor = (pct: number) => {
  if (pct >= 100) return "[&>div]:bg-red-500";
  if (pct >= 80) return "[&>div]:bg-orange-500";
  if (pct >= 60) return "[&>div]:bg-yellow-500";
  return "";
};

const formatModelName = (model: string) => {
  if (model.includes("opus")) return "Opus";
  if (model.includes("sonnet")) return "Sonnet";
  if (model.includes("haiku")) return "Haiku";
  return model.split("-")[0] || model;
};

export default function UsagePage() {
  const [chartView, setChartView] = useState<"week" | "day">("week");
  const [historyPage, setHistoryPage] = useState(1);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["usageSummary"],
    queryFn: api.getUsageSummary,
  });

  const { data: dailyUsage, isLoading: dailyLoading } = useQuery({
    queryKey: ["dailyUsage"],
    queryFn: () => api.getDailyUsage(7),
  });

  const { data: queryHistory, isLoading: historyLoading } = useQuery({
    queryKey: ["queryHistory"],
    queryFn: () => api.getUsageHistory(200),
  });

  const usagePercent = summary?.usage_percent ?? 0;

  // Get today's queries for day view
  const todayQueries = useMemo(() => {
    if (!queryHistory) return [];

    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];

    return queryHistory
      .filter((q) => {
        const queryDate = new Date(q.created_at.endsWith('Z') ? q.created_at : q.created_at + 'Z');
        return queryDate.toISOString().split('T')[0] === todayStr;
      })
      .map((q) => {
        const queryDate = new Date(q.created_at.endsWith('Z') ? q.created_at : q.created_at + 'Z');
        return {
          ...q,
          hour: queryDate.getHours() + queryDate.getMinutes() / 60,
          total_tokens: q.input_tokens + q.output_tokens,
          time: queryDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      });
  }, [queryHistory]);

  // Pagination for query history
  const totalPages = queryHistory ? Math.ceil(queryHistory.length / ITEMS_PER_PAGE) : 0;
  const paginatedHistory = useMemo(
    () => queryHistory
      ? queryHistory.slice((historyPage - 1) * ITEMS_PER_PAGE, historyPage * ITEMS_PER_PAGE)
      : [],
    [queryHistory, historyPage]
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/chat">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <span className="font-semibold">Usage</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <UserAvatar afterSignOutUrl="/" />
          </div>
        </div>
      </header>

      <main className="container max-w-5xl mx-auto py-8 px-4">
        {summaryLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : summary ? (
          <>
            {/* Current Month Usage */}
            <Card className="mb-8">
              <CardHeader>
                <CardTitle>Current Month Usage</CardTitle>
                <CardDescription>
                  {summary.plan_display_name || summary.plan.charAt(0).toUpperCase() + summary.plan.slice(1)} Plan
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between text-sm">
                    <span>{formatTokens(summary.current_month_tokens)} used</span>
                    <span>{formatTokens(summary.token_limit)} limit</span>
                  </div>
                  <Progress
                    value={Math.min(usagePercent, 100)}
                    className={`h-3 ${getProgressColor(usagePercent)}`}
                  />
                  <div className="flex justify-end text-xs text-muted-foreground">
                    <span>{usagePercent.toFixed(1)}%</span>
                  </div>
                  {usagePercent >= 80 && usagePercent < 100 && (
                    <p className="text-sm text-yellow-600 dark:text-yellow-500">
                      You're approaching your monthly limit. Consider upgrading your plan.
                    </p>
                  )}
                  {usagePercent >= 100 && (
                    <p className="text-sm text-red-600 dark:text-red-400">
                      Monthly limit reached.{" "}
                      <Link to="/pricing" className="underline hover:no-underline">Upgrade your plan</Link> to continue.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Stats Grid */}
            <div className="grid md:grid-cols-4 gap-4 mb-8">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <Zap className="h-4 w-4" />
                    <span className="text-sm">Tokens This Month</span>
                  </div>
                  <div className="text-2xl font-bold">
                    {formatTokens(summary.current_month_tokens)}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <DollarSign className="h-4 w-4" />
                    <span className="text-sm">Total Cost</span>
                  </div>
                  <div className="text-2xl font-bold">
                    ${summary.total_cost_usd.toFixed(2)}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <MessageSquare className="h-4 w-4" />
                    <span className="text-sm">Conversations</span>
                  </div>
                  <div className="text-2xl font-bold">
                    {summary.total_conversations}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-sm">Messages</span>
                  </div>
                  <div className="text-2xl font-bold">
                    {summary.total_messages}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Usage Chart */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>
                    {chartView === "week" ? "Token Usage (Last 7 Days)" : "Today's Queries"}
                  </CardTitle>
                  <div className="flex gap-1">
                    <Button
                      variant={chartView === "week" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setChartView("week")}
                    >
                      Week
                    </Button>
                    <Button
                      variant={chartView === "day" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setChartView("day")}
                    >
                      Day
                    </Button>
                  </div>
                </div>
                <CardDescription>
                  {chartView === "week"
                    ? "Daily token usage over the past week"
                    : "Individual queries throughout today"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {chartView === "week" ? (
                  dailyLoading ? (
                    <div className="flex justify-center py-12">
                      <Loader2 className="h-6 w-6 animate-spin" />
                    </div>
                  ) : dailyUsage && dailyUsage.length > 0 ? (
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={dailyUsage}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => {
                              const date = new Date(value);
                              return `${date.getMonth() + 1}/${date.getDate()}`;
                            }}
                          />
                          <YAxis
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => formatTokens(value)}
                          />
                          <Legend
                            formatter={(value) => value === "input_tokens" ? "Input Tokens" : "Output Tokens"}
                          />
                          <Bar dataKey="input_tokens" name="input_tokens" fill="hsl(var(--primary))" />
                          <Bar dataKey="output_tokens" name="output_tokens" fill="hsl(var(--muted-foreground))" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      No usage data yet. Start a conversation to see your usage.
                    </div>
                  )
                ) : (
                  historyLoading ? (
                    <div className="flex justify-center py-12">
                      <Loader2 className="h-6 w-6 animate-spin" />
                    </div>
                  ) : todayQueries.length > 0 ? (
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                          <XAxis
                            dataKey="hour"
                            type="number"
                            domain={[0, 24]}
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => {
                              const hour = Math.floor(value);
                              const ampm = hour >= 12 ? 'PM' : 'AM';
                              const h = hour % 12 || 12;
                              return `${h}${ampm}`;
                            }}
                            ticks={[0, 6, 12, 18, 24]}
                          />
                          <YAxis
                            dataKey="total_tokens"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => formatTokens(value)}
                            label={{ value: 'Tokens', angle: -90, position: 'insideLeft', fontSize: 12 }}
                          />
                          <Tooltip
                            cursor={{ strokeDasharray: '3 3', stroke: 'hsl(var(--muted-foreground))' }}
                            content={({ active, payload }) => {
                              if (active && payload && payload[0]) {
                                const data = payload[0].payload;
                                return (
                                  <div className="bg-popover border border-border rounded-lg p-2 shadow-md text-sm">
                                    <div className="font-mono text-xs text-muted-foreground">{data.id.slice(0, 8)}</div>
                                    <div className="font-medium">{data.time}</div>
                                    <div className="text-muted-foreground mt-1">
                                      Input: {formatTokens(data.input_tokens)}
                                    </div>
                                    <div className="text-muted-foreground">
                                      Output: {formatTokens(data.output_tokens)}
                                    </div>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Scatter
                            data={todayQueries}
                            fill="hsl(var(--primary))"
                          />
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      No queries yet today
                    </div>
                  )
                )}
              </CardContent>
            </Card>

            {/* Query History */}
            <Card className="mt-8">
              <CardHeader>
                <CardTitle>Query History</CardTitle>
                <CardDescription>Individual queries and token usage</CardDescription>
              </CardHeader>
              <CardContent>
                {historyLoading ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : queryHistory && queryHistory.length > 0 ? (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2 px-2 font-medium">ID</th>
                            <th className="text-left py-2 px-2 font-medium">Time</th>
                            <th className="text-left py-2 px-2 font-medium">Conversation</th>
                            <th className="text-left py-2 px-2 font-medium">Model</th>
                            <th className="text-right py-2 px-2 font-medium">Input</th>
                            <th className="text-right py-2 px-2 font-medium">Output</th>
                            <th className="text-right py-2 px-2 font-medium">Total</th>
                            <th className="text-right py-2 px-2 font-medium">Cost</th>
                          </tr>
                        </thead>
                        <tbody>
                          {paginatedHistory.map((item) => (
                            <tr key={item.id} className="border-b border-border/50">
                              <td className="py-2 px-2 text-muted-foreground font-mono text-xs">
                                {item.id.slice(0, 8)}
                              </td>
                              <td className="py-2 px-2 text-muted-foreground whitespace-nowrap">
                                {formatLocalTime(item.created_at)}
                              </td>
                              <td className="py-2 px-2 truncate max-w-[200px]">
                                {item.conversation_title}
                              </td>
                              <td className="py-2 px-2 text-muted-foreground text-xs">
                                {formatModelName(item.model)}
                              </td>
                              <td className="py-2 px-2 text-right tabular-nums">
                                {formatTokens(item.input_tokens)}
                              </td>
                              <td className="py-2 px-2 text-right tabular-nums">
                                {formatTokens(item.output_tokens)}
                              </td>
                              <td className="py-2 px-2 text-right tabular-nums font-medium">
                                {formatTokens(item.input_tokens + item.output_tokens)}
                              </td>
                              <td className="py-2 px-2 text-right tabular-nums">
                                ${item.cost_usd.toFixed(4)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-center gap-4 mt-4">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                          disabled={historyPage === 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span className="text-sm text-muted-foreground">
                          Page {historyPage} of {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => setHistoryPage((p) => Math.min(totalPages, p + 1))}
                          disabled={historyPage === totalPages}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    No query history yet
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            Unable to load usage data
          </div>
        )}
      </main>
    </div>
  );
}
