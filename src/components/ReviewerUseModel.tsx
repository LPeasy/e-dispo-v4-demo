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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { AgeInputField, BinaryField, PageHeader, ReadinessRow, SimulationCountToggle } from "@/components/AppShared";
import { Pas5AcuityInput } from "@/components/Pas5AcuityInput";
import type { ReadinessState, SimulationCount } from "@/appTypes";
import { deriveAgeBand, isPainSeverity, painOptions } from "@/appUtils";
import {
  generalAcuityOptions,
  generalArrivalTransferOptions,
  generalOptionLabel,
  generalSexOptions,
} from "@/data/generalEDispoModel";
import type { Pas5Inputs } from "@/model/aap3Acuity";
import { hypotensionBurdenFromSbp } from "@/model/generalEDispoPrediction";
import { tachycardiaBurdenFromHeartRate } from "@/model/pooledEmpiricalPrediction";
import type {
  BinarySymptom,
  GeneralAcuityCode,
  GeneralArrivalTransferContext,
  GeneralSex,
  PainSeverity,
} from "@/model/types";
import { formatPas5Inputs, valueLabels } from "@/model/worksheet";

type FutureCandidate = {
  title: string;
  status: string;
  whyInactive: string;
  reviewNeed: string;
  currentEffect: string;
};

const futureCandidates: FutureCandidate[] = [
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
  pas5,
  setPas5,
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
  pas5: Pas5Inputs;
  setPas5: (value: Pas5Inputs) => void;
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
        description="Enter the observed inputs used by e-dispo-v4.1. PAS-5 is active as a patient-perceived acuity proxy bridged through an NHAMCS IMMEDR surrogate."
      />
      <section className="grid grid-cols-[minmax(0,1fr)_340px] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Inputs</CardTitle>
            <CardDescription>
              The v4.1 estimate uses age, severe pain status, fever, vomiting,
              heart rate, and PAS-5 high-acuity proxy status.
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
                    Observed heart rate is required for this v4.1 estimate.
                  </FieldDescription>
                ) : null}
              </Field>
              <Pas5AcuityInput
                value={pas5}
                onChange={setPas5}
                idPrefix="reviewer-pas5"
              />
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
              label="PAS-5"
              ready={true}
              detail={formatPas5Inputs(pas5)}
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

