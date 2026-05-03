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
import { coefficientArtifactStatus } from "@/data/empiricalArtifacts";
import { activeEmpiricalModel } from "@/data/eDispoV4Model";
import { modelMetadata } from "@/model/modelParameters";

const excludedVariables = [
  "AAP-3 acuity-proxy concept",
  "SBP",
  "Broad pain region",
  "Onset/duration",
  "Pain pattern",
];

const limitations = [
  "Performance metrics are apparent/exported review metrics and do not establish external transportability.",
  "The model is intentionally compact and omits the AAP-3 acuity-proxy concept, SBP, broad pain region, onset/duration, and pain pattern.",
  "Observed pain and observed HR are required, so estimates are withheld when either required observed field is unavailable.",
  "Pain is collapsed to severe versus non-severe. Mild and moderate are the non-severe reference; this does not claim a monotonic pain dose-response.",
  "Simulation intervals represent coefficient uncertainty in the app method, not individual-level certainty.",
  "The endpoint is limited to same-hospital inpatient admission versus routine ED home disposition after exclusions.",
];

const futureValidationItems = [
  "Add external/source-specific validation and subgroup performance checks.",
  "Add interval estimates for AUROC, Brier score, calibration slope, and calibration-in-the-large.",
  "Add grouped calibration tables and plots using the locked endpoint definition.",
  "Review missingness patterns for observed pain and observed HR before any broader use.",
  "Compare AAP-3 against real triage acuity fields such as NHAMCS IMMEDR or MIMIC triage acuity before any risk-model use.",
  "Evaluate any reintroduction of SBP, broad pain region, onset/duration, or pain pattern as separate empirical work.",
];

export function TechnicalDocsPage({ setPage }: { setPage: (page: Page) => void }) {
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
              The e-dispo-v4.0 reduced empirical model is activated only for transparent
              demonstration, model exploration, and review of uncertainty.
            </p>
          </CardContent>
        </Card>
      </section>
      <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Formula and transformations</CardTitle>
            <CardDescription>Locked active e-dispo-v4.0 specification.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <DefinitionRow
              label="Formula"
              value="admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden"
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
            <DefinitionRow label="Complete-case N" value="3,805" />
            <DefinitionRow label="Admissions" value="459" />
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
            <ResultMetric label="AUROC" value="0.713095417183504" />
            <ResultMetric label="Brier" value="0.0976402591025939" />
            <ResultMetric
              label="Observed prevalence"
              value="0.117546517397583"
            />
            <ResultMetric label="Mean predicted" value="0.117546517398055" />
            <ResultMetric label="Calibration slope" value="1.00000000000481" />
            <ResultMetric
              label="Complete-case N / admissions"
              value="3,805 / 459"
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
