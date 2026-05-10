import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Report, SavedVisualization } from "@/lib/api";
import { Card } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ChartRenderer from "@/components/ChartRenderer";
import VisualizationExpandModal from "@/components/VisualizationExpandModal";
import ScheduleDialog from "@/components/ScheduleDialog";
import AddToReportDialog from "@/components/AddToReportDialog";
import {
  ArrowLeft,
  BarChart3,
  Calendar,
  CalendarPlus,
  ExternalLink,
  Loader2,
  Maximize2,
  Pencil,
  RefreshCw,
  Send,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface RefreshedData {
  [vizId: string]: Record<string, any>[];
}

export default function ReportsPage() {
  const qc = useQueryClient();

  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: api.listReports,
  });

  const { data: visualizations, isLoading: vizLoading } = useQuery({
    queryKey: ["visualizations"],
    queryFn: api.listVisualizations,
  });

  const [refreshedData, setRefreshedData] = useState<RefreshedData>({});
  const [refreshingIds, setRefreshingIds] = useState<Set<string>>(new Set());
  const [expandedViz, setExpandedViz] = useState<{
    viz: SavedVisualization;
    data: Record<string, any>[];
  } | null>(null);

  const [scheduleTarget, setScheduleTarget] = useState<Report | null>(null);
  const [addToReportTarget, setAddToReportTarget] = useState<SavedVisualization | null>(null);

  const autoRefreshed = useRef(false);
  useEffect(() => {
    if (visualizations?.length && !autoRefreshed.current) {
      autoRefreshed.current = true;
      visualizations.forEach((viz) => {
        if (!refreshedData[viz.id]) handleRefresh(viz.id, false);
      });
    }
  }, [visualizations]);

  const deleteVizMutation = useMutation({
    mutationFn: api.deleteVisualization,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["visualizations"] });
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Visualization deleted");
    },
    onError: () => toast.error("Failed to delete visualization"),
  });

  const deleteReportMutation = useMutation({
    mutationFn: api.deleteReport,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Report deleted");
    },
    onError: () => toast.error("Failed to delete report"),
  });

  const renameReportMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      api.updateReport(id, { name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: () => toast.error("Failed to rename report"),
  });

  const sendNowMutation = useMutation({
    mutationFn: api.sendReportNow,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Report sent");
    },
    onError: (e: any) => toast.error(e?.message || "Failed to send report"),
  });

  const setScheduleMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof api.setReportSchedule>[1] }) =>
      api.setReportSchedule(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Schedule saved");
    },
    onError: (e: any) => toast.error(e?.message || "Failed to save schedule"),
  });

  const disableScheduleMutation = useMutation({
    mutationFn: api.disableReportSchedule,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Schedule disabled");
    },
    onError: () => toast.error("Failed to disable schedule"),
  });

  const handleRefresh = async (vizId: string, showToast = true) => {
    setRefreshingIds((prev) => new Set(prev).add(vizId));
    try {
      const result = await api.refreshVisualization(vizId);
      setRefreshedData((prev) => ({ ...prev, [vizId]: result.chart_data }));
      if (showToast) toast.success("Data refreshed");
    } catch {
      if (showToast) toast.error("Failed to refresh data");
    } finally {
      setRefreshingIds((prev) => {
        const n = new Set(prev);
        n.delete(vizId);
        return n;
      });
    }
  };

  const getVizConfig = (viz: SavedVisualization) => {
    try {
      const config = JSON.parse(viz.chart_config);
      return {
        chart_type: viz.chart_type,
        title: config.title || viz.name,
        x_column: config.x_column,
        y_column: config.y_column,
      };
    } catch {
      return null;
    }
  };

  const mainContent = (
    <div className="flex-1 overflow-y-auto">
      <div className="container max-w-5xl mx-auto py-8 px-4 space-y-24">
        {/* Scheduled Reports */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold">Scheduled Reports</h2>
            </div>
          </div>
          {reportsLoading ? (
            <div className="py-8 flex justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !reports?.length ? (
            <p className="text-sm text-muted-foreground">
              No scheduled reports yet. Ask Claude in the panel to "save this as a weekly report"
              after running a query — or schedule one of your saved visualizations below.
            </p>
          ) : (
            <div className="space-y-8">
              {reports.map((r) => (
                <ReportSection
                  key={r.id}
                  report={r}
                  vizMap={new Map((visualizations ?? []).map((v) => [v.id, v]))}
                  refreshedData={refreshedData}
                  refreshingIds={refreshingIds}
                  onRefreshViz={(vizId) => handleRefresh(vizId)}
                  onExpand={(viz, data) => setExpandedViz({ viz, data })}
                  onSchedule={() => setScheduleTarget(r)}
                  onSendNow={() => sendNowMutation.mutate(r.id)}
                  onRename={(next) => renameReportMutation.mutate({ id: r.id, name: next })}
                  onDelete={() => {
                    if (confirm(`Delete report "${r.name}"?`))
                      deleteReportMutation.mutate(r.id);
                  }}
                  sending={sendNowMutation.isPending && sendNowMutation.variables === r.id}
                />
              ))}
            </div>
          )}
        </section>

        {/* Saved Visualizations */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold">Saved Visualizations</h2>
            </div>
          </div>
          {vizLoading ? (
            <div className="py-8 flex justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !visualizations?.length ? (
            <p className="text-sm text-muted-foreground">
              Charts from your conversations can be saved here for quick access.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {visualizations.map((viz) => {
                const config = getVizConfig(viz);
                const data = refreshedData[viz.id];
                return (
                  <Card key={viz.id} className="overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-muted/30">
                      <div className="min-w-0">
                        <h3 className="text-sm font-medium truncate">{viz.name}</h3>
                      </div>
                      <div className="flex items-center gap-0.5 shrink-0">
                        <IconButton
                          icon={<RefreshCw className={`h-3.5 w-3.5 ${refreshingIds.has(viz.id) ? "animate-spin" : ""}`} />}
                          tooltip="Refresh data"
                          onClick={() => handleRefresh(viz.id)}
                          disabled={refreshingIds.has(viz.id)}
                        />
                        <IconButton
                          icon={<CalendarPlus className="h-3.5 w-3.5" />}
                          tooltip="Add to report"
                          onClick={() => setAddToReportTarget(viz)}
                        />
                        {config && data && (
                          <IconButton
                            icon={<Maximize2 className="h-3.5 w-3.5" />}
                            tooltip="Expand"
                            onClick={() => setExpandedViz({ viz, data })}
                          />
                        )}
                        <IconButton
                          icon={<Trash2 className="h-3.5 w-3.5" />}
                          tooltip="Delete"
                          danger
                          onClick={() => deleteVizMutation.mutate(viz.id)}
                        />
                      </div>
                    </div>
                    <div className="p-2">
                      {data && config ? (
                        <ChartRenderer
                          chartType={viz.chart_type}
                          data={data}
                          xColumn={config.x_column}
                          yColumn={config.y_column}
                          height={200}
                        />
                      ) : (
                        <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
                          <BarChart3 className="h-8 w-8 mb-2 opacity-30" />
                          <p className="text-xs">Click refresh to load data</p>
                        </div>
                      )}
                    </div>
                    <div className="px-3 py-2 border-t border-border/50 text-[10px] text-muted-foreground">
                      {new Date(viz.created_at).toLocaleString()}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="border-b shrink-0">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/chat">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <span className="font-semibold">Reports</span>
        </div>
      </header>
      <div className="flex-1 min-h-0 flex">{mainContent}</div>

      {expandedViz && (
        <VisualizationExpandModal
          visualization={getVizConfig(expandedViz.viz)!}
          chartData={expandedViz.data}
          onClose={() => setExpandedViz(null)}
        />
      )}
      <ScheduleDialog
        open={scheduleTarget !== null}
        onOpenChange={(open) => !open && setScheduleTarget(null)}
        report={scheduleTarget}
        onSubmit={(data) =>
          setScheduleMutation.mutateAsync({ id: scheduleTarget!.id, data })
        }
        onDisable={
          scheduleTarget?.schedule
            ? () => disableScheduleMutation.mutate(scheduleTarget!.id)
            : undefined
        }
      />
      <AddToReportDialog
        open={addToReportTarget !== null}
        onOpenChange={(open) => !open && setAddToReportTarget(null)}
        visualization={addToReportTarget}
      />
    </div>
  );
}

function IconButton({
  icon,
  tooltip,
  onClick,
  disabled,
  danger,
}: {
  icon: React.ReactNode;
  tooltip: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={`h-7 w-7 ${danger ? "text-destructive hover:text-destructive" : ""}`}
          onClick={onClick}
          disabled={disabled}
        >
          {icon}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{tooltip}</TooltipContent>
    </Tooltip>
  );
}

function ReportSection({
  report,
  vizMap,
  refreshedData,
  refreshingIds,
  onRefreshViz,
  onExpand,
  onSchedule,
  onSendNow,
  onRename,
  onDelete,
  sending,
}: {
  report: Report;
  vizMap: Map<string, SavedVisualization>;
  refreshedData: { [vizId: string]: Record<string, any>[] };
  refreshingIds: Set<string>;
  onRefreshViz: (vizId: string) => void;
  onExpand: (viz: SavedVisualization, data: Record<string, any>[]) => void;
  onSchedule: () => void;
  onSendNow: () => void;
  onRename: (newName: string) => void;
  onDelete: () => void;
  sending: boolean;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(report.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const startEdit = () => {
    setDraft(report.name);
    setIsEditing(true);
  };

  const commit = () => {
    const next = draft.trim();
    if (next && next !== report.name) onRename(next);
    setIsEditing(false);
  };

  const cancel = () => {
    setDraft(report.name);
    setIsEditing(false);
  };

  const sched = report.schedule;
  const items = report.items.filter((it) => vizMap.has(it.saved_visualization_id));

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-border/50 bg-muted/30">
        {isEditing ? (
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commit();
              } else if (e.key === "Escape") {
                e.preventDefault();
                cancel();
              }
            }}
            className="text-sm font-semibold bg-background border border-input rounded px-1.5 py-0.5 outline-none focus:ring-2 focus:ring-ring min-w-0"
          />
        ) : (
          <h3 className="text-sm font-semibold truncate">{report.name}</h3>
        )}
        {sched && (
          <span className="text-xs text-muted-foreground">
            <span className="capitalize">{sched.cadence}</span> at {sched.time_of_day} {sched.timezone}
            {!sched.enabled && <span className="ml-1">(disabled)</span>}
          </span>
        )}
        <div className="flex-1" />
        <div className="flex items-center gap-0.5 shrink-0">
          <IconButton
            icon={<Pencil className="h-3.5 w-3.5" />}
            tooltip="Rename"
            onClick={startEdit}
          />
          <IconButton
            icon={sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            tooltip="Send now"
            onClick={onSendNow}
            disabled={sending}
          />
          <IconButton
            icon={<Calendar className="h-3.5 w-3.5" />}
            tooltip="Schedule"
            onClick={onSchedule}
          />
          <Tooltip>
            <TooltipTrigger asChild>
              <Link to={`/reports/${report.id}`}>
                <Button variant="ghost" size="icon" className="h-7 w-7">
                  <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </TooltipTrigger>
            <TooltipContent>Open report</TooltipContent>
          </Tooltip>
          <IconButton
            icon={<Trash2 className="h-3.5 w-3.5" />}
            tooltip="Delete"
            danger
            onClick={onDelete}
          />
        </div>
      </div>
      {items.length === 0 ? (
        <div className="p-6 text-sm text-muted-foreground text-center">
          No visualizations in this report yet.
        </div>
      ) : (
        <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map((item) => {
            const viz = vizMap.get(item.saved_visualization_id)!;
            const data = refreshedData[viz.id];
            return (
              <ReportItemPreview
                key={item.id}
                viz={viz}
                data={data}
                refreshing={refreshingIds.has(viz.id)}
                onRefresh={() => onRefreshViz(viz.id)}
                onExpand={(d) => onExpand(viz, d)}
              />
            );
          })}
        </div>
      )}
    </Card>
  );
}

function ReportItemPreview({
  viz,
  data,
  refreshing,
  onRefresh,
  onExpand,
}: {
  viz: SavedVisualization;
  data: Record<string, any>[] | undefined;
  refreshing: boolean;
  onRefresh: () => void;
  onExpand: (data: Record<string, any>[]) => void;
}) {
  let cfg: { x_column?: string; y_column?: string } | null = null;
  try {
    cfg = JSON.parse(viz.chart_config);
  } catch {
    /* ignore */
  }

  const renderChart = data ? canRenderChart(viz.chart_type, cfg, data) : false;

  return (
    <Card className="overflow-hidden border-border/60">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border/50 bg-muted/20">
        <h4 className="text-xs font-medium truncate">{viz.name}</h4>
        <div className="flex items-center gap-0.5 shrink-0">
          <IconButton
            icon={<RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />}
            tooltip="Refresh data"
            onClick={onRefresh}
            disabled={refreshing}
          />
          {data && renderChart && (
            <IconButton
              icon={<Maximize2 className="h-3.5 w-3.5" />}
              tooltip="Expand"
              onClick={() => onExpand(data)}
            />
          )}
        </div>
      </div>
      <div className="p-2">
        {!data ? (
          <div className="flex items-center justify-center h-[200px] text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin opacity-60" />
          </div>
        ) : renderChart && cfg?.x_column && cfg?.y_column ? (
          <ChartRenderer
            chartType={viz.chart_type}
            data={data}
            xColumn={cfg.x_column}
            yColumn={cfg.y_column}
            height={200}
          />
        ) : (
          <DataTable rows={data} maxHeight={200} />
        )}
      </div>
    </Card>
  );
}

function canRenderChart(
  chartType: string,
  cfg: { x_column?: string; y_column?: string } | null,
  rows: Record<string, any>[],
): boolean {
  const supported = new Set(["bar", "line", "area", "pie", "scatter"]);
  if (!supported.has(chartType)) return false;
  if (!cfg?.x_column || !cfg?.y_column) return false;
  if (!rows.length) return false;
  return rows.some((r) => {
    const v = r[cfg.y_column!];
    return v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));
  });
}

function DataTable({
  rows,
  maxHeight = 240,
}: {
  rows: Record<string, any>[];
  maxHeight?: number;
}) {
  if (!rows.length) {
    return (
      <div className="flex items-center justify-center h-[200px] text-xs text-muted-foreground">
        No rows.
      </div>
    );
  }
  const headers = Object.keys(rows[0]);
  return (
    <div className="overflow-auto" style={{ maxHeight }}>
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

