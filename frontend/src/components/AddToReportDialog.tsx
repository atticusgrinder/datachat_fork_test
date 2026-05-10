import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, SavedVisualization } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  visualization: SavedVisualization | null;
}

export default function AddToReportDialog({ open, onOpenChange, visualization }: Props) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [newName, setNewName] = useState<string>("");

  const { data: reports } = useQuery({
    queryKey: ["reports"],
    queryFn: api.listReports,
    enabled: open,
  });

  const addToExisting = useMutation({
    mutationFn: () =>
      api.addReportItem(selectedReportId, visualization!.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Added to report");
      onOpenChange(false);
    },
    onError: (e: any) => toast.error(e?.message || "Failed to add"),
  });

  const createAndAdd = useMutation({
    mutationFn: async () => {
      const report = await api.createReport({
        name: newName,
        warehouse_id: visualization?.warehouse_id ?? undefined,
      });
      await api.addReportItem(report.id, visualization!.id);
      return report;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      toast.success("Report created");
      onOpenChange(false);
    },
    onError: (e: any) => toast.error(e?.message || "Failed to create report"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add to report</DialogTitle>
          <DialogDescription>
            Add this visualization to an existing scheduled report, or create a new one.
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-2">
          <Button
            variant={mode === "existing" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("existing")}
          >
            Existing report
          </Button>
          <Button
            variant={mode === "new" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("new")}
          >
            New report
          </Button>
        </div>

        {mode === "existing" ? (
          <div className="space-y-2 py-2">
            <Label>Report</Label>
            {reports && reports.length > 0 ? (
              <Select value={selectedReportId} onValueChange={setSelectedReportId}>
                <SelectTrigger><SelectValue placeholder="Pick a report..." /></SelectTrigger>
                <SelectContent>
                  {reports.map((r) => (
                    <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <p className="text-sm text-muted-foreground">
                You don't have any reports yet. Switch to "New report" to create one.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-2 py-2">
            <Label>Report name</Label>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Weekly Sales Digest"
              autoFocus
            />
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          {mode === "existing" ? (
            <Button
              onClick={() => addToExisting.mutate()}
              disabled={!selectedReportId || addToExisting.isPending}
            >
              {addToExisting.isPending ? "Adding..." : "Add"}
            </Button>
          ) : (
            <Button
              onClick={() => createAndAdd.mutate()}
              disabled={!newName.trim() || createAndAdd.isPending}
            >
              {createAndAdd.isPending ? "Creating..." : "Create & add"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
