import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Integration } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  Eye,
  EyeOff,
  GitBranch,
  Info,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";

interface IntegrationBoxProps {
  integrationType: string;
  label: string;
  dialogTitle: string;
  namePlaceholder: string;
  repoUrlHint: string;
  integrations: Integration[] | undefined;
  onDeleted?: () => void;
}

export default function IntegrationBox({
  integrationType,
  label,
  dialogTitle,
  namePlaceholder,
  repoUrlHint,
  integrations,
  onDeleted,
}: IntegrationBoxProps) {
  const queryClient = useQueryClient();
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [formName, setFormName] = useState("");
  const [formRepoUrl, setFormRepoUrl] = useState("");
  const [formBranch, setFormBranch] = useState("main");
  const [formAuthToken, setFormAuthToken] = useState("");
  const [showToken, setShowToken] = useState(false);

  const filtered =
    integrations?.filter((i) => i.integration_type === integrationType) || [];

  const createMutation = useMutation({
    mutationFn: (data: {
      integration_type: string;
      name: string;
      config: { repo_url: string; branch?: string; auth_token?: string };
    }) => api.createIntegration(data),
    onSuccess: (integration) => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      setShowAddDialog(false);
      setFormName("");
      setFormRepoUrl("");
      setFormBranch("main");
      setFormAuthToken("");
      toast.success("Integration created");
      syncMutation.mutate(integration.id);
    },
    onError: () => toast.error("Failed to create integration"),
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => api.syncIntegration(id),
    onSuccess: (sync) => {
      queryClient.invalidateQueries({ queryKey: ["context-files"] });
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      if (sync.status === "completed") {
        toast.success(`Synced ${sync.metadata_count} items`);
      } else {
        toast.error(sync.error_message || "Sync failed");
      }
    },
    onError: () => toast.error("Sync failed"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["context-files"] });
      onDeleted?.();
      toast.success("Integration deleted");
    },
    onError: () => toast.error("Failed to delete integration"),
  });

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
          <h3 className="text-base font-bold">{label}</h3>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{dialogTitle}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Label>Name</Label>
                  <div className="relative group">
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                    <div className="absolute left-5 top-1/2 -translate-y-1/2 z-50 hidden group-hover:block w-64 px-3 py-1.5 text-sm rounded-md border bg-popover text-popover-foreground shadow-md">
                      Any name you want — e.g. your repo name
                    </div>
                  </div>
                </div>
                <Input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder={namePlaceholder}
                />
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Label>Repository URL</Label>
                  <div className="relative group">
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                    <div className="absolute left-5 top-1/2 -translate-y-1/2 z-50 hidden group-hover:block w-64 px-3 py-1.5 text-sm rounded-md border bg-popover text-popover-foreground shadow-md">
                      {repoUrlHint}
                    </div>
                  </div>
                </div>
                <Input
                  value={formRepoUrl}
                  onChange={(e) => setFormRepoUrl(e.target.value)}
                  placeholder="https://github.com/org/repo.git"
                />
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Label>Branch</Label>
                  <div className="relative group">
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                    <div className="absolute left-5 top-1/2 -translate-y-1/2 z-50 hidden group-hover:block w-64 px-3 py-1.5 text-sm rounded-md border bg-popover text-popover-foreground shadow-md">
                      Check your repo's default branch in GitHub — usually "main" or "master"
                    </div>
                  </div>
                </div>
                <Input
                  value={formBranch}
                  onChange={(e) => setFormBranch(e.target.value)}
                  placeholder="main"
                />
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Label>Auth Token</Label>
                  <div className="relative group">
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                    <div className="absolute left-5 top-1/2 -translate-y-1/2 z-50 hidden group-hover:block w-64 px-3 py-1.5 text-sm rounded-md border bg-popover text-popover-foreground shadow-md">
                      GitHub → Settings → Developer settings → Personal access tokens → Fine-grained → select your repo → Contents: Read-only
                    </div>
                  </div>
                </div>
                <div className="relative">
                  <Input
                    type={showToken ? "text" : "password"}
                    value={formAuthToken}
                    onChange={(e) => setFormAuthToken(e.target.value)}
                    placeholder="ghp_..."
                  />
                  <button
                    type="button"
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
                    onClick={() => setShowToken(!showToken)}
                  >
                    {showToken ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
              <Button
                className="w-full"
                disabled={
                  !formName || !formRepoUrl || createMutation.isPending
                }
                onClick={() =>
                  createMutation.mutate({
                    integration_type: integrationType,
                    name: formName,
                    config: {
                      repo_url: formRepoUrl,
                      branch: formBranch || "main",
                      ...(formAuthToken ? { auth_token: formAuthToken } : {}),
                    },
                  })
                }
              >
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                Connect & Sync
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      {filtered.length > 0 ? (
        <div className="space-y-2">
          {filtered.map((integration) => (
            <div
              key={integration.id}
              className="flex items-center justify-between text-sm"
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="truncate">{integration.name}</span>
                <span className="text-[10px] text-muted-foreground">
                  ({integration.connection_status})
                </span>
              </div>
              <div className="flex items-center gap-0.5 shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  disabled={syncMutation.isPending}
                  onClick={() => syncMutation.mutate(integration.id)}
                >
                  <RefreshCw
                    className={`h-3 w-3 ${
                      syncMutation.isPending ? "animate-spin" : ""
                    }`}
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 text-destructive"
                  onClick={() => deleteMutation.mutate(integration.id)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No projects connected.</p>
      )}
    </div>
  );
}
