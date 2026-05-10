import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import IntegrationBox from "@/components/IntegrationBox";
import { toast } from "sonner";
import {
  ArrowLeft,
  FileText,
  Loader2,
  Save,
  Trash2,
} from "lucide-react";

const DEFAULT_CONTEXT_TEMPLATE = `# Context

Add background information about your data, team, and business that helps the assistant give better answers.

## Preferences
- Preferred date formats
- Default chart styles
- SQL dialect preferences

## Glossary
- MRR = Monthly Recurring Revenue
- DAU = Daily Active Users
`;

export default function ContextPage() {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [isDirty, setIsDirty] = useState(false);

  const { data: contextFiles, isLoading: loadingFiles } = useQuery({
    queryKey: ["context-files"],
    queryFn: api.listContextFiles,
  });

  const { data: integrations } = useQuery({
    queryKey: ["integrations"],
    queryFn: api.listIntegrations,
  });

  const userFiles =
    contextFiles?.files.filter((f) => f.source === "user") || [];
  const dbtFiles =
    contextFiles?.files.filter((f) => f.source === "integration") || [];
  const allFiles = [...userFiles, ...dbtFiles];

  const currentFile = allFiles.find((f) => f.filename === selectedFile);
  const isUserFile = currentFile?.source === "user";

  // Auto-select context.md on load
  useEffect(() => {
    if (!selectedFile && allFiles.length > 0) {
      const contextMd = allFiles.find((f) => f.filename === "context.md");
      setSelectedFile(contextMd ? "context.md" : allFiles[0].filename);
    }
  }, [allFiles.length, selectedFile]);

  // Load file content when selection changes
  // Treat default template as empty so placeholder shows instead
  useEffect(() => {
    if (currentFile) {
      const isTemplate = currentFile.content.trim() === DEFAULT_CONTEXT_TEMPLATE.trim();
      setEditorContent(isTemplate ? "" : currentFile.content);
      setIsDirty(false);
    }
  }, [selectedFile, currentFile?.content]);

  const saveMutation = useMutation({
    mutationFn: (content: string) =>
      api.updateContextFile(selectedFile!, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["context-files"] });
      setIsDirty(false);
      toast.success("Context saved");
    },
    onError: () => toast.error("Failed to save context"),
  });

  // Cmd+S / Ctrl+S to save
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (isDirty && selectedFile && isUserFile) {
          saveMutation.mutate(editorContent);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isDirty, selectedFile, isUserFile, editorContent, saveMutation]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/chat">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <span className="font-semibold">Context</span>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex gap-6 min-h-[500px]">
          {/* Left panel - File list + dbt integrations */}
          <div className="w-64 shrink-0 space-y-4">
            {/* File list */}
            <div className="border rounded-lg p-4 bg-card">
              <div className="mb-2">
                <h3 className="text-base font-bold">Files</h3>
              </div>
              {loadingFiles ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-0.5">
                  {allFiles.map((file) => (
                    <button
                      key={file.filename}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-left transition-colors ${
                        selectedFile === file.filename
                          ? "text-foreground font-medium hover:bg-accent/50 cursor-pointer"
                          : "hover:bg-accent/50 text-foreground cursor-pointer"
                      }`}
                      onClick={() => setSelectedFile(file.filename)}
                    >
                      <FileText className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{file.filename}</span>
                      {selectedFile === file.filename &&
                        file.source === "user" &&
                        file.filename !== "context.md" && (
                          <Trash2 className="h-3 w-3 ml-auto shrink-0 text-destructive opacity-60 hover:opacity-100" />
                        )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <IntegrationBox
              integrationType="dbt"
              label="dbt"
              dialogTitle="Connect dbt Project"
              namePlaceholder="My dbt Project"
              repoUrlHint="Copy from GitHub → your repo → Code → HTTPS clone URL. Must contain a compiled target/manifest.json."
              integrations={integrations}
              onDeleted={() => setSelectedFile(null)}
            />

            <IntegrationBox
              integrationType="omni"
              label="Omni"
              dialogTitle="Connect Omni Project"
              namePlaceholder="My Omni Project"
              repoUrlHint="Copy from GitHub → your Omni repo → Code → HTTPS clone URL. Must contain Omni view/model YAML files."
              integrations={integrations}
              onDeleted={() => setSelectedFile(null)}
            />
          </div>

          {/* Right panel - File editor */}
          <div className="flex-1 border rounded-lg flex flex-col min-h-0 bg-card">
            {selectedFile ? (
              <>
                <div className="flex items-center justify-between px-4 py-3 border-b">
                  <h3 className="font-bold text-base">{selectedFile}</h3>
                  {isUserFile && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      disabled={!isDirty || saveMutation.isPending}
                      onClick={() => saveMutation.mutate(editorContent)}
                    >
                      {saveMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Save className="h-3.5 w-3.5" />
                      )}
                      Save
                    </Button>
                  )}
                </div>
                <div className="flex-1 p-4">
                  {isUserFile ? (
                    <textarea
                      className="w-full h-full min-h-[480px] text-xs font-mono bg-background border border-border rounded-md p-3 resize-y focus:outline-none focus:ring-1 focus:ring-ring"
                      value={editorContent}
                      onChange={(e) => {
                        setEditorContent(e.target.value);
                        setIsDirty(true);
                      }}
                      placeholder={`# Context\n\nAdd background information about your data, team, and business that helps the assistant give better answers.\n\n## Preferences\n- Preferred date formats\n- Default chart styles\n- SQL dialect preferences\n\n## Glossary\n- MRR = Monthly Recurring Revenue\n- DAU = Daily Active Users`}
                    />
                  ) : (
                    <pre className="w-full h-full min-h-[480px] text-xs font-mono bg-background border border-border rounded-md p-3 overflow-auto whitespace-pre-wrap">
                      {editorContent}
                    </pre>
                  )}
                </div>
                {isUserFile && (
                  <div className="px-4 pb-3 text-xs text-muted-foreground">
                    {editorContent.length.toLocaleString()} / 51,200 characters
                  </div>
                )}
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Select a file to edit</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
