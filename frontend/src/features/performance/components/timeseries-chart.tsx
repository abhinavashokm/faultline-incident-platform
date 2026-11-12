"use client";

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { TimeseriesPoint } from "../types";

export type TimeseriesType = "bar" | "line";

export interface TimeseriesChartProps {
  title: string;
  subtitle?: string;
  data: TimeseriesPoint[];
  dataKey: "requests" | "error_rate" | "p95_ms";
  type: TimeseriesType;
  intervalSeconds: number;
  strokeColor?: string;
  fillColor?: string;
  unit?: string;
  formatter?: (val: number) => string;
  className?: string;
  height?: number;
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  } catch {
    return isoString;
  }
}

function defaultFormatter(val: number, key: string): string {
  if (val === null || val === undefined) return "—";
  if (key === "error_rate") return `${val.toFixed(2)}%`;
  if (key === "p95_ms") {
    return val >= 1000 ? `${(val / 1000).toFixed(2)}s` : `${val}ms`;
  }
  if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
  if (val >= 1000) return `${(val / 1000).toFixed(1)}k`;
  return val.toLocaleString();
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
  dataKey: string;
  formatter?: (val: number) => string;
  unit?: string;
}

function CustomTooltip({ active, payload, label, dataKey, formatter }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    const item = payload[0];
    const rawVal = item.value;
    const formatted =
      rawVal === null || rawVal === undefined
        ? "No traffic"
        : formatter
        ? formatter(rawVal)
        : defaultFormatter(rawVal, dataKey);

    return (
      <div className="rounded-lg bg-[#131b2e] px-3 py-2 text-white shadow-xl border border-[#283044] text-xs font-mono select-none pointer-events-none z-50">
        <div className="text-[#a0aec0] text-[11px] mb-0.5">{label}</div>
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: item.stroke || item.fill || "#0058be" }}
          />
          <span className="font-semibold text-white tabular-nums">{formatted}</span>
        </div>
      </div>
    );
  }
  return null;
}

export function TimeseriesChart({
  title,
  subtitle,
  data,
  dataKey,
  type,
  intervalSeconds,
  strokeColor = "#0058be",
  fillColor = "#0058be",
  unit,
  formatter,
  height = 140,
}: TimeseriesChartProps) {
  const chartData = React.useMemo(() => {
    return data.map((pt) => ({
      ...pt,
      formattedTime: formatTime(pt.t),
    }));
  }, [data]);

  // Tick calculation: display roughly 6-8 evenly spaced ticks along the timeline
  const tickIndices = React.useMemo(() => {
    if (chartData.length <= 6) return chartData.map((d) => d.formattedTime);
    const step = Math.ceil(chartData.length / 6);
    return chartData.filter((_, idx) => idx % step === 0).map((d) => d.formattedTime);
  }, [chartData]);

  return (
    <div className="bg-card rounded-2xl border border-border p-5 shadow-xs relative transition-all">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary tracking-tight">{title}</h3>
        {subtitle && (
          <span className="text-xs font-mono text-text-secondary tabular-nums">{subtitle}</span>
        )}
      </div>

      <div style={{ width: "100%", height }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === "bar" ? (
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e4ee" vertical={false} opacity={0.6} />
              <XAxis
                dataKey="formattedTime"
                ticks={tickIndices}
                tick={{ fontSize: 11, fill: "#424754", fontFamily: "JetBrains Mono, monospace" }}
                axisLine={{ stroke: "#e2e4ee" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#424754", fontFamily: "JetBrains Mono, monospace" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)}
              />
              <Tooltip
                content={<CustomTooltip dataKey={dataKey} formatter={formatter} unit={unit} />}
                cursor={{ fill: "rgba(0, 88, 190, 0.05)" }}
              />
              <Bar
                dataKey={dataKey}
                fill={fillColor}
                radius={[3, 3, 0, 0]}
                maxBarSize={28}
                isAnimationActive={false}
              />
            </BarChart>
          ) : (
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e4ee" vertical={false} opacity={0.6} />
              <XAxis
                dataKey="formattedTime"
                ticks={tickIndices}
                tick={{ fontSize: 11, fill: "#424754", fontFamily: "JetBrains Mono, monospace" }}
                axisLine={{ stroke: "#e2e4ee" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#424754", fontFamily: "JetBrains Mono, monospace" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => {
                  if (dataKey === "error_rate") return `${v}%`;
                  if (dataKey === "p95_ms") return v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v}ms`;
                  return v;
                }}
              />
              <Tooltip
                content={<CustomTooltip dataKey={dataKey} formatter={formatter} unit={unit} />}
              />
              {/* connectNulls={false} ensures null values show as GAPS, not zero */}
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={strokeColor}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: strokeColor, strokeWidth: 2, fill: "#ffffff" }}
                connectNulls={false}
                isAnimationActive={false}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
