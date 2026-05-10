import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface VisualizationConfig {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string;
}

interface SaveVisualizationModalProps {
  visualization: VisualizationConfig;
  chartData: Record<string, any>[];
  sqlQuery: string;
  warehouseId?: string | null;
  localDuckdbId?: string | null;
  onSave: (data: {
    name: string;
    description: string;
    chart_type: string;
    chart_config: string;
    sql_query: string;
    warehouse_id?: string;
    local_duckdb_id?: string;
  }) => void;
  onClose: () => void;
  isSaving?: boolean;
}

export default function SaveVisualizationModal({
  visualization,
  chartData,
  sqlQuery,
  warehouseId,
  localDuckdbId,
  onSave,
  onClose,
  isSaving,
}: SaveVisualizationModalProps) {
  const [name, setName] = useState(visualization.title);
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    onSave({
      name: name.trim(),
      description: description.trim(),
      chart_type: visualization.chart_type,
      chart_config: JSON.stringify({
        x_column: visualization.x_column,
        y_column: visualization.y_column,
        title: visualization.title,
      }),
      sql_query: sqlQuery,
      warehouse_id: warehouseId || undefined,
      local_duckdb_id: localDuckdbId || undefined,
    });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Save Visualization</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="viz-name">Name</Label>
            <Input
              id="viz-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Chart name"
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="viz-desc">Description (optional)</Label>
            <Textarea
              id="viz-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this visualization show?"
              rows={2}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isSaving}>
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
