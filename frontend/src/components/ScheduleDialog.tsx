import { useEffect, useState } from "react";
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
import { Report, ReportCadence } from "@/lib/api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  report: Report | null;
  onSubmit: (data: {
    cadence: ReportCadence;
    time_of_day: string;
    timezone: string;
    day_of_week?: number | null;
    day_of_month?: number | null;
    enabled: boolean;
  }) => Promise<unknown> | unknown;
  onDisable?: () => Promise<unknown> | unknown;
}

const COMMON_TIMEZONES = [
  "UTC",
  "America/Los_Angeles",
  "America/Denver",
  "America/Chicago",
  "America/New_York",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const WEEKDAYS = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];

function detectLocalTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export default function ScheduleDialog({ open, onOpenChange, report, onSubmit, onDisable }: Props) {
  const existing = report?.schedule ?? null;
  const [cadence, setCadence] = useState<ReportCadence>(existing?.cadence ?? "weekly");
  const [time, setTime] = useState<string>(existing?.time_of_day ?? "09:00");
  const [tz, setTz] = useState<string>(existing?.timezone ?? detectLocalTimezone());
  const [dayOfWeek, setDayOfWeek] = useState<number>(existing?.day_of_week ?? 0);
  const [dayOfMonth, setDayOfMonth] = useState<number>(existing?.day_of_month ?? 1);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCadence(existing?.cadence ?? "weekly");
    setTime(existing?.time_of_day ?? "09:00");
    setTz(existing?.timezone ?? detectLocalTimezone());
    setDayOfWeek(existing?.day_of_week ?? 0);
    setDayOfMonth(existing?.day_of_month ?? 1);
  }, [open, report?.id]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        cadence,
        time_of_day: time,
        timezone: tz,
        day_of_week: cadence === "weekly" ? dayOfWeek : null,
        day_of_month: cadence === "monthly" ? dayOfMonth : null,
        enabled: true,
      });
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  const tzOptions = Array.from(new Set([...COMMON_TIMEZONES, detectLocalTimezone()]));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{existing ? "Edit schedule" : "Schedule report"}</DialogTitle>
          <DialogDescription>
            Reports are emailed to your account email only. Choose a cadence and time.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Cadence</Label>
            <Select value={cadence} onValueChange={(v) => setCadence(v as ReportCadence)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {cadence === "weekly" && (
            <div className="space-y-2">
              <Label>Day of week</Label>
              <Select value={String(dayOfWeek)} onValueChange={(v) => setDayOfWeek(Number(v))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {WEEKDAYS.map((d) => (
                    <SelectItem key={d.value} value={String(d.value)}>{d.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {cadence === "monthly" && (
            <div className="space-y-2">
              <Label>Day of month</Label>
              <Input
                type="number"
                min={1}
                max={28}
                value={dayOfMonth}
                onChange={(e) => setDayOfMonth(Number(e.target.value))}
              />
              <p className="text-xs text-muted-foreground">
                Limited to 1–28 to handle short months consistently.
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Time of day</Label>
              <Input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Timezone</Label>
              <Select value={tz} onValueChange={setTz}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {tzOptions.map((z) => (
                    <SelectItem key={z} value={z}>{z}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter className="flex flex-row items-center justify-between sm:justify-between">
          <div>
            {existing && onDisable && (
              <Button
                variant="ghost"
                className="text-destructive hover:text-destructive"
                onClick={() => {
                  onDisable();
                  onOpenChange(false);
                }}
              >
                Disable schedule
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving..." : "Save schedule"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
