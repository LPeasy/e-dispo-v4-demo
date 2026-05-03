import { useEffect, useRef, useState, type ReactNode } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { HistogramBin, SensitivityResult } from "@/model/types"

export function HistogramChart({
  data,
  height = 288,
}: {
  data: HistogramBin[]
  height?: number
}) {
  return (
    <MeasuredChart height={height}>
      {(width, height) => (
        <BarChart
          width={width}
          height={height}
          data={data}
          barCategoryGap="18%"
          margin={{ top: 20, right: 18, bottom: 54, left: 12 }}
        >
          <CartesianGrid
            stroke="#d9e5ee"
            strokeDasharray="4 8"
            strokeOpacity={0.75}
            vertical={false}
          />
          <XAxis
            dataKey="range"
            axisLine={{ stroke: "#d9e5ee" }}
            tickLine={false}
            interval={1}
            minTickGap={8}
            tick={{ fill: "#607080", fontSize: 11 }}
            label={{
              value: "Simulated P(admit) range",
              position: "insideBottom",
              offset: -36,
              fill: "#607080",
              fontSize: 12,
            }}
          />
          <YAxis
            allowDecimals={false}
            axisLine={false}
            tickLine={false}
            width={48}
            tick={{ fill: "#607080", fontSize: 11 }}
            label={{
              value: "Model runs",
              angle: -90,
              position: "insideLeft",
              fill: "#607080",
              fontSize: 12,
            }}
          />
          <ChartTooltip
            content={<HistogramTooltip />}
            cursor={{ fill: "#2563eb", opacity: 0.08 }}
          />
          <Bar
            dataKey="count"
            fill="#2563eb"
            maxBarSize={42}
            radius={[8, 8, 2, 2]}
          />
        </BarChart>
      )}
    </MeasuredChart>
  )
}

export function SensitivityChart({ data }: { data: SensitivityResult[] }) {
  return (
    <MeasuredChart height={256}>
      {(width, height) => (
        <BarChart
          width={width}
          height={height}
          data={data.slice(0, 6)}
          layout="vertical"
          margin={{ left: 72 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} />
          <YAxis
            dataKey="parameter"
            type="category"
            width={120}
            tick={{ fontSize: 11 }}
          />
          <ChartTooltip />
          <Bar
            dataKey="absoluteCorrelation"
            fill="#2f6f9f"
            radius={[0, 4, 4, 0]}
          />
        </BarChart>
      )}
    </MeasuredChart>
  )
}

function HistogramTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value?: number | string }>
  label?: string
}) {
  if (!active || !payload?.length) {
    return null
  }

  const count = Number(payload[0]?.value ?? 0)

  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
      <p className="font-medium">P(admit) range: {label}</p>
      <p className="mt-1 text-muted-foreground">
        {count.toLocaleString()} simulated model estimates
      </p>
    </div>
  )
}

function MeasuredChart({
  height,
  children,
}: {
  height: number
  children: (width: number, height: number) => ReactNode
}) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    if (!ref.current) {
      return
    }

    const updateWidth = () => {
      setWidth(Math.max(0, Math.floor(ref.current?.clientWidth ?? 0)))
    }
    const observer = new ResizeObserver(updateWidth)
    observer.observe(ref.current)
    updateWidth()

    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref} className="h-full min-h-56 w-full min-w-0">
      {width > 0 ? (
        children(width, height)
      ) : (
        <div className="flex h-full min-h-56 items-center justify-center rounded-lg border border-border bg-muted/30 text-sm text-muted-foreground">
          Loading chart
        </div>
      )}
    </div>
  )
}
