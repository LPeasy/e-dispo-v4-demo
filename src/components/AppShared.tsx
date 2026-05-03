import { useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Field,
  FieldDescription,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { PageHeaderTone, SimulationCount } from "@/appTypes";
import type { BinarySymptom } from "@/model/types";
import { binaryOptions, isBinarySymptom, parseSimulationCount, simulationCounts } from "@/appUtils";
import { valueLabels } from "@/model/worksheet";

function ageDraftFromValue(age: number): string {
  return Number.isFinite(age) ? String(age) : "";
}

function parseAgeDraft(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed.length === 0 || !/^\d+$/.test(trimmed)) {
    return null;
  }

  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function PageHeader({
  icon: Icon,
  title,
  description,
  action,
  tone = "reviewer",
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  tone?: PageHeaderTone;
}) {
  const isCustomer = tone === "customer";

  return (
    <section
      className={
        isCustomer
          ? "flex flex-wrap items-end justify-between gap-6 rounded-lg border border-primary/10 bg-primary/5 p-5 max-[520px]:p-4"
          : "flex flex-wrap items-end justify-between gap-4"
      }
    >
      <div
        className={
          isCustomer
            ? "flex max-w-4xl items-start gap-4"
            : "flex max-w-3xl items-start gap-3"
        }
      >
        <div
          className={
            isCustomer
              ? "flex size-14 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary max-[420px]:size-12"
              : "flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
          }
        >
          <Icon className={isCustomer ? "size-7 max-[420px]:size-6" : "size-5"} />
        </div>
        <div>
          <h1
            className={
              isCustomer
                ? "text-5xl font-semibold leading-tight max-[720px]:text-4xl max-[420px]:text-3xl"
                : "text-3xl font-semibold leading-tight max-[720px]:text-2xl"
            }
          >
            {title}
          </h1>
          <p
            className={
              isCustomer
                ? "mt-3 max-w-3xl text-lg leading-8 text-muted-foreground max-[520px]:text-base max-[520px]:leading-7"
                : "mt-1.5 text-sm leading-6 text-muted-foreground"
            }
          >
            {description}
          </p>
        </div>
      </div>
      {action ? <div className="flex flex-wrap gap-2">{action}</div> : null}
    </section>
  );
}

export function SimulationCountToggle({
  sampleCount,
  setSampleCount,
}: {
  sampleCount: SimulationCount;
  setSampleCount: (value: SimulationCount) => void;
}) {
  return (
    <ToggleGroup
      type="single"
      value={String(sampleCount)}
      onValueChange={(value) => {
        const parsed = parseSimulationCount(value);
        if (parsed !== null) {
          setSampleCount(parsed);
        }
      }}
      className="flex-wrap"
      variant="outline"
    >
      {simulationCounts.map((count) => (
        <ToggleGroupItem key={count} value={String(count)}>
          {count.toLocaleString()}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

export function BinaryField({
  label,
  value,
  onChange,
  description,
}: {
  label: string;
  value: BinarySymptom;
  onChange: (value: BinarySymptom) => void;
  description?: string;
}) {
  return (
    <FieldSet>
      <FieldLegend>{label}</FieldLegend>
      <ToggleGroup
        type="single"
        value={value}
        onValueChange={(nextValue) => {
          if (isBinarySymptom(nextValue)) {
            onChange(nextValue);
          }
        }}
        className="flex-wrap"
        variant="outline"
      >
        {binaryOptions.map((option) => (
          <ToggleGroupItem key={option} value={option}>
            {valueLabels[option]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      {description ? <FieldDescription>{description}</FieldDescription> : null}
    </FieldSet>
  );
}

export function AgeInputField({
  id,
  age,
  setAge,
  description,
  showCenteredAge = false,
}: {
  id: string;
  age: number;
  setAge: (age: number) => void;
  description: string;
  showCenteredAge?: boolean;
}) {
  const [ageDraft, setAgeDraft] = useState(() => ageDraftFromValue(age));
  const parsedAge = parseAgeDraft(ageDraft);
  const hasInvalidText = ageDraft.trim().length > 0 && parsedAge === null;
  const centeredAge = parsedAge === null ? "pending" : String(parsedAge - 42);

  return (
    <Field data-invalid={hasInvalidText || undefined}>
      <FieldLabel htmlFor={id}>Age</FieldLabel>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={ageDraft}
        aria-invalid={hasInvalidText || undefined}
        onChange={(event) => {
          const nextDraft = event.target.value;
          const nextAge = parseAgeDraft(nextDraft);
          setAgeDraft(nextDraft);
          setAge(nextAge ?? Number.NaN);
        }}
        className="h-10 rounded-lg border border-input bg-card px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20"
      />
      <FieldDescription>
        {description}
        {showCenteredAge ? ` Current age_centered: ${centeredAge}.` : null}
      </FieldDescription>
      {hasInvalidText ? (
        <FieldDescription className="font-medium text-destructive">
          Use whole numbers only.
        </FieldDescription>
      ) : null}
    </Field>
  );
}

export function DefinitionRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm leading-6">{value}</dd>
    </div>
  );
}

export function CompactList({ items }: { items: string[] }) {
  return (
    <ul className="grid gap-3 text-sm leading-6 text-muted-foreground">
      {items.map((item) => (
        <li
          key={item}
          className="rounded-lg border border-border bg-background p-3"
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

export function ReadinessRow({
  label,
  ready,
  detail,
}: {
  label: string;
  ready: boolean;
  detail: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background p-3">
      <div>
        <p className="font-medium">{label}</p>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </div>
      <Badge variant={ready ? "default" : "secondary"}>
        {ready ? "Ready" : "Pending"}
      </Badge>
    </div>
  );
}

export function ResultMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-2xl font-semibold">{value}</p>
    </div>
  );
}
