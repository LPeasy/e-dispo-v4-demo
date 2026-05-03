import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Activity, ArrowRight, Info, ShieldCheck, X } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { AgeInputField, BinaryField, PageHeader, ReadinessRow, SimulationCountToggle } from "@/components/AppShared";
import type { ModelRun, ReadinessState, SimulationCount } from "@/appTypes";
import { clampNumber, isPainSeverity, painOptions } from "@/appUtils";
import { formatPercent } from "@/model/logisticModel";
import { tachycardiaBurdenFromHeartRate } from "@/model/pooledEmpiricalPrediction";
import type { BinarySymptom, PainSeverity, SimulationResult } from "@/model/types";
import type { SimulationWorkerState } from "@/model/useSimulationWorker";
import { valueLabels } from "@/model/worksheet";

type ProbabilityInterval = [number, number];
type HistogramAxis = {
  min: number;
  max: number;
  binWidth: number;
  sliderStep: number;
};
type DynamicHistogramBin = {
  range: string;
  lower: number;
  upper: number;
  midpoint: number;
  count: number;
};
type CustomerStep = "start" | "inputs" | "review" | "results";
type CustomerUncertaintyViewMode = "overview" | "zoomed";

const FULL_PROBABILITY_AXIS: HistogramAxis = {
  min: 0,
  max: 1,
  binWidth: 1 / 40,
  sliderStep: 0.01,
};
const FULL_RANGE_BIN_COUNT = 40;

