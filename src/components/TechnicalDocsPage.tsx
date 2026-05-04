import { FileText } from "lucide-react";

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CompactList, DefinitionRow, PageHeader, ResultMetric } from "@/components/AppShared";
import type { Page } from "@/appTypes";
import { isGeneralEDispoVariant } from "@/appVariant";
import { coefficientArtifactStatus } from "@/data/empiricalArtifacts";
import { activeEmpiricalModel } from "@/data/eDispoV4Model";
import {
  generalEDispoModel,
  GENERAL_E_DISPO_PUBLIC_MODEL_ID,
} from "@/data/generalEDispoModel";
import { modelMetadata } from "@/model/modelParameters";

const excludedVariables = [
  "SBP",
  "Broad pain region",
  "Onset/duration",
  "Pain pattern",
];

const limitations = [
  "Performance metrics are apparent/exported review metrics and do not establish external transportability.",
  "The model is intentionally compact and still omits SBP, broad pain region, onset/duration, and pain pattern.",
  "Observed pain and observed HR are required, so estimates are withheld when either required observed field is unavailable.",
  "Pain is collapsed to severe versus non-severe. Mild and moderate are the non-severe reference; this does not claim a monotonic pain dose-response.",
  "Simulation intervals represent coefficient uncertainty in the app method, not individual-level certainty.",
  "The endpoint is limited to same-hospital inpatient admission versus routine ED home disposition after exclusions.",
  "PAS-5 is active only as high_acuity_proxy: A1/A2 activate the term, while A3/A4/A5 are reference.",
  "NHAMCS does not contain direct PAS-5 patient answers. The PAS-5 coefficient is derived from IMMEDR as a clinician-acuity surrogate and must not be read as direct patient self-assessment validation.",
];

const futureValidationItems = [
  "Review the new grouped calibration, subgroup, missingness, fixed-prediction interval, and optimism-correction artifacts as internal educational validation only.",
  "Build an adequate external/source-specific validation cohort before making any transportability claim.",
  "Review race/ethnicity, payer, region, and MSA subgroup rows; small payer levels remain sparse-cell or no-outcome blockers.",
  "Add subgroup interval estimates for calibration, AUROC, and Brier where event counts and survey design support them.",
  "Validate PAS-5 prospectively or in another direct patient-answer source before treating the proxy as direct self-acuity evidence.",
  "Evaluate any reintroduction of SBP, broad pain region, onset/duration, or pain pattern as separate empirical work.",
];

const formatPerformanceInterval = (
  metric: "auroc" | "brier_score"
): string => {
  const row = activeEmpiricalModel.performance_intervals?.find(
    (interval) => interval.metric === metric
  );

  if (!row) {
    return "Not available";
  }

  const level = Math.round(row.interval_level * 100);

  return `${row.ci_low.toFixed(6)} to ${row.ci_high.toFixed(6)} (${level}% apparent)`;
};

