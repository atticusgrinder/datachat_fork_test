import { useMemo } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

/**
 * Tremor-inspired color palette — muted, modern, cohesive.
 * Primary blue used for single-series charts; rest for multi-series/categorical.
 */
const CHART_COLORS = [
  "var(--chart-blue, #3b82f6)",
  "var(--chart-cyan, #06b6d4)",
  "var(--chart-violet, #8b5cf6)",
  "var(--chart-amber, #f59e0b)",
  "var(--chart-emerald, #10b981)",
  "var(--chart-rose, #f43f5e)",
  "var(--chart-indigo, #6366f1)",
  "var(--chart-teal, #14b8a6)",
];

/** Resolved hex fallbacks for gradient defs (can't use CSS vars in SVG stops reliably) */
const CHART_COLORS_HEX = [
  "#3b82f6",
  "#06b6d4",
  "#8b5cf6",
  "#f59e0b",
  "#10b981",
  "#f43f5e",
  "#6366f1",
  "#14b8a6",
];

interface ChartRendererProps {
  chartType: string;
  data: Record<string, any>[];
  xColumn: string;
  yColumn: string;
  height?: number;
}

function formatValue(value: any): string {
  if (typeof value === "number") {
    if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toFixed(2);
  }
  return String(value);
}

function formatAxisValue(value: any): string {
  if (typeof value === "number") {
    if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toFixed(1);
  }
  return String(value);
}

function truncateLabel(label: string, maxLen = 14): string {
  if (label.length <= maxLen) return label;
  return label.slice(0, maxLen) + "…";
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{String(label)}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="chart-tooltip-row">
          <span
            className="chart-tooltip-dot"
            style={{ backgroundColor: entry.color }}
          />
          <span className="chart-tooltip-name">{entry.name}</span>
          <span className="chart-tooltip-value">{formatValue(entry.value)}</span>
        </div>
      ))}
    </div>
  );
};

const DonutTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-row">
        <span
          className="chart-tooltip-dot"
          style={{ backgroundColor: entry.payload?.fill }}
        />
        <span className="chart-tooltip-name">{entry.name}</span>
        <span className="chart-tooltip-value">{formatValue(entry.value)}</span>
      </div>
    </div>
  );
};

