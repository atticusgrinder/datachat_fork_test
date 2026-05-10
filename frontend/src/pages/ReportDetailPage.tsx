import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, SavedVisualization } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ChartRenderer from "@/components/ChartRenderer";
import ScheduleDialog from "@/components/ScheduleDialog";
import VisualizationExpandModal from "@/components/VisualizationExpandModal";
import {
  ArrowLeft,
  BarChart3,
  Calendar,
  Loader2,
  Maximize2,
  Pencil,
  RefreshCw,
  Send,
  Table as TableIcon,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

export default function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const qc = useQueryClient();
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renaming) {
      titleInputRef.current?.focus();
      titleInputRef.current?.select();
    }
  }, [renaming]);

  const { data: report, isLoading } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.getReport(reportId!),
    enabled: !!reportId,
  });

  const { data: allViz } = useQuery({
    queryKey: ["visualizations"],
    queryFn: api.listVisualizations,
  });

  const [vizData, setVizData] = useState<Record<string, Record<string, any>[]>>({});
  const [refreshingId, setRefreshingId] = useState<string | null>(null);
  const [showDataIds, setShowDataIds] = useState<Set<string>>(new Set());
  const [expandedViz, setExpandedViz] = useState<{
    viz: SavedVisualization;
    data: Record<string, any>[];
  } | null>(null);

  const toggleShowData = (vizId: string) => {
    setShowDataIds((prev) => {
      const next = new Set(prev);
      if (next.has(vizId)) next.delete(vizId);
      else next.add(vizId);
      return next;
    });
  };

  useEffect(() => {
    if (!report) return;
    report.items.forEach((item) => {
      if (vizData[item.saved_visualization_id]) return;
      void refreshOne(item.saved_visualization_id);
    });
  }, [report?.id]);

  const refreshOne = async (vizId: string) => {
    setRefreshingId(vizId);
    try {
      const result = await api.refreshVisualization(vizId);
      setVizData((p) => ({ ...p, [vizId]: result.chart_data }));
    } catch {
      // surfacing per-card; main toast below for explicit user actions
    } finally {
      setRefreshingId(null);
    }
  };

  const sendNowMutation = useMutation({
    mutationFn: () => api.sendReportNow(reportId!),
    onSuccess: () => toast.success("Report sent"),
    onError: (e: any) => toast.error(e?.message || "Failed to send"),
  });

  const renameReportMutation = useMutation({
    mutationFn: (name: string) => api.updateReport(reportId!, { name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["report", reportId] });
      qc.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: () => toast.error("Failed to rename report"),
  });

  const startRename = () => {
    if (!report) return;
    setTitleDraft(report.name);
    setRenaming(true);
  };
  const commitRename = () => {
    const next = titleDraft.trim();
    if (next && report && next !== report.name) renameReportMutation.mutate(next);
    setRenaming(false);
  };
  const cancelRename = () => {
    setRenaming(false);
  };

  const setScheduleMutation = useMutation({
    mutationFn: (data: Parameters<typeof api.setReportSchedule>[1]) =>
      api.setReportSchedule(reportId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["report", reportId] });
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Schedule saved");
    },
    onError: (e: any) => toast.error(e?.message || "Failed"),
  });

  const disableScheduleMutation = useMutation({
    mutationFn: () => api.disableReportSchedule(reportId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["report", reportId] });
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Schedule disabled");
    },
  });

  const removeItemMutation = useMutation({
    mutationFn: (itemId: string) => api.removeReportItem(reportId!, itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["report", reportId] });
      toast.success("Visualization removed");
    },
  });

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!report) {
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-3">
        <p className="text-muted-foreground">Report not found.</p>
        <Link to="/reports">
          <Button variant="outline">Back to Reports</Button>
        </Link>
      </div>
    );
  }

  const vizMap = new Map<string, SavedVisualization>(
    (allViz ?? []).map((v) => [v.id, v]),
  );

  return (
    <div className="min-h-screen bg-background">
      <header className="h-14 border-b flex items-center px-4 gap-3">
        <Link to="/reports">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="min-w-0 flex items-center gap-2">
          {renaming ? (
            <input
              ref={titleInputRef}
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  commitRename();
                } else if (e.key === "Escape") {
                  e.preventDefault();
                  cancelRename();
                }
              }}
              className="font-semibold bg-background border border-input rounded px-2 py-0.5 outline-none focus:ring-2 focus:ring-ring min-w-0"
            />
          ) : (
            <h1 className="font-semibold truncate">{report.name}</h1>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                onClick={startRename}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Rename</TooltipContent>
          </Tooltip>
        </div>
        <div className="flex-1" />
        {!report.schedule && (
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() => sendNowMutation.mutate()}
              disabled={sendNowMutation.isPending}
            >
              {sendNowMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
              ) : (
                <Send className="h-3.5 w-3.5 mr-1.5" />
              )}
              Send now
            </Button>
            <Button size="sm" onClick={() => setScheduleOpen(true)}>
              <Calendar className="h-3.5 w-3.5 mr-1.5" />
              Schedule
            </Button>
          </>
        )}
      </header>

      <div className="max-w-6xl mx-auto p-6 space-y-4">
        {report.schedule && (
          <Card className="px-4 py-3 text-sm flex items-center justify-between">
            <div>
              <span className="font-medium capitalize">{report.schedule.cadence}</span>
              <span className="text-muted-foreground ml-2">
                at {report.schedule.time_of_day} {report.schedule.timezone}
                {report.schedule.next_send_at && (
                  <> · next send {new Date(report.schedule.next_send_at).toLocaleString()}</>
                )}
              </span>
            </div>
            <div className="flex items-center gap-1">
              {!report.schedule.enabled && (
                <span className="text-xs text-muted-foreground mr-2">Disabled</span>
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setScheduleOpen(true)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Edit schedule</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => sendNowMutation.mutate()}
                    disabled={sendNowMutation.isPending}
                  >
                    {sendNowMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Send className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Send now</TooltipContent>
              </Tooltip>
            </div>
          </Card>
        )}

        {report.items.length === 0 ? (
          <Card className="p-8 text-center text-sm text-muted-foreground">
            This report has no visualizations yet. Add one from the Reports page or via chat.
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {report.items.map((item) => {
              const viz = vizMap.get(item.saved_visualization_id);
              if (!viz) {
                return (
                  <Card key={item.id} className="p-4 text-xs text-muted-foreground">
                    Visualization unavailable (id={item.saved_visualization_id})
                  </Card>
                );
              }
              const data = vizData[viz.id];
              let cfg: { x_column: string; y_column: string } | null = null;
              try {
                const c = JSON.parse(viz.chart_config);
                cfg = { x_column: c.x_column, y_column: c.y_column };
              } catch { /* ignore */ }
              const isRefreshing = refreshingId === viz.id;
              const showData = showDataIds.has(viz.id);
              return (
                <Card key={item.id} className="overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-muted/30">
                    <h3 className="text-sm font-medium truncate">{viz.name}</h3>
                    <div className="flex items-center gap-0.5 shrink-0">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => refreshOne(viz.id)}
                            disabled={isRefreshing}
                          >
                            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Refresh data</TooltipContent>
                      </Tooltip>
                      {data && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className={`h-7 w-7 ${showData ? "text-foreground bg-muted" : ""}`}
                              onClick={() => toggleShowData(viz.id)}
                            >
                              <TableIcon className="h-3.5 w-3.5" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>{showData ? "Show chart" : "Show data"}</TooltipContent>
                        </Tooltip>
                      )}
                      {data && cfg && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => setExpandedViz({ viz, data })}
                            >
                              <Maximize2 className="h-3.5 w-3.5" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Expand</TooltipContent>
                        </Tooltip>
                      )}
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive hover:text-destructive"
                            onClick={() => removeItemMutation.mutate(item.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Remove from report</TooltipContent>
                      </Tooltip>
                    </div>
                  </div>
                  <div className="p-2">
                    {showData && data ? (
                      <DataTable rows={data} />
                    ) : data && cfg ? (
                      <ChartRenderer
                        chartType={viz.chart_type}
                        data={data}
                        xColumn={cfg.x_column}
                        yColumn={cfg.y_column}
                        height={240}
                      />
                    ) : isRefreshing ? (
                      <div className="flex items-center justify-center h-[240px] text-muted-foreground">
                        <Loader2 className="h-5 w-5 animate-spin" />
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-[240px] text-muted-foreground">
                        <BarChart3 className="h-8 w-8 mb-2 opacity-30" />
                        <Button size="sm" variant="ghost" onClick={() => refreshOne(viz.id)}>
                          Load data
                        </Button>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <ScheduleDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        report={report}
        onSubmit={(data) => setScheduleMutation.mutateAsync(data)}
        onDisable={
          report.schedule
            ? () => disableScheduleMutation.mutate()
            : undefined
        }
      />

      {expandedViz && (() => {
        try {
          const cfg = JSON.parse(expandedViz.viz.chart_config);
          return (
            <VisualizationExpandModal
              visualization={{
                chart_type: expandedViz.viz.chart_type,
                title: cfg.title || expandedViz.viz.name,
                x_column: cfg.x_column,
                y_column: cfg.y_column,
              }}
              chartData={expandedViz.data}
              onClose={() => setExpandedViz(null)}
            />
          );
        } catch {
          return null;
        }
      })()}
    </div>
  );
}

function DataTable({ rows }: { rows: Record<string, any>[] }) {
  if (!rows.length) {
    return (
      <div className="flex items-center justify-center h-[240px] text-xs text-muted-foreground">
        No rows.
      </div>
    );
  }
  const headers = Object.keys(rows[0]);
  return (
    <div className="max-h-[240px] overflow-auto">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0 bg-muted/60">
          <tr>
            {headers.map((h) => (
              <th key={h} className="text-left px-2 py-1.5 font-medium border-b border-border/50">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-muted/30">
              {headers.map((h) => (
                <td key={h} className="px-2 py-1 border-b border-border/30">
                  {String(r[h] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
