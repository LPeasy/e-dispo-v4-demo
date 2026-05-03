import { ArrowRight, Calculator, Info } from "lucide-react";

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
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { AgeInputField, BinaryField, PageHeader, ReadinessRow, SimulationCountToggle } from "@/components/AppShared";
import type { ReadinessState, SimulationCount } from "@/appTypes";
import { deriveAgeBand, isPainSeverity, painOptions } from "@/appUtils";
import { tachycardiaBurdenFromHeartRate } from "@/model/pooledEmpiricalPrediction";
import type { BinarySymptom, PainSeverity } from "@/model/types";
import { valueLabels } from "@/model/worksheet";

type FutureCandidate = {
  title: string;
  status: string;
  whyInactive: string;
  reviewNeed: string;
  currentEffect: string;
};

const futureCandidates: FutureCandidate[] = [
  {
    title: "AAP-3 acuity-proxy validation concept",
    status: "prototype proxy",
    whyInactive:
      "AAP-3 is a reviewer-only validation concept and is not an active predictor in e-dispo-v4.0.",
    reviewNeed:
      "Future work would need comparison against real acuity fields such as NHAMCS IMMEDR or MIMIC acuity.",
    currentEffect: "Does not affect current P(admit).",
  },
  {
    title: "SBP",
    status: "objective severity candidate",
    whyInactive:
      "Systolic blood pressure could add objective severity context in a future model.",
    reviewNeed:
      "Requires source mapping, missingness review, coefficient fitting, calibration review, and activation gates.",
    currentEffect: "Does not affect current P(admit).",
  },
  {
    title: "Broad pain region",
    status: "conditional proxy candidate",
    whyInactive:
      "Pain location may be useful only if a reliable source mapping can separate regions with enough counts.",
    reviewNeed:
      "Requires validated RFV, chief-complaint, or text mapping before any model use.",
    currentEffect: "Does not affect current P(admit).",
  },
  {
    title: "Onset/duration",
    status: "blocked pending extraction",
    whyInactive:
      "Timing information is not currently a reliable structured input for the active class model.",
    reviewNeed:
      "Requires validated text or structured extraction before review as an empirical predictor.",
    currentEffect: "Does not affect current P(admit).",
  },
  {
    title: "Pain pattern",
    status: "blocked pending extraction",
    whyInactive:
      "Constant or intermittent pain pattern is not currently supported as an active model field.",
    reviewNeed:
      "Requires validated extraction and evidence review before any future model consideration.",
    currentEffect: "Does not affect current P(admit).",
  },
];

export function UseModelPage({
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
  runError,
  runModel,
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
  runError: string | null;
  runModel: () => void;
}) {
  const burden =
    heartRateBpm === null ? null : tachycardiaBurdenFromHeartRate(heartRateBpm);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        icon={Calculator}
        title="Use the Model"
        description="Enter the observed inputs used by e-dispo-v4.0. Run it when the fields are ready."
      />
      <section className="grid grid-cols-[minmax(0,1fr)_340px] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Inputs</CardTitle>
            <CardDescription>
              The v4 estimate uses age, severe pain status, fever, vomiting, and heart rate.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <AgeInputField
                id="age-input"
                age={age}
                setAge={setAge}
                description="The model uses exact age. It centers age at 42, so age 50 becomes 8."
                showCenteredAge
              />
              <FieldSet>
                <FieldLegend>Pain severity</FieldLegend>
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
                  description="Required yes/no input. Yes activates the vomiting term."
                />
              </div>
              <Field>
                <FieldLabel htmlFor="hr-input">Observed heart rate</FieldLabel>
                <div className="flex gap-2">
                  <input
                    id="hr-input"
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
                  Only heart rate above 100 changes the tachycardia burden. HR
                  110 equals 1 burden unit, meaning 10 bpm above 100. Current
                  burden:{" "}
                  {burden === null ? "pending" : burden.toFixed(2)}.
                </FieldDescription>
                {heartRateBpm === null ? (
                  <FieldDescription className="font-medium text-destructive">
                    Observed heart rate is required for this v4 estimate.
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
                  Simulation means repeated model runs. More runs make the
                  range chart smoother. They do not change the model.
                </FieldDescription>
              </FieldSet>
            </FieldGroup>
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Readiness</CardTitle>
            <CardDescription>
              The app waits for required fields and an explicit Run model click.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <ReadinessRow
              label="Age"
              ready={deriveAgeBand(age) !== null}
              detail={deriveAgeBand(age) ?? "Enter 18-64"}
            />
            <ReadinessRow
              label="Pain"
              ready={true}
              detail={valueLabels[painSeverity]}
            />
            <ReadinessRow
              label="Heart rate"
              ready={heartRateBpm !== null}
              detail={
                heartRateBpm === null ? "Required" : `${heartRateBpm} bpm`
              }
            />
            <Separator />
            {readinessState.error || runError ? (
              <Alert>
                <Info />
                <AlertTitle>Result pending</AlertTitle>
                <AlertDescription>
                  {runError ?? readinessState.error}
                </AlertDescription>
              </Alert>
            ) : (
              <div className="rounded-lg border border-border bg-background p-4 text-sm leading-6 text-muted-foreground">
                Inputs are ready. Choose Run model to calculate the main
                estimate and build the range chart.
              </div>
            )}
            <Button
              type="button"
              disabled={!readinessState.canRun}
              onClick={runModel}
            >
              Run model
              <ArrowRight data-icon="inline-end" />
            </Button>
          </CardContent>
        </Card>
      </section>
      <InactiveFutureCandidatesSection />
    </div>
  );
}

function InactiveFutureCandidatesSection() {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">
            Inactive / Future Review Candidates
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            These concepts are shown for reviewer context only. They are not
            active e-dispo-v4.0 predictors and do not affect current P(admit).
          </p>
        </div>
        <Badge variant="outline">review-only</Badge>
      </div>
      <div className="grid grid-cols-2 gap-4 max-[760px]:grid-cols-1">
        {futureCandidates.map((candidate) => (
          <Card key={candidate.title} className="rounded-lg" size="sm">
            <CardHeader className="gap-2">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <CardTitle className="text-base leading-6">
                  {candidate.title}
                </CardTitle>
                <Badge variant="secondary" className="w-fit">
                  {candidate.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm leading-6">
              <ReviewerCandidateField
                label="Status"
                value={candidate.status}
              />
              <ReviewerCandidateField
                label="Why inactive"
                value={candidate.whyInactive}
              />
              <ReviewerCandidateField
                label="Review need"
                value={candidate.reviewNeed}
              />
              <ReviewerCandidateField
                label="Current effect on P(admit)"
                value={candidate.currentEffect}
                emphasized
              />
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function ReviewerCandidateField({
  label,
  value,
  emphasized = false,
}: {
  label: string;
  value: string;
  emphasized?: boolean;
}) {
  return (
    <div
      className={
        emphasized
          ? "rounded-lg border border-primary/20 bg-primary/5 p-3"
          : "rounded-lg border border-border bg-background p-3"
      }
    >
      <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <p
        className={
          emphasized
            ? "mt-1 font-medium text-foreground"
            : "mt-1 text-muted-foreground"
        }
      >
        {value}
      </p>
    </div>
  );
}