export function CustomerPreviewPage({
  age,
  setAge,
  heartRateText,
  setHeartRateText,
  heartRateBpm,
  painSeverity,
  setPainSeverity,
  fever,
  setFever,
  vomiting,
  setVomiting,
  sampleCount,
  setSampleCount,
  readinessState,
  customerRunError,
  customerScopeAccepted,
  setCustomerScopeAccepted,
  customerDisclaimerAccepted,
  setCustomerDisclaimerAccepted,
  runCustomerModel,
  run,
  simulationState,
}: {
  age: number;
  setAge: (age: number) => void;
  heartRateText: string;
  setHeartRateText: (value: string) => void;
  heartRateBpm: number | null;
  painSeverity: PainSeverity;
  setPainSeverity: (value: PainSeverity) => void;
  fever: BinarySymptom;
  setFever: (value: BinarySymptom) => void;
  vomiting: BinarySymptom;
  setVomiting: (value: BinarySymptom) => void;
  sampleCount: SimulationCount;
  setSampleCount: (value: SimulationCount) => void;
  readinessState: ReadinessState;
  customerRunError: string | null;
  customerScopeAccepted: boolean;
  setCustomerScopeAccepted: (value: boolean) => void;
  customerDisclaimerAccepted: boolean;
  setCustomerDisclaimerAccepted: (value: boolean) => void;
  runCustomerModel: () => void;
  run: ModelRun | null;
  simulationState: SimulationWorkerState;
}) {
  const burden =
    heartRateBpm === null ? null : tachycardiaBurdenFromHeartRate(heartRateBpm);
  const canUseCustomerFlow =
    customerScopeAccepted && customerDisclaimerAccepted;
  const canRunCustomerEstimate =
    readinessState.canRun &&
    customerScopeAccepted &&
    customerDisclaimerAccepted;
  const [step, setStep] = useState<CustomerStep>("start");

  const runAndShowResults = () => {
    runCustomerModel();
    if (canRunCustomerEstimate) {
      setStep("results");
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        icon={ShieldCheck}
        title="Customer Preview"
        description="Answer a few required questions. Then see the model estimate and its range. This prototype is for education and review only."
        tone="customer"
      />
      <CustomerStepTracker currentStep={step} />

      {step === "start" ? (
        <section className="grid grid-cols-[minmax(0,1fr)_minmax(320px,0.78fr)] gap-5 max-[520px]:pb-20 max-[940px]:grid-cols-1">
          <Card
            className="rounded-lg border-primary/20 bg-primary/5 max-[520px]:gap-3 max-[520px]:py-3"
            size="sm"
          >
            <CardHeader className="max-[520px]:gap-0.5">
              <CardTitle>First, check the limits</CardTitle>
              <CardDescription className="max-[520px]:text-xs max-[520px]:leading-5">
                The preview opens after you check the scope and safety notice.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup className="max-[520px]:gap-3">
                <CustomerCheckboxField
                  checked={customerScopeAccepted}
                  onCheckedChange={setCustomerScopeAccepted}
                  label="This example fits the prototype scope."
                  description="Adult male, age 18-64, with non-traumatic stomach or abdominal pain."
                />
                <CustomerLegalDisclaimer
                  checked={customerDisclaimerAccepted}
                  onCheckedChange={setCustomerDisclaimerAccepted}
                />
                {customerRunError ? (
                  <Alert>
                    <Info />
                    <AlertTitle>Estimate not shown</AlertTitle>
                    <AlertDescription>{customerRunError}</AlertDescription>
                  </Alert>
                ) : null}
                <Button
                  type="button"
                  disabled={!canUseCustomerFlow}
                  onClick={() => setStep("inputs")}
                  className="w-fit max-[520px]:hidden"
                >
                  Continue to questions
                  <ArrowRight data-icon="inline-end" />
                </Button>
              </FieldGroup>
            </CardContent>
          </Card>
          <CustomerPlainLanguagePanel />
          <div className="fixed inset-x-0 bottom-0 z-40 hidden border-t border-border bg-background/95 p-3 shadow-[0_-8px_24px_rgba(23,33,43,0.08)] backdrop-blur max-[520px]:block">
            <Button
              type="button"
              disabled={!canUseCustomerFlow}
              onClick={() => setStep("inputs")}
              className="w-full"
            >
              Continue to questions
              <ArrowRight data-icon="inline-end" />
            </Button>
          </div>
        </section>
      ) : null}

      {step === "inputs" ? (
        <section className="grid grid-cols-[minmax(0,1fr)_minmax(300px,0.72fr)] gap-5 max-[940px]:grid-cols-1">
          <Card className="rounded-lg">
            <CardHeader>
              <CardTitle className="text-2xl leading-8 max-[520px]:text-xl">
                Answer the required questions
              </CardTitle>
              <CardDescription>
                These answers are the only inputs used here.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <AgeInputField
                  id="customer-age-input"
                  age={age}
                  setAge={setAge}
                  description="This prototype is limited to ages 18 through 64."
                />
                <FieldSet>
                  <FieldLegend>Pain right now</FieldLegend>
                  <ToggleGroup
                    type="single"
                    value={painSeverity}
                    onValueChange={(value) => {
                      if (isPainSeverity(value)) {
                        setPainSeverity(value);
                      }
                    }}
                    className="flex-wrap"
                    variant="outline"
                  >
                    {painOptions.map((option) => (
                      <ToggleGroupItem key={option} value={option}>
                        {valueLabels[option]}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                  <FieldDescription>
                    Mild and moderate are the non-severe comparison point.
                  </FieldDescription>
                </FieldSet>
                <div className="grid grid-cols-2 gap-5 max-[720px]:grid-cols-1">
                  <BinaryField
                    label="Fever"
                    value={fever}
                    onChange={setFever}
                    description="Select Yes when the measured temperature is 100.4°F or higher."
                  />
                  <BinaryField
                    label="Vomiting"
                    value={vomiting}
                    onChange={setVomiting}
                    description="Required yes/no input."
                  />
                </div>
                <Field>
                  <FieldLabel htmlFor="customer-hr-input">
                    Observed heart rate
                  </FieldLabel>
                  <div className="flex gap-2">
                    <input
                      id="customer-hr-input"
                      type="number"
                      min={1}
                      value={heartRateText}
                      onChange={(event) => setHeartRateText(event.target.value)}
                      className="h-10 min-w-0 flex-1 rounded-lg border border-input bg-card px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setHeartRateText("")}
                    >
                      Clear
                    </Button>
                  </div>
                  <FieldDescription>
                    Heart rate above 100 changes the model. HR 110 equals one
                    burden unit, meaning 10 bpm above 100. Current burden:{" "}
                    {burden === null ? "pending" : burden.toFixed(2)}.
                  </FieldDescription>
                  {heartRateBpm === null ? (
                    <FieldDescription className="font-medium text-destructive">
                      Observed heart rate is required before an estimate can be
                      shown.
                    </FieldDescription>
                  ) : null}
                </Field>
                <FieldSet>
                  <FieldLegend>Simulation runs</FieldLegend>
                  <SimulationCountToggle
                    sampleCount={sampleCount}
                    setSampleCount={setSampleCount}
                  />
                  <FieldDescription>
                    More runs make the range chart smoother. They do not change
                    the model.
                  </FieldDescription>
                </FieldSet>
                {readinessState.error ? (
                  <Alert>
                    <Info />
                    <AlertTitle>Question still needed</AlertTitle>
                    <AlertDescription>{readinessState.error}</AlertDescription>
                  </Alert>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setStep("start")}
                  >
                    Back
                  </Button>
                  <Button
                    type="button"
                    disabled={!readinessState.canRun}
                    onClick={() => setStep("review")}
                  >
                    Review inputs
                    <ArrowRight data-icon="inline-end" />
                  </Button>
                </div>
              </FieldGroup>
            </CardContent>
          </Card>
          <CustomerEstimateStatus
            readinessState={readinessState}
            scopeAccepted={customerScopeAccepted}
            disclaimerAccepted={customerDisclaimerAccepted}
          />
        </section>
      ) : null}

      {step === "review" ? (
        <section className="grid grid-cols-[minmax(0,1fr)_minmax(300px,0.72fr)] gap-5 max-[940px]:grid-cols-1">
          <Card className="rounded-lg">
            <CardHeader>
              <CardTitle>Review, then run</CardTitle>
              <CardDescription>
                Nothing is calculated until you choose Run model.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              <CustomerInputPreview
                age={age}
                painSeverity={painSeverity}
                fever={fever}
                vomiting={vomiting}
                heartRateBpm={heartRateBpm}
                sampleCount={sampleCount}
              />
              {customerRunError ? (
                <Alert>
                  <Info />
                  <AlertTitle>Estimate not shown</AlertTitle>
                  <AlertDescription>{customerRunError}</AlertDescription>
                </Alert>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setStep("inputs")}
                >
                  Edit answers
                </Button>
                <Button
                  type="button"
                  disabled={!canRunCustomerEstimate}
                  onClick={runAndShowResults}
                >
                  Run model
                  <ArrowRight data-icon="inline-end" />
                </Button>
              </div>
            </CardContent>
          </Card>
          <CustomerEstimateStatus
            readinessState={readinessState}
            scopeAccepted={customerScopeAccepted}
            disclaimerAccepted={customerDisclaimerAccepted}
          />
        </section>
      ) : null}

      {step === "results" ? (
        <section className="flex flex-col gap-5">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep("inputs")}
            >
              Edit answers
            </Button>
            <Button
              type="button"
              disabled={!canRunCustomerEstimate}
              onClick={runAndShowResults}
            >
              Run again
            </Button>
          </div>
          <CustomerResultsPanel run={run} simulationState={simulationState} />
        </section>
      ) : null}
    </div>
  );
}

function CustomerStepTracker({
  currentStep,
}: {
  currentStep: CustomerStep;
}) {
  const steps: Array<{ id: CustomerStep; label: string; description: string }> =
    [
      { id: "start", label: "Start", description: "Scope and safety notice" },
      { id: "inputs", label: "Questions", description: "Required answers" },
      { id: "review", label: "Review", description: "Confirm before running" },
      { id: "results", label: "Results", description: "Range first" },
    ];
  const currentIndex = steps.findIndex((step) => step.id === currentStep);

  return (
    <nav
      aria-label="Customer preview steps"
      className="grid grid-cols-4 gap-2 rounded-lg border border-primary/20 bg-primary/5 p-2.5 max-[760px]:grid-cols-2 max-[420px]:p-2"
    >
      {steps.map((step, index) => {
        const active = step.id === currentStep;
        const complete = index < currentIndex;

        return (
          <div
            key={step.id}
            className={
              active
                ? "rounded-lg bg-primary px-4 py-3 text-primary-foreground shadow-sm max-[420px]:px-3"
                : complete
                  ? "rounded-lg bg-card px-4 py-3 text-foreground max-[420px]:px-3"
                  : "rounded-lg bg-background/70 px-4 py-3 text-muted-foreground max-[420px]:px-3"
            }
          >
            <p className="text-base font-semibold leading-6 max-[520px]:text-sm">
              {step.label}
            </p>
            <p className="mt-1 text-xs leading-5 opacity-85">
              {step.description}
            </p>
          </div>
        );
      })}
    </nav>
  );
}

function CustomerPlainLanguagePanel() {
  const points = [
    {
      label: "You will see a range",
      text: "The preview shows the model estimate and the range around it for this limited prototype profile.",
    },
    {
      label: "The range can move",
      text: "A simulation means many repeated model runs. Those runs do not all land in the same place.",
    },
    {
      label: "It does not guide care",
      text: "It does not give medical advice or tell anyone what to do.",
    },
  ];

  return (
    <Card className="rounded-lg border-primary/10 bg-card/95">
      <CardHeader>
        <CardTitle className="text-2xl leading-8 max-[520px]:text-xl">
          Quick guide
        </CardTitle>
        <CardDescription>
          Read the result as a range, not as a personal instruction.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {points.map((point) => (
          <div
            key={point.label}
            className="rounded-lg border border-border bg-background p-4"
          >
            <p className="text-base font-semibold leading-6">{point.label}</p>
            <p className="mt-2 text-base leading-7 text-muted-foreground max-[520px]:text-sm max-[520px]:leading-6">
              {point.text}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CustomerInputPreview({
  age,
  painSeverity,
  fever,
  vomiting,
  heartRateBpm,
  sampleCount,
}: {
  age: number;
  painSeverity: PainSeverity;
  fever: BinarySymptom;
  vomiting: BinarySymptom;
  heartRateBpm: number | null;
  sampleCount: SimulationCount;
}) {
  const items = [
    ["Age", String(age)],
    ["Pain", valueLabels[painSeverity]],
    ["Fever", `${valueLabels[fever]} (100.4°F or higher)`],
    ["Vomiting", valueLabels[vomiting]],
    ["Observed HR", heartRateBpm === null ? "Required" : `${heartRateBpm} bpm`],
    ["Simulation runs", sampleCount.toLocaleString()],
  ];

  return (
    <div className="rounded-lg border border-border bg-background p-4">
      <p className="font-medium">Inputs ready to run</p>
      <div className="mt-4 grid grid-cols-3 gap-2 max-[760px]:grid-cols-2 max-[460px]:grid-cols-1">
        {items.map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-border bg-card p-3"
          >
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              {label}
            </p>
            <p className="mt-1 text-sm font-semibold">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CustomerCheckboxField({
  checked,
  onCheckedChange,
  label,
  description,
}: {
  checked: boolean;
  onCheckedChange: (value: boolean) => void;
  label: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-background p-4 max-[520px]:p-3">
      <div className="flex items-start gap-3">
        <Checkbox
          checked={checked}
          onCheckedChange={(value) => onCheckedChange(value === true)}
          aria-label={label}
          className="mt-1"
        />
        <div>
          <p className="font-medium">{label}</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground max-[520px]:text-xs max-[520px]:leading-5">
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}

function CustomerLegalDisclaimer({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (value: boolean) => void;
}) {
  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 max-[520px]:p-3">
      <div className="flex items-start gap-3">
        <Checkbox
          checked={checked}
          onCheckedChange={(value) => onCheckedChange(value === true)}
          aria-label="Safety notice acknowledgement"
          className="mt-1"
        />
        <div>
          <p className="font-medium text-foreground">
            Safety notice
          </p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground max-[520px]:text-xs max-[520px]:leading-5">
            I understand this prototype is not medical advice, does not replace
            professional care, and does not tell me what health decision to
            make.
          </p>
          <details className="mt-2 text-sm text-muted-foreground max-[520px]:text-xs">
            <summary className="cursor-pointer font-medium text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
              Full safety text
            </summary>
            <p className="mt-2 leading-6 max-[520px]:leading-5">
              I understand and agree that this internal prototype is not medical
              advice and does not replace professional care. I am solely
              responsible for any personal health decision made after viewing
              it. The model development team is not responsible under any
              condition for any decision, action, delay, outcome, injury, cost,
              loss, or consequence connected to use of this prototype,
              regardless of intent, interpretation, or result.
            </p>
          </details>
          <p className="sr-only">
            I understand and agree that this internal prototype is not medical
            advice and does not replace professional care. I am solely
            responsible for any personal health decision made after viewing it.
            The model development team is not responsible under any condition
            for any decision, action, delay, outcome, injury, cost, loss, or
            consequence connected to use of this prototype, regardless of
            intent, interpretation, or result.
          </p>
        </div>
      </div>
    </div>
  );
}

function CustomerEstimateStatus({
  readinessState,
  scopeAccepted,
  disclaimerAccepted,
}: {
  readinessState: ReadinessState;
  scopeAccepted: boolean;
  disclaimerAccepted: boolean;
}) {
  const rows = [
    {
      label: "Prototype scope",
      ready: scopeAccepted,
      detail: scopeAccepted ? "Confirmed" : "Required before estimate",
    },
    {
      label: "Required model fields",
      ready: readinessState.canRun,
      detail: readinessState.canRun
        ? "Age, yes/no symptom choices, and observed heart rate ready"
        : (readinessState.error ?? "Required fields pending"),
    },
    {
      label: "Safety notice",
      ready: disclaimerAccepted,
      detail: disclaimerAccepted ? "Accepted" : "Required before estimate",
    },
  ];

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>Before results appear</CardTitle>
        <CardDescription>
          The preview waits for all required checks.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {rows.map((row) => (
          <ReadinessRow
            key={row.label}
            label={row.label}
            ready={row.ready}
            detail={row.detail}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function CustomerResultsPanel({
  run,
  simulationState,
}: {
  run: ModelRun | null;
  simulationState: SimulationWorkerState;
}) {
  const simulation = simulationState.result;

  if (run === null) {
    return (
      <Card className="rounded-lg border-dashed">
        <CardHeader>
          <CardTitle>Results wait for Run model</CardTitle>
          <CardDescription>
            The customer view does not calculate while inputs are being edited.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm leading-6 text-muted-foreground">
          Complete the required fields and checks. Then run the model to build
          the estimate range.
        </CardContent>
      </Card>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-card p-6 shadow-sm max-[520px]:p-4">
      <div className="flex flex-col gap-3">
        <h2 className="text-3xl font-semibold leading-tight max-[520px]:text-2xl">
          A range, not one exact answer
        </h2>
        <p className="max-w-3xl text-base leading-7 text-muted-foreground">
          Start with the spread of model results. The result is not one exact
          answer.
        </p>
      </div>
      <div className="mt-6 flex flex-col gap-6 max-[520px]:mt-5 max-[520px]:gap-5">
        {simulationState.status === "error" ? (
          <Alert>
            <Info />
            <AlertTitle>Range view unavailable</AlertTitle>
            <AlertDescription>
              {simulationState.error ?? "Simulation failed."}
            </AlertDescription>
          </Alert>
        ) : null}
        {simulationState.status !== "complete" &&
        simulationState.status !== "error" ? (
          <div className="flex min-h-[280px] items-center justify-center rounded-lg border border-border bg-muted/30">
            <div className="flex flex-col items-center gap-3 text-center">
              <Activity className="size-8 animate-pulse text-primary" />
              <p className="text-sm text-muted-foreground">
                Building the range from {run.sampleCount.toLocaleString()}{" "}
                simulation runs
              </p>
            </div>
          </div>
        ) : null}
        {simulationState.status === "complete" && simulation ? (
          <>
            <CustomerUncertaintyExplorer
              key={`${simulation.seed}-${simulation.sampleCount}-${simulation.p10}-${simulation.p90}`}
              simulation={simulation}
            />
            <CustomerRangeSummary simulation={simulation} />
            <CustomerMedicalAdviceNotice />
            <CustomerInputReceipt run={run} />
          </>
        ) : null}
      </div>
    </section>
  );
}

function CustomerRangeSummary({
  simulation,
}: {
  simulation: SimulationResult;
}) {
  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 p-5 max-[520px]:p-4">
      <p className="text-2xl font-semibold leading-8 text-foreground max-[520px]:text-xl">
        What this range is saying
      </p>
      <p className="mt-3 text-base leading-7 text-muted-foreground">
        Across {simulation.sampleCount.toLocaleString()} simulation runs, most
        runs landed between{" "}
        <strong>{formatPercent(simulation.p10)}</strong> and{" "}
        <strong>{formatPercent(simulation.p90)}</strong>. A wider look at the
        model spread ran from <strong>{formatPercent(simulation.p025)}</strong>{" "}
        to <strong>{formatPercent(simulation.p975)}</strong>.
      </p>
    </div>
  );
}

function CustomerMedicalAdviceNotice() {
  return (
    <div className="rounded-lg border border-border bg-background p-4">
      <div className="flex items-start gap-3">
        <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div>
          <p className="text-base font-medium text-foreground">
            This is not medical advice.
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            This internal prototype does not diagnose you, choose a care
            setting, tell you what to do, or tell you whether stomach pain is
            harmless. Do not use it as medical advice or as the basis for
            personal health decisions.
          </p>
        </div>
      </div>
    </div>
  );
}

export function CustomerUncertaintyExplorer({
  simulation,
}: {
  simulation: SimulationResult;
}) {
  const focusedAxis = useMemo(
    () => buildFocusedHistogramAxis(simulation),
    [simulation],
  );
  const overviewBins = useMemo(
    () =>
      buildHistogramBins(simulation.samples, FULL_PROBABILITY_AXIS, {
        minBins: FULL_RANGE_BIN_COUNT,
        maxBins: FULL_RANGE_BIN_COUNT,
      }),
    [simulation.samples],
  );
  const focusedBins = useMemo(
    () => buildHistogramBins(simulation.samples, focusedAxis),
    [focusedAxis, simulation.samples],
  );
  const [viewMode, setViewMode] =
    useState<CustomerUncertaintyViewMode>("overview");
  const [interval, setInterval] = useState<ProbabilityInterval>([
    simulation.p10,
    simulation.p90,
  ]);
  const [activeBin, setActiveBin] = useState<DynamicHistogramBin | null>(null);
  const explorerRef = useRef<HTMLDivElement | null>(null);

  const highlightedBin =
    activeBin ??
    focusedBins.find((bin) => bin.count > 0) ??
    overviewBins.find((bin) => bin.count > 0) ??
    overviewBins[0];
  const selectedCoverage = estimateIntervalCoverage(
    simulation.samples,
    interval[0],
    interval[1],
  );
  const showZoomedView = viewMode === "zoomed";

  useEffect(() => {
    if (activeBin === null) {
      return;
    }

    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setActiveBin(null);
      }
    };
    const dismissOnOutsidePointer = (event: PointerEvent) => {
      if (
        explorerRef.current &&
        !explorerRef.current.contains(event.target as Node)
      ) {
        setActiveBin(null);
      }
    };

    window.addEventListener("keydown", dismissOnEscape);
    window.addEventListener("pointerdown", dismissOnOutsidePointer, {
      capture: true,
    });

    return () => {
      window.removeEventListener("keydown", dismissOnEscape);
      window.removeEventListener("pointerdown", dismissOnOutsidePointer, {
        capture: true,
      });
    };
  }, [activeBin]);

  const activateBin = (bin: DynamicHistogramBin) => {
    setActiveBin((current) => (binsMatch(current ?? undefined, bin) ? null : bin));
  };
  const changeViewMode = (nextViewMode: CustomerUncertaintyViewMode) => {
    setActiveBin(null);
    setViewMode(nextViewMode);
  };

  return (
    <div
      ref={explorerRef}
      onPointerDownCapture={(event) => {
        if (
          !(event.target instanceof Element) ||
          !event.target.closest("[data-histogram-bar='true']")
        ) {
          setActiveBin(null);
        }
      }}
      className="rounded-lg border border-border bg-background p-6 max-[520px]:p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold leading-8 max-[520px]:text-xl">
            Explore the full range, then zoom in
          </h2>
          <p className="mt-2 max-w-3xl text-base leading-7 text-muted-foreground max-[520px]:text-sm max-[520px]:leading-6">
            Switch between the full 0% to 100% view and a closer view with
            adjustable range handles.
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2 max-[640px]:items-start">
          <Badge variant="outline">
            {simulation.sampleCount.toLocaleString()} runs
          </Badge>
          <GraphEducationToggle />
        </div>
      </div>
      <DistributionViewToggle
        viewMode={viewMode}
        setViewMode={changeViewMode}
      />
      <div className="mt-5 flex flex-wrap gap-2">
        <IntervalPresetButton
          label="Common range (80%)"
          active={intervalMatches(interval, simulation.p10, simulation.p90)}
          onClick={() => {
            setInterval([simulation.p10, simulation.p90]);
            changeViewMode("zoomed");
          }}
        />
        <IntervalPresetButton
          label="Wider range (95%)"
          active={intervalMatches(interval, simulation.p025, simulation.p975)}
          onClick={() => {
            setInterval([simulation.p025, simulation.p975]);
            changeViewMode("zoomed");
          }}
        />
        <IntervalPresetButton
          label="Full zoom window"
          active={intervalMatches(interval, focusedAxis.min, focusedAxis.max)}
          onClick={() => {
            setInterval([focusedAxis.min, focusedAxis.max]);
            changeViewMode("zoomed");
          }}
        />
      </div>
      {!showZoomedView ? (
      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-base font-semibold">Full range view</p>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
              This shows where the simulation runs sit between 0% and 100%.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="default"
            onClick={() => changeViewMode("zoomed")}
          >
            Zoom in
          </Button>
        </div>
        <div
          className="mt-4 rounded-lg border border-border/70 bg-background p-3"
          onClick={() => changeViewMode("zoomed")}
        >
          <CustomerIntervalBoxPlot
            axis={FULL_PROBABILITY_AXIS}
            simulation={simulation}
            interval={interval}
            onActivate={() => setViewMode("zoomed")}
          />
          <div className="relative mt-5 h-52">
            <CustomerOverviewClusterCallout
              axis={FULL_PROBABILITY_AXIS}
              low={simulation.p10}
              high={simulation.p90}
            />
            <div className="absolute inset-x-0 bottom-0 top-12">
              <CustomerHistogramBars
                axis={FULL_PROBABILITY_AXIS}
                bins={overviewBins}
                density="dense"
                interval={interval}
                selectedBin={highlightedBin}
                activeBin={activeBin ?? undefined}
                onHoverBin={setActiveBin}
                onSelectBin={activateBin}
                onDismissBin={() => setActiveBin(null)}
              />
            </div>
          </div>
          <div className="mt-3 flex justify-between text-xs text-muted-foreground">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>
      </div>
      ) : null}
      {showZoomedView ? (
        <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-base font-semibold">Zoomed view</p>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                This makes the tight group of simulation runs easier to inspect
                and adjust.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
            variant="outline"
            onClick={() => changeViewMode("overview")}
          >
              Zoom out
            </Button>
          </div>
          <div className="mt-4 rounded-lg border border-border bg-card p-4">
            <div className="relative h-80">
              <div className="absolute inset-x-0 bottom-20 top-0">
                <CustomerHistogramBars
                  axis={focusedAxis}
                  bins={focusedBins}
                  density="comfortable"
                  interval={interval}
                  selectedBin={highlightedBin}
                  activeBin={activeBin ?? undefined}
                  onHoverBin={setActiveBin}
                  onSelectBin={activateBin}
                  onDismissBin={() => setActiveBin(null)}
                />
              </div>
              <div className="absolute inset-x-0 bottom-0">
                <CustomerSliderEndpointLabels
                  interval={interval}
                />
                <Slider
                  value={[interval[0] * 100, interval[1] * 100]}
                  min={focusedAxis.min * 100}
                  max={focusedAxis.max * 100}
                  step={focusedAxis.sliderStep * 100}
                  onFocus={() => changeViewMode("zoomed")}
                  onValueChange={(value) => {
                    if (value.length === 2) {
                      setInterval([
                        Math.min(value[0], value[1]) / 100,
                        Math.max(value[0], value[1]) / 100,
                      ]);
                    }
                  }}
                  aria-label="Selected range interval"
                />
                <div className="mt-3 flex justify-between text-xs text-muted-foreground">
                  <span>{formatPercent(focusedAxis.min)}</span>
                  <span>{formatPercent(focusedAxis.max)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
      <div className="mt-4 grid grid-cols-[minmax(0,1fr)_minmax(280px,0.72fr)] gap-3 max-[820px]:grid-cols-1">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-base font-semibold">Range you’re highlighting</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            You are highlighting{" "}
            <strong>
              {formatPercent(interval[0])} to {formatPercent(interval[1])}
            </strong>
            . About <strong>{formatPercent(selectedCoverage)}</strong> of
            simulation runs fall inside that range.
          </p>
        </div>
      </div>
    </div>
  );
}

function GraphEducationToggle() {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  useEffect(() => {
    if (!open) {
      return;
    }

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", closeOnEscape);

    return () => {
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="flex w-full flex-col items-end gap-2 max-[640px]:items-start">
      <Button
        type="button"
        variant="outline"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
        className="h-auto rounded-full border-primary/30 bg-card py-2 pl-2 pr-3 shadow-lg"
      >
        <RetroGraphHelperAvatar />
        <span className="text-sm font-medium">Need graph help?</span>
      </Button>
      {open ? (
        <div
          id={panelId}
          role="dialog"
          aria-label="Graph help"
          className="w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-border bg-card p-4 text-sm shadow-lg"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-foreground">
                Plain-English graph help
              </p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Box plots can use different rules, so labels matter.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setOpen(false)}
            >
              <X data-icon="inline-start" />
              Close
            </Button>
          </div>
          <dl className="mt-3 grid gap-2">
            <GraphHelpItem
              label="Median"
              text="The middle value. Half the runs are lower, and half are higher."
            />
            <GraphHelpItem
              label="Middle 50%"
              text="In a standard box plot, the box holds the middle half of the data."
            />
            <GraphHelpItem
              label="Whiskers"
              text="The thin lines show the outer range used by that chart. Some charts use min and max. Others use an IQR rule."
            />
            <GraphHelpItem
              label="Outliers"
              text="Dots beyond the whiskers, when shown. They are values far from the main group."
            />
          </dl>
          <p className="mt-3 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs leading-5 text-muted-foreground">
            This app uses an uncertainty range guide, not a full standard box
            plot. The thick band is the 80% simulation range. The thin band is
            the 95% simulation range.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function RetroGraphHelperAvatar() {
  return (
    <span
      aria-hidden="true"
      className="relative flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-full border border-primary/30 bg-primary/10"
    >
      <span className="absolute left-3 top-3 size-2 rounded-full bg-foreground/80" />
      <span className="absolute right-3 top-3 size-2 rounded-full bg-foreground/80" />
      <span className="absolute bottom-3 h-2 w-6 rounded-b-full border-b-2 border-primary" />
      <span className="absolute left-2 top-1 h-3 w-8 rounded-t-full border border-primary/30 bg-primary/20" />
      <span className="absolute bottom-0 left-2 right-2 h-2 rounded-t-lg bg-primary/20" />
    </span>
  );
}

function GraphHelpItem({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <dt className="font-medium text-foreground">{label}</dt>
      <dd className="mt-1 leading-5 text-muted-foreground">{text}</dd>
    </div>
  );
}

function CustomerOverviewClusterCallout({
  axis,
  low,
  high,
}: {
  axis: HistogramAxis;
  low: number;
  high: number;
}) {
  const left = axisPosition(low, axis.min, axis.max);
  const right = axisPosition(high, axis.min, axis.max);
  const width = Math.max(2, right - left);
  const labelPosition = clusterCalloutLabelPosition(left, right);

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 h-11 text-xs">
      <div
        className="absolute top-0 whitespace-nowrap rounded-md border border-primary/30 bg-primary/10 px-2 py-1 font-medium text-primary"
        style={{
          left: `${labelPosition.left}%`,
          transform: labelPosition.transform,
        }}
      >
        Most runs cluster here
      </div>
      <div
        className="absolute top-8 h-3 rounded-t-sm border-x-2 border-t-2 border-primary/70"
        style={{ left: `${left}%`, width: `${width}%` }}
      />
      <span className="sr-only">
        Most model runs are between {formatPercent(low)} and{" "}
        {formatPercent(high)} on the full zero to one hundred percent chart.
      </span>
    </div>
  );
}

function CustomerSliderEndpointLabels({
  interval,
}: {
  interval: ProbabilityInterval;
}) {
  return (
    <div className="mb-2 grid grid-cols-2 gap-2 text-xs font-medium">
      <span className="rounded-md border border-border bg-background px-2 py-1 text-foreground shadow-sm">
        Low endpoint: {formatPercent(interval[0])}
      </span>
      <span className="rounded-md border border-border bg-background px-2 py-1 text-right text-foreground shadow-sm">
        High endpoint: {formatPercent(interval[1])}
      </span>
    </div>
  );
}

function CustomerIntervalBoxPlot({
  axis,
  simulation,
  interval,
  onActivate,
}: {
  axis: HistogramAxis;
  simulation: SimulationResult;
  interval: ProbabilityInterval;
  onActivate: () => void;
}) {
  const whiskerLow = axisPosition(simulation.p025, axis.min, axis.max);
  const whiskerHigh = axisPosition(simulation.p975, axis.min, axis.max);
  const boxLow = axisPosition(simulation.p10, axis.min, axis.max);
  const boxHigh = axisPosition(simulation.p90, axis.min, axis.max);
  const selectedLow = axisPosition(interval[0], axis.min, axis.max);
  const selectedHigh = axisPosition(interval[1], axis.min, axis.max);
  const median = axisPosition(simulation.median, axis.min, axis.max);

  return (
    <button
      type="button"
      onClick={onActivate}
      className="w-full rounded-lg border border-border bg-card p-4 text-left outline-none transition hover:border-primary/40 focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-base font-semibold">Quick range guide</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            The thicker box shows where most simulation runs landed. The thin
            line shows the wider spread.
          </p>
        </div>
        <Badge variant="secondary">tap to zoom</Badge>
      </div>
      <div className="relative mt-5 h-16">
        <div className="absolute inset-x-0 top-7 h-px bg-border" />
        <div
          className="absolute top-5 h-5 rounded-full border border-border bg-muted"
          style={{
            left: `${whiskerLow}%`,
            width: `${Math.max(1, whiskerHigh - whiskerLow)}%`,
          }}
        />
        <div
          className="absolute top-3 h-9 rounded-lg border border-teal-500/60 bg-teal-500/20"
          style={{
            left: `${boxLow}%`,
            width: `${Math.max(1, boxHigh - boxLow)}%`,
          }}
        />
        <div
          className="absolute top-0 h-14 rounded-lg border border-primary/50 bg-primary/10"
          style={{
            left: `${selectedLow}%`,
            width: `${Math.max(1, selectedHigh - selectedLow)}%`,
          }}
        />
        <div
          className="absolute top-1 h-12 w-px bg-primary"
          style={{ left: `${median}%` }}
        />
      </div>
      <div
        className="mt-2 grid grid-cols-3 gap-2 text-xs text-muted-foreground"
        aria-hidden="true"
      >
        <span>lower runs</span>
        <span className="text-center">middle of runs</span>
        <span className="text-right">higher runs</span>
      </div>
      <span className="sr-only">
        Most simulation runs sit from {formatPercent(simulation.p025)} to{" "}
        {formatPercent(simulation.p975)}, with the middle simulation estimate at{" "}
        {formatPercent(simulation.median)}.
      </span>
    </button>
  );
}

function CustomerHistogramBars({
  axis,
  bins,
  density,
  interval,
  selectedBin,
  activeBin,
  onHoverBin,
  onSelectBin,
  onDismissBin,
}: {
  axis: HistogramAxis;
  bins: DynamicHistogramBin[];
  density: "comfortable" | "dense";
  interval: ProbabilityInterval;
  selectedBin: DynamicHistogramBin | undefined;
  activeBin: DynamicHistogramBin | undefined;
  onHoverBin: (bin: DynamicHistogramBin) => void;
  onSelectBin: (bin: DynamicHistogramBin) => void;
  onDismissBin: () => void;
}) {
  const maxCount = Math.max(...bins.map((bin) => bin.count), 1);
  const intervalLeft = axisPosition(interval[0], axis.min, axis.max);
  const intervalRight = axisPosition(interval[1], axis.min, axis.max);
  const intervalWidth = Math.max(1, intervalRight - intervalLeft);
  const gapClass = density === "dense" ? "gap-[2px]" : "gap-1.5";
  const minWidthClass = density === "dense" ? "min-w-0" : "min-w-3";
  const emptyHeight = density === "dense" ? 1.5 : 3;
  const filledMinimumHeight = density === "dense" ? 8 : 10;
  const activeChartBin = activeBin
    ? bins.find((bin) => binsMatch(activeBin, bin))
    : undefined;

  return (
    <div className="relative h-full" onMouseLeave={onDismissBin}>
      <div
        className="pointer-events-none absolute inset-y-0 rounded-lg border border-primary/40 bg-primary/10"
        style={{ left: `${intervalLeft}%`, width: `${intervalWidth}%` }}
      />
      <div className={`absolute inset-0 flex items-end ${gapClass}`}>
        {bins.map((bin) => {
          const isSelected = binsMatch(selectedBin, bin);
          const insideInterval =
            bin.upper >= interval[0] && bin.lower <= interval[1];
          const hasRuns = bin.count > 0;
          const height = Math.max(
            hasRuns ? filledMinimumHeight : emptyHeight,
            Math.sqrt(bin.count / maxCount) * 100,
          );
          const barClass = hasRuns
            ? isSelected
              ? "w-full rounded-t-md bg-primary shadow-sm transition-all"
              : insideInterval
                ? "w-full rounded-t-md bg-primary/70 transition-all group-hover:bg-primary"
                : "w-full rounded-t-md bg-primary/40 transition-all group-hover:bg-primary/60"
            : insideInterval
              ? "w-full rounded-t-sm bg-primary/20"
              : "w-full rounded-t-sm bg-border/70";

          if (!hasRuns) {
            return (
              <span
                key={bin.range}
                className={`flex h-full flex-1 ${minWidthClass} items-end`}
                aria-hidden="true"
              >
                <span className={barClass} style={{ height: `${height}%` }} />
              </span>
            );
          }

          return (
            <button
              key={bin.range}
              type="button"
              data-histogram-bar="true"
              className={`group flex h-full flex-1 ${minWidthClass} items-end outline-none`}
              onClick={(event) => {
                event.stopPropagation();
                onSelectBin(bin);
              }}
              onFocus={() => onHoverBin(bin)}
              onMouseEnter={() => onHoverBin(bin)}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  event.stopPropagation();
                  onDismissBin();
                }
              }}
              aria-label={`${bin.range}, ${bin.count.toLocaleString()} simulation runs`}
            >
              <span className={barClass} style={{ height: `${height}%` }} />
            </button>
          );
        })}
      </div>
      {activeChartBin ? (
        <SelectedBarFloatingTab
          bin={activeChartBin}
          axis={axis}
          maxCount={maxCount}
          filledMinimumHeight={filledMinimumHeight}
        />
      ) : null}
    </div>
  );
}

function SelectedBarFloatingTab({
  bin,
  axis,
  maxCount,
  filledMinimumHeight,
}: {
  bin: DynamicHistogramBin;
  axis: HistogramAxis;
  maxCount: number;
  filledMinimumHeight: number;
}) {
  const left = axisPosition(bin.midpoint, axis.min, axis.max);
  const height = Math.max(
    filledMinimumHeight,
    Math.sqrt(bin.count / maxCount) * 100,
  );
  const style = {
    "--bar-tab-left": `${left}%`,
    "--bar-tab-bottom": `calc(${Math.min(84, height)}% + 0.5rem)`,
  } as CSSProperties;

  return (
    <div
      className="pointer-events-none absolute bottom-[var(--bar-tab-bottom)] left-[var(--bar-tab-left)] w-56 -translate-x-1/2 rounded-lg border border-border bg-card p-3 text-xs shadow-lg max-[520px]:bottom-2 max-[520px]:left-0 max-[520px]:right-0 max-[520px]:w-auto max-[520px]:translate-x-0"
      style={style}
      role="status"
      aria-live="polite"
    >
      <p className="font-medium text-foreground">{bin.range}</p>
      <p className="mt-1 text-lg font-semibold leading-6 text-foreground">
        {bin.count.toLocaleString()} runs
      </p>
      <p className="mt-1 leading-5 text-muted-foreground">
        This bar shows one slice of the simulation.
      </p>
    </div>
  );
}

function DistributionViewToggle({
  viewMode,
  setViewMode,
}: {
  viewMode: CustomerUncertaintyViewMode;
  setViewMode: (viewMode: CustomerUncertaintyViewMode) => void;
}) {
  return (
    <div
      className="mt-4 grid w-full max-w-md grid-cols-2 rounded-lg border border-border bg-muted p-1"
      aria-label="Distribution view"
      role="group"
    >
      <Button
        type="button"
        size="sm"
        variant={viewMode === "overview" ? "default" : "ghost"}
        aria-pressed={viewMode === "overview"}
        onClick={() => setViewMode("overview")}
        className="w-full"
      >
        Zoomed out
      </Button>
      <Button
        type="button"
        size="sm"
        variant={viewMode === "zoomed" ? "default" : "ghost"}
        aria-pressed={viewMode === "zoomed"}
        onClick={() => setViewMode("zoomed")}
        className="w-full"
      >
        Zoomed in
      </Button>
    </div>
  );
}

function IntervalPresetButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      variant={active ? "default" : "outline"}
      size="sm"
      onClick={onClick}
    >
      {label}
    </Button>
  );
}

function buildFocusedHistogramAxis(
  simulation: SimulationResult,
): HistogramAxis {
  const spread = Math.max(simulation.p975 - simulation.p025, 0.01);
  const binWidth = chooseDynamicBinWidth(spread);
  const padding = Math.max(spread * 0.45, binWidth * 2);
  const min = Math.max(
    0,
    Math.floor((simulation.p025 - padding) / binWidth) * binWidth,
  );
  const max = Math.min(
    1,
    Math.ceil((simulation.p975 + padding) / binWidth) * binWidth,
  );

  return {
    min,
    max: Math.min(1, Math.max(max, min + binWidth * 6)),
    binWidth,
    sliderStep: Math.min(binWidth, 0.005),
  };
}

function chooseDynamicBinWidth(spread: number) {
  if (spread <= 0.03) {
    return 0.0025;
  }
  if (spread <= 0.06) {
    return 0.005;
  }
  if (spread <= 0.12) {
    return 0.01;
  }
  if (spread <= 0.25) {
    return 0.02;
  }
  return 0.05;
}

function buildHistogramBins(
  samples: number[],
  axis: HistogramAxis,
  limits: { minBins?: number; maxBins?: number } = {},
): DynamicHistogramBin[] {
  const span = Math.max(axis.max - axis.min, axis.binWidth);
  const binCount = clampNumber(
    Math.ceil(span / axis.binWidth),
    limits.minBins ?? 8,
    limits.maxBins ?? 24,
  );
  const actualBinWidth = span / binCount;
  const bins = Array.from({ length: binCount }, (_, index) => {
    const lower = axis.min + actualBinWidth * index;
    const upper = index === binCount - 1 ? axis.max : lower + actualBinWidth;

    return {
      range: `${formatPercent(lower)}-${formatPercent(upper)}`,
      lower,
      upper,
      midpoint: (lower + upper) / 2,
      count: 0,
    };
  });

  for (const sample of samples) {
    if (sample < axis.min || sample > axis.max) {
      continue;
    }
    const index = Math.min(
      binCount - 1,
      Math.max(0, Math.floor(((sample - axis.min) / span) * binCount)),
    );
    bins[index].count += 1;
  }

  return bins;
}

function binsMatch(
  selectedBin: DynamicHistogramBin | undefined,
  bin: DynamicHistogramBin,
) {
  return (
    selectedBin?.range === bin.range &&
    Math.abs(selectedBin.lower - bin.lower) < 0.0001 &&
    Math.abs(selectedBin.upper - bin.upper) < 0.0001
  );
}

function estimateIntervalCoverage(
  samples: number[],
  low: number,
  high: number,
) {
  if (samples.length === 0) {
    return 0;
  }
  const count = samples.reduce(
    (sum, sample) => (sample >= low && sample <= high ? sum + 1 : sum),
    0,
  );
  return count / samples.length;
}

function axisPosition(value: number, min: number, max: number) {
  return clampNumber(((value - min) / Math.max(max - min, 0.01)) * 100, 0, 100);
}

function clusterCalloutLabelPosition(left: number, right: number) {
  const center = (left + right) / 2;
  if (center < 24) {
    return {
      left: clampNumber(right + 2, 0, 82),
      transform: "translateX(0)",
    };
  }
  if (center > 76) {
    return {
      left: clampNumber(left - 2, 18, 100),
      transform: "translateX(-100%)",
    };
  }
  return {
    left: center,
    transform: "translateX(-50%)",
  };
}

function intervalMatches(
  interval: ProbabilityInterval,
  low: number,
  high: number,
) {
  return (
    Math.abs(interval[0] - low) < 0.0001 &&
    Math.abs(interval[1] - high) < 0.0001
  );
}

function CustomerInputReceipt({ run }: { run: ModelRun }) {
  const items = [
    ["Age", String(run.age)],
    ["Pain", valueLabels[run.inputs.painSeverity]],
    ["Fever", `${valueLabels[run.inputs.fever]} (100.4°F or higher)`],
    ["Vomiting", valueLabels[run.inputs.vomiting]],
    ["Observed HR", `${run.heartRateBpm} bpm`],
    ["Simulation runs", run.sampleCount.toLocaleString()],
  ];

  return (
    <div className="rounded-lg border border-border bg-background p-5">
      <p className="font-medium">Inputs used for this range view</p>
      <div className="mt-4 grid grid-cols-6 gap-2 max-[900px]:grid-cols-3 max-[520px]:grid-cols-2">
        {items.map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-border bg-card p-3"
          >
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              {label}
            </p>
            <p className="mt-1 text-sm font-semibold">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
