import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  GitBranch,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  Eye,
  EyeOff,
  Loader2,
} from "lucide-react";

export default function ContextPanel() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [editorContent, setEditorContent] = useState("");
  const [isDirty, setIsDirty] = useState(false);
  const [expandedDbtFile, setExpandedDbtFile] = useState<string | null>(null);
  const [dialogType, setDialogType] = useState<"dbt" | "omni" | null>(null);
  const [formName, setFormName] = useState("");
  const [formRepoUrl, setFormRepoUrl] = useState("");
  const [formBranch, setFormBranch] = useState("main");
  const [formAuthToken, setFormAuthToken] = useState("");
  const [showToken, setShowToken] = useState(false);

  const { data: contextFiles } = useQuery({
    queryKey: ["context-files"],
    queryFn: api.listContextFiles,
    enabled: expanded,
  });

  const { data: integrations } = useQuery({
    queryKey: ["integrations"],
    queryFn: api.listIntegrations,
    enabled: expanded,
  });

  const userFile = contextFiles?.files.find(
    (f) => f.source === "user" && f.filename === "context.md"
  );
  const integrationFiles = contextFiles?.files.filter((f) => f.source === "integration") || [];

  // Sync editor content when data loads
  useEffect(() => {
    if (userFile && !isDirty) {
      setEditorContent(userFile.content);
    }
  }, [userFile, isDirty]);

  const saveMutation = useMutation({
    mutationFn: (content: string) => api.updateContextFile("context.md", content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["context-files"] });
      setIsDirty(false);
      toast.success("Context saved");
    },
    onError: () => toast.error("Failed to save context"),
  });

  const createIntegrationMutation = useMutation({
    mutationFn: (data: { integration_type: string; name: string; config: { repo_url: string; branch?: string; auth_token?: string } }) =>
      api.createIntegration(data),
    onSuccess: (integration) => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      setDialogType(null);
      setFormName("");
      setFormRepoUrl("");
      setFormBranch("main");
      setFormAuthToken("");
      toast.success("Integration created");
      // Auto-sync
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
        toast.success(`Synced ${sync.metadata_count} models`);
      } else {
        toast.error(sync.error_message || "Sync failed");
      }
    },
    onError: () => toast.error("Sync failed"),
  });

  const deleteIntegrationMutation = useMutation({
    mutationFn: (id: string) => api.deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["context-files"] });
      toast.success("Integration deleted");
    },
    onError: () => toast.error("Failed to delete integration"),
  });

  const totalFiles = (contextFiles?.files.length || 0);

  return (
    <div className="border-b" data-context-panel>
      {/* Collapsed bar */}
      <button
        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" />
        )}
        <FileText className="h-3.5 w-3.5" />
        <span>Context</span>
        {totalFiles > 0 && (
          <span className="text-xs bg-muted rounded-full px-1.5 py-0.5">
            {totalFiles} {totalFiles === 1 ? "file" : "files"}
          </span>
        )}
      </button>

      {/* Expanded panel */}
      {expanded && (
        <div className="px-4 pb-3 space-y-3">
          {/* User context editor */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-muted-foreground">context.md</label>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs gap-1"
                disabled={!isDirty || saveMutation.isPending}
                onClick={() => saveMutation.mutate(editorContent)}
              >
                {saveMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Save className="h-3 w-3" />
                )}
                Save
              </Button>
            </div>
            <textarea
              className="w-full h-32 text-xs font-mono bg-muted/50 border rounded-md p-2 resize-y focus:outline-none focus:ring-1 focus:ring-ring"
              value={editorContent}
              onChange={(e) => {
                setEditorContent(e.target.value);
                setIsDirty(true);
              }}
              placeholder="Add context about your data, team, and business..."
            />
          </div>

          {/* Integration files (dbt + omni) */}
          {integrationFiles.map((file) => {
            const integration = integrations?.find(
              (i) => i.id === file.integration_id
            );
            const isExpanded = expandedDbtFile === file.filename;
            return (
              <div key={file.id} className="border rounded-md">
                <div className="flex items-center gap-2 px-2 py-1.5">
                  <button
                    className="flex items-center gap-1.5 flex-1 text-left text-xs"
                    onClick={() =>
                      setExpandedDbtFile(isExpanded ? null : file.filename)
                    }
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    <GitBranch className="h-3 w-3 text-muted-foreground" />
                    <span className="font-medium">{file.filename}</span>
                    {integration && (
                      <span className="text-muted-foreground">
                        ({integration.connection_status})
                      </span>
                    )}
                  </button>
                  <div className="flex items-center gap-1">
                    {integration && (
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
                    )}
                    {integration && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-destructive"
                        onClick={() =>
                          deleteIntegrationMutation.mutate(integration.id)
                        }
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </div>
                {isExpanded && (
                  <pre className="text-xs font-mono bg-muted/30 p-2 border-t max-h-48 overflow-auto whitespace-pre-wrap">
                    {file.content}
                  </pre>
                )}
              </div>
            );
          })}

          {/* Connect buttons */}
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs gap-1"
            onClick={() => setDialogType("dbt")}
          >
            <Plus className="h-3 w-3" />
            Connect dbt Project
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs gap-1"
            onClick={() => setDialogType("omni")}
          >
            <Plus className="h-3 w-3" />
            Connect Omni Project
          </Button>

          <Dialog
            open={dialogType !== null}
            onOpenChange={(open) => !open && setDialogType(null)}
          >
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  Connect {dialogType === "omni" ? "Omni" : "dbt"} Project
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div>
                  <Label>Name</Label>
                  <Input
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder={
                      dialogType === "omni" ? "My Omni Project" : "My dbt Project"
                    }
                  />
                </div>
                <div>
                  <Label>Repository URL</Label>
                  <Input
                    value={formRepoUrl}
                    onChange={(e) => setFormRepoUrl(e.target.value)}
                    placeholder="https://github.com/org/repo.git"
                  />
                </div>
                <div>
                  <Label>Branch</Label>
                  <Input
                    value={formBranch}
                    onChange={(e) => setFormBranch(e.target.value)}
                    placeholder="main"
                  />
                </div>
                <div>
                  <Label>Auth Token (optional)</Label>
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
                    !formName ||
                    !formRepoUrl ||
                    !dialogType ||
                    createIntegrationMutation.isPending
                  }
                  onClick={() =>
                    createIntegrationMutation.mutate({
                      integration_type: dialogType!,
                      name: formName,
                      config: {
                        repo_url: formRepoUrl,
                        branch: formBranch || "main",
                        ...(formAuthToken ? { auth_token: formAuthToken } : {}),
                      },
                    })
                  }
                >
                  {createIntegrationMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : null}
                  Connect & Sync
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      )}
    </div>
  );
}