export function GeneralUseModelPage({
  age,
  setAge,
  sex,
  setSex,
  acuityCode,
  setAcuityCode,
  arrivalTransferContext,
  setArrivalTransferContext,
  fever,
  setFever,
  heartRateText,
  setHeartRateText,
  heartRateBpm,
  systolicBloodPressureText,
  setSystolicBloodPressureText,
  systolicBloodPressure,
  sampleCount,
  setSampleCount,
  readinessState,
  runError,
  runModel,
}: {
  age: number;
  setAge: (age: number) => void;
  sex: GeneralSex;
  setSex: (value: GeneralSex) => void;
  acuityCode: GeneralAcuityCode;
  setAcuityCode: (value: GeneralAcuityCode) => void;
  arrivalTransferContext: GeneralArrivalTransferContext;
  setArrivalTransferContext: (value: GeneralArrivalTransferContext) => void;
  fever: Exclude<BinarySymptom, "unknown">;
  setFever: (value: Exclude<BinarySymptom, "unknown">) => void;
  heartRateText: string;
  setHeartRateText: (value: string) => void;
  heartRateBpm: number | null;
  systolicBloodPressureText: string;
  setSystolicBloodPressureText: (value: string) => void;
  systolicBloodPressure: number | null;
  sampleCount: SimulationCount;
  setSampleCount: (value: SimulationCount) => void;
  readinessState: ReadinessState;
  runError: string | null;
  runModel: () => void;
}) {
  const tachycardiaBurden =
    heartRateBpm === null ? null : tachycardiaBurdenFromHeartRate(heartRateBpm);
  const hypotensionBurden =
    systolicBloodPressure === null
      ? null
      : hypotensionBurdenFromSbp(systolicBloodPressure);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        icon={Calculator}
        title="Use the General Model"
        description="Enter the prespecified inputs for general-E-Dispo-model-v1-sex-adjusted, a separate all-sex/all-age non-trauma NHAMCS educational model."
      />
      <Alert>
        <Info />
        <AlertTitle>Separate educational model</AlertTitle>
        <AlertDescription>
          This is not the active adult-male abdominal-pain model and is not a
          replacement for it. It is not medical advice, clinical decision
          support, diagnosis, triage, or discharge-safety guidance.
        </AlertDescription>
      </Alert>
      <section className="grid grid-cols-[minmax(0,1fr)_340px] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>General model inputs</CardTitle>
            <CardDescription>
              The sex-adjusted general model uses age, sex, acuity, arrival
              transfer context, fever, heart rate, and systolic blood pressure.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <AgeInputField
                id="general-age-input"
                age={age}
                setAge={setAge}
                description="The general model uses exact age. It centers age at 40, so age 50 becomes 10."
                showCenteredAge
                centerAt={40}
              />
              <div className="grid grid-cols-2 gap-5 max-[720px]:grid-cols-1">
                <GeneralSelectField
                  id="general-sex"
                  label="Sex"
                  value={sex}
                  onChange={setSex}
                  options={generalSexOptions}
                />
                <BinaryField
                  label="Fever"
                  value={fever}
                  onChange={(value) => {
                    if (value !== "unknown") {
                      setFever(value);
                    }
                  }}
                  description="Required yes/no input. Yes means measured temperature is 100.4°F or higher."
                />
              </div>
              <div className="grid grid-cols-2 gap-5 max-[860px]:grid-cols-1">
                <GeneralSelectField
                  id="general-acuity"
                  label="Triage acuity"
                  value={acuityCode}
                  onChange={setAcuityCode}
                  options={generalAcuityOptions}
                />
                <GeneralSelectField
                  id="general-arrival-transfer"
                  label="Arrival transfer context"
                  value={arrivalTransferContext}
                  onChange={setArrivalTransferContext}
                  options={generalArrivalTransferOptions}
                />
              </div>
              <div className="grid grid-cols-2 gap-5 max-[720px]:grid-cols-1">
                <Field>
                  <FieldLabel htmlFor="general-hr-input">
                    Observed heart rate
                  </FieldLabel>
                  <div className="flex gap-2">
                    <input
                      id="general-hr-input"
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
                    tachycardia_burden = max(HR - 100, 0) / 10. Current
                    burden:{" "}
                    {tachycardiaBurden === null
                      ? "pending"
                      : tachycardiaBurden.toFixed(2)}
                    .
                  </FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="general-sbp-input">
                    Observed systolic blood pressure
                  </FieldLabel>
                  <div className="flex gap-2">
                    <input
                      id="general-sbp-input"
                      type="number"
                      min={1}
                      value={systolicBloodPressureText}
                      onChange={(event) =>
                        setSystolicBloodPressureText(event.target.value)
                      }
                      className="h-10 min-w-0 flex-1 rounded-lg border border-input bg-card px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setSystolicBloodPressureText("")}
                    >
                      Clear
                    </Button>
                  </div>
                  <FieldDescription>
                    hypotension_burden = max(100 - SBP, 0) / 10. Current
                    burden:{" "}
                    {hypotensionBurden === null
                      ? "pending"
                      : hypotensionBurden.toFixed(2)}
                    .
                  </FieldDescription>
                </Field>
              </div>
              <FieldSet>
                <FieldLegend>Simulation runs</FieldLegend>
                <SimulationCountToggle
                  sampleCount={sampleCount}
                  setSampleCount={setSampleCount}
                />
                <FieldDescription>
                  Simulation uses bundled joint coefficient draws for this
                  separate general model artifact.
                </FieldDescription>
              </FieldSet>
            </FieldGroup>
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Readiness</CardTitle>
            <CardDescription>
              Unknown and blank source levels are explicit selectable levels.
              Missing vitals still block prediction.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <ReadinessRow
              label="Age"
              ready={Number.isFinite(age) && age >= 0 && age <= 120}
              detail={Number.isFinite(age) ? String(age) : "Required"}
            />
            <ReadinessRow
              label="Sex"
              ready={true}
              detail={generalOptionLabel(generalSexOptions, sex)}
            />
            <ReadinessRow
              label="Acuity"
              ready={true}
              detail={generalOptionLabel(generalAcuityOptions, acuityCode)}
            />
            <ReadinessRow
              label="Arrival context"
              ready={true}
              detail={generalOptionLabel(
                generalArrivalTransferOptions,
                arrivalTransferContext,
              )}
            />
            <ReadinessRow
              label="Heart rate"
              ready={heartRateBpm !== null}
              detail={
                heartRateBpm === null ? "Required" : `${heartRateBpm} bpm`
              }
            />
            <ReadinessRow
              label="SBP"
              ready={systolicBloodPressure !== null}
              detail={
                systolicBloodPressure === null
                  ? "Required"
                  : `${systolicBloodPressure} mmHg`
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
                Inputs are ready. Choose Run model to calculate the general
                source-scope estimate and build the range chart.
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
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>Why these inputs are different</CardTitle>
          <CardDescription>
            This parallel model is broader than the abdominal-pain model.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm leading-6 max-[760px]:grid-cols-1">
          <ReviewerCandidateField
            label="Included"
            value="Pre-disposition age, sex, triage acuity, transfer-in context, fever, HR, and SBP."
          />
          <ReviewerCandidateField
            label="Not included"
            value="Race/ethnicity, payer, region, MSA, pain, vomiting, diagnosis, treatment, imaging, medications, wait time, length of visit, and disposition-derived fields."
          />
          <ReviewerCandidateField
            label="Sex caveat"
            value="Sex is presentation-available but fairness-sensitive. It is included here because you chose to publish the sex-adjusted sensitivity as a separate runnable general model."
          />
          <ReviewerCandidateField
            label="Scope"
            value="All-sex/all-age NHAMCS non-trauma source-scope model. This is not external validation or transportability evidence."
            emphasized
          />
        </CardContent>
      </Card>
    </div>
  );
}

function GeneralSelectField<T extends string>({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: Array<{
    value: T;
    label: string;
    description: string;
  }>;
}) {
  const selectedOption =
    options.find((option) => option.value === value) ?? options[0];

  return (
    <FieldSet>
      <FieldLegend>{label}</FieldLegend>
      <Select value={value} onValueChange={(nextValue) => onChange(nextValue as T)}>
        <SelectTrigger id={id} className="h-10 w-full justify-between">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <FieldDescription>{selectedOption.description}</FieldDescription>
    </FieldSet>
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
            active e-dispo-v4.1 predictors and do not affect current P(admit).
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