export function TechnicalDocsPage({ setPage }: { setPage: (page: Page) => void }) {
  if (isGeneralEDispoVariant) {
    return <GeneralTechnicalDocsPage setPage={setPage} />;
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        icon={FileText}
        title="Technical Docs"
        description="Model review package and defense of specification for the active E-Dispo class model."
        action={
          <Button
            type="button"
            variant="outline"
            onClick={() => setPage("explorer")}
          >
            Review formula
          </Button>
        }
      />
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Model identity</CardTitle>
            <CardDescription>
              Active model and intended endpoint.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 max-[620px]:grid-cols-1">
            <DefinitionRow
              label="model_id"
              value={activeEmpiricalModel.model_id}
            />
            <DefinitionRow label="Run id" value={activeEmpiricalModel.run_id} />
            <DefinitionRow
              label="Population"
              value="Adult men 18-64, ED, non-traumatic abdominal pain"
            />
            <DefinitionRow
              label="Endpoint"
              value="Same-hospital inpatient admission vs routine ED home disposition after exclusions"
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Activation decision</CardTitle>
            <CardDescription>
              Scope approved for this proof-of-concept shell.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Badge
              variant={
                coefficientArtifactStatus.valid ? "default" : "secondary"
              }
              className="w-fit"
            >
              {coefficientArtifactStatus.label}
            </Badge>
            <p>
              E-Dispo is an educational and statistical class prototype. It is
              not real clinical decision support, medical advice, a patient-care
              workflow, or a production medical device.
            </p>
            <p>
              The e-dispo-v4.1 PAS-5 high-acuity surrogate model is activated
              only for transparent demonstration, model exploration, and review
              of uncertainty.
            </p>
          </CardContent>
        </Card>
      </section>
      <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Formula and transformations</CardTitle>
            <CardDescription>Locked active e-dispo-v4.1 specification.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Formula"
              value="admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy"
            />
            <DefinitionRow label="age_centered" value="age - 42" />
            <DefinitionRow
              label="tachycardia_burden"
              value="max(HR - 100, 0) / 10"
            />
            <DefinitionRow
              label="Pain handling"
              value="Observed severe pain activates pain_severe. Mild and moderate are the non-severe reference."
            />
            <DefinitionRow
              label="PAS-5 handling"
              value="A1/A2 activate high_acuity_proxy; A3/A4/A5 are reference."
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Required observed fields</CardTitle>
            <CardDescription>
              Missingness policy used by the class app.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Observed pain"
              value="Required. Missing pain is not an active input path."
            />
            <DefinitionRow
              label="Observed HR"
              value="Required. Missing HR blocks prediction."
            />
            <DefinitionRow
              label="Fever"
              value="Required yes/no in the app. Yes means measured temperature is 100.4°F or higher and activates fever_or_temp."
            />
            <DefinitionRow
              label="Vomiting"
              value="Required yes/no in the app. Yes activates vomiting_present."
            />
            <DefinitionRow
              label="PAS-5"
              value="Required five-question patient-perceived acuity proxy. A1/A2 activate the surrogate term."
            />
          </CardContent>
        </Card>
      </section>
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>Active predictors and coefficients</CardTitle>
          <CardDescription>
            Coefficients are log-odds weights; positive values move the estimate
            upward.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Predictor</TableHead>
                  <TableHead>Level/rule</TableHead>
                  <TableHead>Beta</TableHead>
                  <TableHead>SE/SD</TableHead>
                  <TableHead>Source status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeEmpiricalModel.predictors.map((predictor) => (
                  <TableRow key={`${predictor.term}-${predictor.level}`}>
                    <TableCell className="font-medium">
                      {predictor.term}
                    </TableCell>
                    <TableCell>{predictor.level || "intercept"}</TableCell>
                    <TableCell>{String(predictor.center_beta)}</TableCell>
                    <TableCell>{String(predictor.se_or_sd)}</TableCell>
                    <TableCell>{predictor.evidence_tier}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>PAS-5 surrogate evidence</CardTitle>
            <CardDescription>
              Active proxy term and source limitation.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Active term"
              value="high_acuity_proxy = 1 when PAS-5 maps to A1 or A2"
            />
            <DefinitionRow
              label="Reference"
              value="PAS-5 A3/A4/A5"
            />
            <DefinitionRow
              label="Surrogate source"
              value="NHAMCS IMMEDR clinician-acuity surrogate"
            />
            <DefinitionRow
              label="Limitation"
              value="Direct PAS-5 patient answers are not observed in NHAMCS."
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>PAS-5 gate summary</CardTitle>
            <CardDescription>
              Deterministic candidate screen rerun on 2026-05-04.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="High-acuity beta"
              value="1.24984421126593; OR 3.48979924370436"
            />
            <DefinitionRow
              label="High-acuity cell"
              value="n=163, events=53, non-events=110"
            />
            <DefinitionRow
              label="Base refit AUROC / Brier"
              value="0.736367002137274 / 0.093767198895187"
            />
            <DefinitionRow
              label="Stability caveat"
              value="Mean leave-one-year-out gate passed, but 2018 heldout worsened."
            />
          </CardContent>
        </Card>
      </section>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Reference categories</CardTitle>
            <CardDescription>
              Terms that define zero contribution for categorical predictors.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow label="pain_severe" value="Non-severe pain: mild or moderate" />
            <DefinitionRow
              label="fever_or_temp"
              value="No not activated; Yes means measured temperature is 100.4°F or higher"
            />
            <DefinitionRow label="vomiting_present" value="No not activated" />
            <DefinitionRow
              label="tachycardia_burden"
              value="HR at or below 100 bpm gives 0 burden"
            />
            <DefinitionRow
              label="high_acuity_proxy"
              value="PAS-5 A3/A4/A5; A1/A2 activate the surrogate term"
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Dataset/source status</CardTitle>
            <CardDescription>
              Evidence source and complete-case summary.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Coefficient source"
              value={activeEmpiricalModel.coefficient_source}
            />
            <DefinitionRow
              label="Dataset sources"
              value={activeEmpiricalModel.dataset_sources.join(", ")}
            />
            <DefinitionRow label="Strict binary pooled N" value="3,805" />
            <DefinitionRow label="Strict binary admissions" value="459" />
            <DefinitionRow label="PAS-5/IMMEDR fit complete-case N" value="2,245" />
            <DefinitionRow label="PAS-5/IMMEDR fit admissions" value="254" />
          </CardContent>
        </Card>
      </section>
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>Performance metrics</CardTitle>
          <CardDescription>
            Apparent/exported metrics for review; not external validation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3 max-[900px]:grid-cols-2 max-[560px]:grid-cols-1">
            <ResultMetric label="AUROC" value="0.759077823237526" />
            <ResultMetric
              label="AUROC apparent interval"
              value={formatPerformanceInterval("auroc")}
            />
            <ResultMetric label="Brier" value="0.091311819980443" />
            <ResultMetric
              label="Brier apparent interval"
              value={formatPerformanceInterval("brier_score")}
            />
            <ResultMetric
              label="Observed prevalence"
              value="0.113520799110049"
            />
            <ResultMetric label="Mean predicted" value="0.113520799126063" />
            <ResultMetric label="Calibration slope" value="1.00000000017151" />
            <ResultMetric
              label="Complete-case N / admissions"
              value="2,245 / 254"
            />
            <ResultMetric
              label="LOO AUROC gain"
              value="+0.0195420688224538"
            />
            <ResultMetric
              label="LOO Brier change"
              value="-0.00224960097683449"
            />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 max-[760px]:grid-cols-1">
            <DefinitionRow
              label="AUROC"
              value="Ranking performance; higher means better separation."
            />
            <DefinitionRow
              label="Brier"
              value="Average probability error; lower is better."
            />
            <DefinitionRow
              label="Observed prevalence"
              value="How often admission appeared in the complete-case data."
            />
            <DefinitionRow
              label="Mean predicted"
              value="Average model probability across the same data."
            />
            <DefinitionRow
              label="Calibration slope"
              value="Whether estimates are too compressed or too spread out."
            />
            <DefinitionRow
              label="Coefficients"
              value="Log-odds weights; positive values move the estimate upward."
            />
          </div>
        </CardContent>
      </Card>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Uncertainty method</CardTitle>
            <CardDescription>
              How Results generates the uncertainty display.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Distribution"
              value="The app samples bundled joint coefficient vectors, applies the fixed selected inputs, then recalculates P(admit) many times."
            />
            <DefinitionRow
              label="Simulation counts"
              value="1,000, 10,000, or 100,000 user-selected Monte Carlo draws"
            />
            <DefinitionRow label="Seed" value={String(modelMetadata.seed)} />
            <DefinitionRow
              label="Displayed intervals"
              value="Central 80% and central 95% simulated P(admit) intervals"
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Excluded variables</CardTitle>
            <CardDescription>Not active in this model.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {excludedVariables.map((variable) => (
              <Badge key={variable} variant="secondary">
                {variable}
              </Badge>
            ))}
          </CardContent>
        </Card>
      </section>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Limitations</CardTitle>
            <CardDescription>
              Boundaries that constrain interpretation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CompactList items={limitations} />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Future validation</CardTitle>
            <CardDescription>
              Work required before any stronger claim.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CompactList items={futureValidationItems} />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function GeneralTechnicalDocsPage({ setPage }: { setPage: (page: Page) => void }) {
  const limitations = [
    "This is a parallel educational/statistical model, not a replacement for the adult-male abdominal-pain model.",
    "Metrics are apparent NHAMCS source-scope review metrics and do not establish external validation or transportability.",
    "Sex is presentation-available but fairness-sensitive; inclusion is not endorsed by apparent performance alone.",
    "Race/ethnicity, payer, region, and MSA remain subgroup/fairness review variables only, not fitted predictors.",
    "Transfers are excluded from the admit-vs-routine-home model target.",
    "Simulation intervals represent coefficient uncertainty in the app method, not individual-level certainty.",
  ];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        icon={FileText}
        title="Technical Docs"
        description="Review package summary for the separate general-E-Dispo sex-adjusted all-sex/all-age non-trauma model."
        action={
          <Button
            type="button"
            variant="outline"
            onClick={() => setPage("explorer")}
          >
            Review formula
          </Button>
        }
      />
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Model identity</CardTitle>
            <CardDescription>
              Separate public runnable model and source artifact.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 max-[620px]:grid-cols-1">
            <DefinitionRow label="model_id" value={GENERAL_E_DISPO_PUBLIC_MODEL_ID} />
            <DefinitionRow
              label="Source artifact"
              value={generalEDispoModel.sourceArtifactId}
            />
            <DefinitionRow
              label="Population"
              value="All-sex/all-age NHAMCS 2018-2022 non-trauma ED records"
            />
            <DefinitionRow
              label="Endpoint"
              value="Same-hospital admission vs routine home discharge; transfer excluded from fitting"
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Boundary</CardTitle>
            <CardDescription>
              Public interpretation guardrails.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Badge variant="outline">parallel model</Badge>
            <p>
              This general model is educational and statistical only. It is not
              clinical decision support, medical advice, diagnosis, triage,
              discharge-safety guidance, or a production medical device.
            </p>
            <p>
              The adult-male abdominal-pain E-Dispo model remains separate.
              This site exposes a broader all-sex/all-age non-trauma model as a
              second runnable demo.
            </p>
          </CardContent>
        </Card>
      </section>
      <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Formula and transformations</CardTitle>
            <CardDescription>Public sex-adjusted general specification.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow label="Formula" value={generalEDispoModel.formula} />
            <DefinitionRow label="age_centered_40" value="age - 40" />
            <DefinitionRow
              label="tachycardia_burden"
              value="max(HR - 100, 0) / 10"
            />
            <DefinitionRow
              label="hypotension_burden"
              value="max(100 - SBP, 0) / 10"
            />
            <DefinitionRow
              label="References"
              value="Sex code 1, urgent acuity, and no transfer-in context are reference categories."
            />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Required observed fields</CardTitle>
            <CardDescription>
              Missingness policy used by this public model.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Required"
              value="Age, sex, acuity, arrival transfer context, fever yes/no, HR, and SBP"
            />
            <DefinitionRow
              label="Explicit source levels"
              value="Unknown and blank acuity/arrival levels are selectable levels, not silent missingness."
            />
            <DefinitionRow
              label="Blocked"
              value="Missing HR or missing SBP withholds the estimate."
            />
          </CardContent>
        </Card>
      </section>
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>Fitted predictors and coefficients</CardTitle>
          <CardDescription>
            Coefficients are log-odds weights; positive values move the estimate
            upward.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Predictor</TableHead>
                  <TableHead>Level/rule</TableHead>
                  <TableHead>Beta</TableHead>
                  <TableHead>SE</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {generalEDispoModel.coefficients.map((coefficient) => (
                  <TableRow key={coefficient.key}>
                    <TableCell className="font-medium">
                      {coefficient.term}
                    </TableCell>
                    <TableCell>{coefficient.level || "intercept"}</TableCell>
                    <TableCell>{String(coefficient.beta)}</TableCell>
                    <TableCell>{String(coefficient.standardError)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>Performance metrics</CardTitle>
          <CardDescription>
            Apparent NHAMCS source-scope metrics for review; not external
            validation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3 max-[900px]:grid-cols-2 max-[560px]:grid-cols-1">
            <ResultMetric
              label="AUROC"
              value={String(generalEDispoModel.apparentPerformance.auroc)}
            />
            <ResultMetric
              label="Brier"
              value={String(generalEDispoModel.apparentPerformance.brierScore)}
            />
            <ResultMetric
              label="Calibration slope"
              value={String(
                generalEDispoModel.apparentPerformance.calibrationSlope,
              )}
            />
            <ResultMetric
              label="Observed prevalence"
              value={String(
                generalEDispoModel.apparentPerformance.observedPrevalence,
              )}
            />
            <ResultMetric
              label="Complete-case N / admissions"
              value={`${generalEDispoModel.cohortCounts.completeCaseRows.toLocaleString()} / ${generalEDispoModel.cohortCounts.completeCaseAdmissionEvents.toLocaleString()}`}
            />
            <ResultMetric
              label="Endpoint N / admissions"
              value={`${generalEDispoModel.cohortCounts.endpointRows.toLocaleString()} / ${generalEDispoModel.cohortCounts.admissionEvents.toLocaleString()}`}
            />
          </div>
        </CardContent>
      </Card>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Uncertainty method</CardTitle>
            <CardDescription>
              How Results generates the uncertainty display.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Distribution"
              value="The app samples bundled joint coefficient vectors generated from the plus-sex covariance artifact, applies fixed selected inputs, then recalculates P(admit)."
            />
            <DefinitionRow
              label="Simulation counts"
              value="1,000, 10,000, or 100,000 user-selected Monte Carlo draws"
            />
            <DefinitionRow label="Draw seed" value="20260429" />
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Limitations</CardTitle>
            <CardDescription>
              Boundaries that constrain interpretation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CompactList items={limitations} />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
