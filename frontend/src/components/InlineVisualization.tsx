import { useState } from "react";
import { Button } from "@/components/ui/button";
import ChartRenderer from "@/components/ChartRenderer";
import VisualizationExpandModal from "@/components/VisualizationExpandModal";
import {
  Maximize2,
  Save,
  Table as TableIcon,
  BarChart3,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface VisualizationConfig {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string;
  reasoning?: string;
}

interface InlineVisualizationProps {
  visualization: VisualizationConfig;
  chartData: Record<string, any>[];
  onSave?: () => void;
}

const CHART_TYPE_LABELS: Record<string, string> = {
  bar: "Bar",
  line: "Line",
  area: "Area",
  pie: "Donut",
  scatter: "Scatter",
};

export default function InlineVisualization({
  visualization,
  chartData,
  onSave,
}: InlineVisualizationProps) {
  const [showTable, setShowTable] = useState(false);
  const [expanded, setExpanded] = useState(false);

  if (!chartData || chartData.length === 0) return null;

  const columns = Object.keys(chartData[0]);

  return (
    <>
      <div className="mt-3 mb-3 rounded-xl border border-border/60 bg-card/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <h4 className="text-[13px] font-medium text-foreground truncate">
              {visualization.title}
            </h4>
          </div>
          <div className="flex items-center gap-0.5 shrink-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowTable(!showTable)}
                >
                  {showTable ? (
                    <BarChart3 className="h-3.5 w-3.5" />
                  ) : (
                    <TableIcon className="h-3.5 w-3.5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{showTable ? "Show chart" : "Show data table"}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={() => setExpanded(true)}
                >
                  <Maximize2 className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Expand</TooltipContent>
            </Tooltip>
            {onSave && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-foreground"
                    onClick={onSave}
                  >
                    <Save className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Save visualization</TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="px-2 pb-3">
          {showTable ? (
            <div className="max-h-[280px] overflow-auto rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    {columns.map((col) => (
                      <TableHead key={col} className="text-xs py-1.5 px-3">
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {chartData.slice(0, 50).map((row, i) => (
                    <TableRow key={i}>
                      {columns.map((col) => (
                        <TableCell key={col} className="text-xs py-1.5 px-3">
                          {typeof row[col] === "number"
                            ? row[col].toLocaleString()
                            : String(row[col] ?? "")}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {chartData.length > 50 && (
                <p className="text-[10px] text-muted-foreground text-center py-1.5">
                  Showing 50 of {chartData.length} rows
                </p>
              )}
            </div>
          ) : (
            <ChartRenderer
              chartType={visualization.chart_type}
              data={chartData}
              xColumn={visualization.x_column}
              yColumn={visualization.y_column}
              height={280}
            />
          )}
        </div>
      </div>

      {expanded && (
        <VisualizationExpandModal
          visualization={visualization}
          chartData={chartData}
          onClose={() => setExpanded(false)}
        />
      )}
    </>
  );
}
