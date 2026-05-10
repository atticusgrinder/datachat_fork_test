import { useState, useRef, useCallback } from "react";
import { Upload, Loader2, Database, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import excelLogo from "@/assets/excel-logo.svg";
import duckdbLogo from "@/assets/duckdb-logo.svg";

const ACCEPT_MAP: Record<string, string> = {
  excel_csv: ".csv,.tsv,.xlsx,.xls",
  local_upload: ".parquet,.json,.ndjson",
  duckdb: ".duckdb,.db",
};

const LABEL_MAP: Record<string, { label: string; subtitle: string }> = {
  excel_csv: {
    label: "Drop a spreadsheet here or click to browse",
    subtitle: "CSV, TSV, or Excel files (max 50 MB)",
  },
  local_upload: {
    label: "Drop a file here or click to browse",
    subtitle: "Parquet, JSON, or NDJSON files (max 50 MB)",
  },
  duckdb: {
    label: "Drop a .duckdb file here or click to browse",
    subtitle: "Accepts .duckdb and .db files (max 50 MB)",
  },
};

interface FileUploadZoneProps {
  mode: "excel_csv" | "local_upload" | "duckdb";
  onFileSelected: (file: File) => void;
  isUploading: boolean;
  onBack?: () => void;
}

export default function FileUploadZone({ mode, onFileSelected, isUploading, onBack }: FileUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = ACCEPT_MAP[mode];
  const { label, subtitle } = LABEL_MAP[mode];

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  }, [onFileSelected]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  };

  const icon = mode === "duckdb" ? (
    <img src={duckdbLogo} alt="DuckDB" className="h-10 w-10 mx-auto mb-3" />
  ) : mode === "excel_csv" ? (
    <img src={excelLogo} alt="Excel" className="h-10 w-10 mx-auto mb-3" />
  ) : (
    <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
  );

  return (
    <div className="space-y-4">
      <div className="p-3 bg-green-500/5 border border-green-500/20 rounded-lg space-y-1">
        <div className="flex items-center gap-2 text-xs font-medium text-green-600 dark:text-green-400">
          <Shield className="h-3.5 w-3.5" />
          Your data is secure
        </div>
        <ul className="text-[10px] text-muted-foreground space-y-0.5 ml-5 list-disc">
          <li>Files are processed in memory and not stored on disk</li>
          <li>Data is never shared or logged</li>
        </ul>
      </div>
      <div
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
          isDragOver
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
        } ${isUploading ? "pointer-events-none opacity-60" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
        />
        {isUploading ? (
          <>
            <Loader2 className="h-10 w-10 mx-auto mb-3 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Loading file...</p>
          </>
        ) : (
          <>
            {icon}
            <p className="text-sm font-medium">{label}</p>
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          </>
        )}
      </div>
      {onBack && (
        <div className="flex gap-3">
          <Button variant="outline" onClick={onBack}>Back</Button>
        </div>
      )}
    </div>
  );
}