export default function ChartRenderer({
  chartType,
  data,
  xColumn,
  yColumn,
  height = 280,
}: ChartRendererProps) {
  const chartData = useMemo(() => {
    return data.map((row) => ({
      ...row,
      [xColumn]: row[xColumn],
      [yColumn]:
        typeof row[yColumn] === "string"
          ? parseFloat(row[yColumn]) || 0
          : row[yColumn],
    }));
  }, [data, xColumn, yColumn]);

  const axisStyle = {
    tick: { fontSize: 11, fill: "hsl(var(--muted-foreground))" },
    axisLine: false as const,
    tickLine: false as const,
  };

  if (chartType === "bar") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 4, bottom: 4, left: -8 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="hsl(var(--border))"
            strokeOpacity={0.4}
            strokeDasharray=""
          />
          <XAxis
            dataKey={xColumn}
            {...axisStyle}
            tickFormatter={(v) => truncateLabel(String(v))}
            tickMargin={8}
          />
          <YAxis {...axisStyle} tickFormatter={formatAxisValue} tickMargin={4} />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }}
          />
          <Bar
            dataKey={yColumn}
            fill={CHART_COLORS[0]}
            radius={[4, 4, 0, 0]}
            maxBarSize={48}
          />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={chartData}
          margin={{ top: 8, right: 4, bottom: 4, left: -8 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="hsl(var(--border))"
            strokeOpacity={0.4}
            strokeDasharray=""
          />
          <XAxis
            dataKey={xColumn}
            {...axisStyle}
            tickFormatter={(v) => truncateLabel(String(v))}
            tickMargin={8}
          />
          <YAxis {...axisStyle} tickFormatter={formatAxisValue} tickMargin={4} />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ stroke: "hsl(var(--muted-foreground))", strokeWidth: 1, strokeDasharray: "4 4" }}
          />
          <Line
            type="monotone"
            dataKey={yColumn}
            stroke={CHART_COLORS_HEX[0]}
            strokeWidth={2}
            dot={false}
            activeDot={{
              r: 4,
              fill: CHART_COLORS_HEX[0],
              stroke: "hsl(var(--background))",
              strokeWidth: 2,
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "area") {
    const gradientId = `area-gradient-${yColumn}`;
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={chartData}
          margin={{ top: 8, right: 4, bottom: 4, left: -8 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="hsl(var(--border))"
            strokeOpacity={0.4}
            strokeDasharray=""
          />
          <XAxis
            dataKey={xColumn}
            {...axisStyle}
            tickFormatter={(v) => truncateLabel(String(v))}
            tickMargin={8}
          />
          <YAxis {...axisStyle} tickFormatter={formatAxisValue} tickMargin={4} />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ stroke: "hsl(var(--muted-foreground))", strokeWidth: 1, strokeDasharray: "4 4" }}
          />
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS_HEX[0]} stopOpacity={0.25} />
              <stop offset="100%" stopColor={CHART_COLORS_HEX[0]} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey={yColumn}
            stroke={CHART_COLORS_HEX[0]}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{
              r: 4,
              fill: CHART_COLORS_HEX[0],
              stroke: "hsl(var(--background))",
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "pie") {
    // On small cards (e.g. Saved Visualizations grid) outer labels overflow the
    // SVG and get clipped. Only show outer labels at >=260px height; otherwise
    // rely on the legend below.
    const isCompact = height < 260;
    const innerRadius = height * (isCompact ? 0.22 : 0.18);
    const outerRadius = height * (isCompact ? 0.42 : 0.32);

    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart
          margin={
            isCompact
              ? { top: 8, right: 8, bottom: 8, left: 8 }
              : { top: 40, right: 40, bottom: 20, left: 40 }
          }
        >
          <Pie
            data={chartData}
            dataKey={yColumn}
            nameKey={xColumn}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            strokeWidth={0}
            label={
              isCompact
                ? false
                : ({ name, percent }) =>
                    `${truncateLabel(String(name), 12)} ${(percent * 100).toFixed(0)}%`
            }
            labelLine={
              isCompact
                ? false
                : {
                    stroke: "hsl(var(--muted-foreground))",
                    strokeWidth: 1,
                    strokeOpacity: 0.5,
                  }
            }
          >
            {chartData.map((_, index) => (
              <Cell
                key={index}
                fill={CHART_COLORS_HEX[index % CHART_COLORS_HEX.length]}
              />
            ))}
          </Pie>
          <Tooltip content={<DonutTooltip />} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{
              fontSize: 11,
              color: "hsl(var(--muted-foreground))",
              paddingTop: 8,
            }}
            formatter={(value: string) => (
              <span style={{ color: "hsl(var(--foreground))", fontSize: 11 }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "scatter") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 8, right: 4, bottom: 4, left: -8 }}>
          <CartesianGrid
            vertical={false}
            stroke="hsl(var(--border))"
            strokeOpacity={0.4}
            strokeDasharray=""
          />
          <XAxis
            dataKey={xColumn}
            name={xColumn}
            {...axisStyle}
            tickFormatter={formatAxisValue}
            tickMargin={8}
          />
          <YAxis
            dataKey={yColumn}
            name={yColumn}
            {...axisStyle}
            tickFormatter={formatAxisValue}
            tickMargin={4}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ strokeDasharray: "4 4" }}
          />
          <Scatter
            data={chartData}
            fill={CHART_COLORS_HEX[0]}
            fillOpacity={0.7}
            r={5}
          />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  return (
    <div className="text-sm text-muted-foreground p-4">
      Unsupported chart type: {chartType}
    </div>
  );
}
