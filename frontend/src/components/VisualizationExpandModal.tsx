import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ChartRenderer from "@/components/ChartRenderer";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BarChart3, Table as TableIcon } from "lucide-react";

interface VisualizationConfig {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string;
  reasoning?: string;
}

interface VisualizationExpandModalProps {
  visualization: VisualizationConfig;
  chartData: Record<string, any>[];
  onClose: () => void;
}

export default function VisualizationExpandModal({
  visualization,
  chartData,
  onClose,
}: VisualizationExpandModalProps) {
  const [showTable, setShowTable] = useState(false);
  const columns = chartData.length > 0 ? Object.keys(chartData[0]) : [];

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col gap-0">
        <DialogHeader className="pb-4">
          <div className="flex items-center justify-between pr-8">
            <DialogTitle className="text-base font-medium">
              {visualization.title}
            </DialogTitle>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs h-8"
              onClick={() => setShowTable(!showTable)}
            >
              {showTable ? (
                <>
                  <BarChart3 className="h-3.5 w-3.5" />
                  Chart
                </>
              ) : (
                <>
                  <TableIcon className="h-3.5 w-3.5" />
                  Data
                </>
              )}
            </Button>
          </div>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-auto">
          {showTable ? (
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((col) => (
                    <TableHead key={col} className="text-xs">
                      {col}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {chartData.map((row, i) => (
                  <TableRow key={i}>
                    {columns.map((col) => (
                      <TableCell key={col} className="text-xs">
                        {typeof row[col] === "number"
                          ? row[col].toLocaleString()
                          : String(row[col] ?? "")}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <ChartRenderer
              chartType={visualization.chart_type}
              data={chartData}
              xColumn={visualization.x_column}
              yColumn={visualization.y_column}
              height={480}
            />
          )}
        </div>

      </DialogContent>
    </Dialog>
  );
}
