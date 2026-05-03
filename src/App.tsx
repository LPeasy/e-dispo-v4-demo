import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  Calculator,
  FileText,
  Gauge,
  Home,
  Info,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Table2,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";

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
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatPercent } from "@/model/logisticModel";
import { modelMetadata } from "@/model/modelParameters";
import {
  predictPooledEmpiricalDisposition,
  toPooledEmpiricalPredictionInputs,
} from "@/model/pooledEmpiricalPrediction";
import type {
  BinarySymptom,
  ModelInputs,
  PainSeverity,
  PredictionResult,
  SimulationResult,
} from "@/model/types";
import { useSimulationWorker } from "@/model/useSimulationWorker";
import type { SimulationWorkerState } from "@/model/useSimulationWorker";
import { valueLabels } from "@/model/worksheet";
import type { ModelRun, Page, SimulationCount } from "@/appTypes";
import { DefinitionRow, PageHeader, ResultMetric } from "@/components/AppShared";
import { CustomerPreviewPage } from "@/components/CustomerPreview";
import { TechnicalDocsPage } from "@/components/TechnicalDocsPage";
import { UseModelPage } from "@/components/ReviewerUseModel";
import {
  buildModelRunKey,
  buildReadinessState,
  clampNumber,
  deriveAgeBand,
  formatCoefficient,
  parseHeartRate,
} from "@/appUtils";
import { cn } from "@/lib/utils";

type ArcadeMode = "ready" | "playing" | "paused" | "over";
type ArcadePhase = 1 | 2 | 3;
type ArcadePatternId =
  | "single-left"
  | "single-center"
  | "single-right"
  | "two-lane-gap-left"
  | "two-lane-gap-center"
  | "two-lane-gap-right"
  | "gate-after-obstacle"
  | "recovery-gap";
type SimulationSummary = {
  median: number;
  p025: number;
  p975: number;
  sampleCount: number;
  seed: number;
};
type SavedModelRun = ModelRun & {
  id: string;
  name: string;
  createdAt: string;
  simulationSummary: SimulationSummary | null;
};
const runDifferenceFields: Array<{ id: keyof ModelInputs; label: string }> = [
  { id: "ageBand", label: "Age band" },
  { id: "painSeverity", label: "Pain" },
  { id: "fever", label: "Fever" },
  { id: "vomiting", label: "Vomiting" },
];
type ArcadeHud = {
  mode: ArcadeMode;
  score: number;
  bestScore: number;
  timeLeft: number;
  phase: ArcadePhase;
  combo: number;
  audioMuted: boolean;
  breakdown: ArcadeScoreBreakdown;
};
type ArcadeEntity = {
  id: number;
  lane: number;
  type: "traffic" | "gate";
  x: number;
  y: number;
  width: number;
  height: number;
  nearMissAwarded?: boolean;
};
type ArcadeEffectType = "pickup" | "near-miss" | "collision" | "combo";
type ArcadeSound = "start" | "pickup" | "collision" | "near-miss";
type ArcadeEffect = {
  id: number;
  type: ArcadeEffectType;
  x: number;
  y: number;
  text: string;
  age: number;
  duration: number;
};
type ArcadeScoreBreakdown = {
  distance: number;
  gatesCollected: number;
  nearMisses: number;
  comboBonus: number;
  finalScore: number;
  bestScore: number;
};
type ArcadeRuntime = {
  audioMuted: boolean;
  bestScore: number;
  breakdown: ArcadeScoreBreakdown;
  collisionFlash: number;
  combo: number;
  comboBonus: number;
  comboTimer: number;
  currentPattern: ArcadePatternId | "none";
  distance: number;
  entities: ArcadeEntity[];
  eventLog: string[];
  effects: ArcadeEffect[];
  elapsedTime: number;
  gateTimer: number;
  gatesCollected: number;
  idCounter: number;
  keys: {
    left: boolean;
    right: boolean;
  };
  mode: ArcadeMode;
  nearMisses: number;
  obstacleTimer: number;
  phase: ArcadePhase;
  playerX: number;
  reducedMotion: boolean;
  roadOffset: number;
  runFinalized: boolean;
  score: number;
  seed: number;
  shakeTime: number;
  soundEvents: ArcadeSound[];
  speed: number;
  timeLeft: number;
};


type ExplorerNodeId =
  | "age"
  | "pain"
  | "fever"
  | "vomiting"
  | "heartRate"
  | "logistic"
  | "simulation"
  | "endpoint";
type ExplorerNode = {
  id: ExplorerNodeId;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  group: "Input" | "Model" | "Output";
  role: string;
  direction: string;
  rule: string;
  source: string;
  uncertainty: string;
  why: string;
  beta?: string;
};

const HistogramChart = lazy(() =>
  import("@/components/ModelCharts").then((module) => ({
    default: module.HistogramChart,
  })),
);

const navigationItems: Array<{
  id: Page;
  label: string;
  mobileLabel: string;
  tooltip: string;
  icon: LucideIcon;
}> = [
  {
    id: "landing",
    label: "Landing",
    mobileLabel: "Home",
    tooltip: "Open the E-Dispo overview",
    icon: Home,
  },
  {
    id: "customer",
    label: "Customer Preview",
    mobileLabel: "Preview",
    tooltip: "Open the guided customer preview",
    icon: ShieldCheck,
  },
  {
    id: "explorer",
    label: "Model Explorer",
    mobileLabel: "Model",
    tooltip: "See how the model is put together",
    icon: BarChart3,
  },
  {
    id: "use",
    label: "Use the Model",
    mobileLabel: "Use",
    tooltip: "Enter model inputs",
    icon: Calculator,
  },
  {
    id: "results",
    label: "Results",
    mobileLabel: "Results",
    tooltip: "Open the saved run results",
    icon: Gauge,
  },
  {
    id: "docs",
    label: "Technical Docs",
    mobileLabel: "Docs",
    tooltip: "Open the technical documentation",
    icon: FileText,
  },
];

const explorerNodes: ExplorerNode[] = [
  {
    id: "age",
    label: "Exact age",
    shortLabel: "Age",
    icon: Gauge,
    group: "Input",
    role: "Age helps the model account for different admission patterns in the 18-64 class group.",
    direction:
      "In this fitted model, a higher age usually moves the estimate upward.",
    rule: "The app subtracts 42 from the entered age, so age 50 becomes age_centered 8.",
    source: "Comes from the fitted e-dispo-v4.0 model export.",
    uncertainty:
      "The model treats each added year the same way. That is a statistical shortcut.",
    why: "Age can track health burden and different ED disposition patterns within the modeled group.",
    beta: "Technical detail: beta 0.043118787834530395 per year centered at 42",
  },
  {
    id: "pain",
    label: "Pain severity",
    shortLabel: "Pain",
    icon: Activity,
    group: "Input",
    role: "Pain severity tells the model whether severe pain was recorded.",
    direction:
      "Severe pain usually moves the estimate upward compared with non-severe pain in the current v4 fit.",
    rule: "Mild and moderate are the non-severe comparison point. Severe adds beta 0.52181881795062.",
    source: "Comes from the fitted e-dispo-v4.0 model export.",
    uncertainty:
      "Pain is collapsed to severe versus non-severe. This is not a monotonic pain claim.",
    why: "Pain intensity can reflect the visit, the documentation, or other features related to disposition.",
  },
  {
    id: "fever",
    label: "Fever",
    shortLabel: "Fever",
    icon: Activity,
    group: "Input",
    role: "This input tells the model whether fever or a high-temperature proxy was recorded.",
    direction: "A yes value usually moves the estimate upward.",
    rule: "The app asks for a required yes/no fever value. Yes means an observed temperature of 100.4 F or higher and activates the fever_or_temp term. Beta 0.8870420313203969 when active.",
    source: "Comes from the fitted e-dispo-v4.0 model export.",
    uncertainty: "Proxy mapping can vary by dataset and documentation source.",
    why: "Fever or high temperature can track visit severity and disposition patterns.",
  },
  {
    id: "vomiting",
    label: "Vomiting",
    shortLabel: "Vomiting",
    icon: Activity,
    group: "Input",
    role: "Vomiting tells the model whether this symptom was recorded.",
    direction: "A yes value usually moves the estimate upward.",
    rule: "The app asks for a required yes/no vomiting value. Yes activates the vomiting_present term; no does not. Beta 0.46912257968096427 when active.",
    source: "Comes from the fitted e-dispo-v4.0 model export.",
    uncertainty: "Vomiting may be recorded differently across source systems.",
    why: "Vomiting can relate to symptom burden, dehydration concerns, and ED observation patterns.",
  },
  {
    id: "heartRate",
    label: "Observed HR / tachycardia burden",
    shortLabel: "HR burden",
    icon: Gauge,
    group: "Input",
    role: "Heart rate only changes the model when it is above 100 bpm.",
    direction: "Higher HR above 100 bpm usually moves the estimate upward.",
    rule: "tachycardia_burden = max(HR - 100, 0) / 10. HR 110 equals 1 burden unit. Here, burden means 10 bpm above 100. Beta 0.4269432162227637 per unit.",
    source: "Comes from the fitted e-dispo-v4.0 model export.",
    uncertainty:
      "Observed HR is required. Missing HR blocks prediction in this class app.",
    why: "Heart rate above 100 can track physiologic stress and disposition patterns.",
  },
  {
    id: "logistic",
    label: "Logistic model",
    shortLabel: "Logistic model",
    icon: Calculator,
    group: "Model",
    role: "The model adds the active pieces together. Then it turns that total into a probability.",
    direction:
      "Positive active terms usually move P(admit) upward; negative active terms move it downward.",
    rule: "Formula: admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden.",
    source:
      "The active prototype shell uses model_id e-dispo-v4.0.",
    uncertainty:
      "This model is intentionally compact, so it cannot represent every source of variation.",
    why: "Logistic regression is a transparent way to combine inputs into a probability estimate.",
  },
  {
    id: "simulation",
    label: "Simulation range",
    shortLabel: "Uncertainty",
    icon: BarChart3,
    group: "Model",
    role: "A simulation means many repeated model runs. It shows how much the estimate can move.",
    direction:
      "It does not push the main estimate up or down by itself.",
    rule: "Users can run 1,000, 10,000, or 100,000 draws using the fixed class seed.",
    source:
      "Uses bundled joint coefficient draws from the reviewed pooled empirical artifact.",
    uncertainty:
      "The interval shows model uncertainty. It is not a guarantee about an individual case.",
    why: "A range helps users see how much the estimate moves when the fitted model numbers vary.",
  },
  {
    id: "endpoint",
    label: "P(admit) endpoint",
    shortLabel: "P(admit)",
    icon: FileText,
    group: "Output",
    role: "P(admit) means the model's probability for same-hospital inpatient admission in the strict binary cohort.",
    direction:
      "This is the final output, not a predictor with its own direction of effect.",
    rule: "Binary endpoint after exclusions: same-hospital inpatient admission vs routine ED home disposition.",
    source:
      "Defined by the e-dispo-v4.0 model artifact and documented in Technical Docs.",
    uncertainty:
      "Excluded disposition categories are not estimated by this endpoint.",
    why: "One locked endpoint keeps the demo easier to read and review.",
  },
];

const defaultModelInputs: ModelInputs = {
  ageBand: "30_44",
  broadPainRegion: "diffuse_or_hard_to_pinpoint",
  painSeverity: "moderate",
  onsetDurationCategory: "unknown",
  constantVsIntermittent: "unknown",
  vomiting: "no",
  fever: "no",
};

function App() {
  const [page, setPage] = useState<Page>("landing");
  const [age, setAge] = useState(42);
  const [painSeverity, setPainSeverity] = useState<PainSeverity>("moderate");
  const [fever, setFever] = useState<BinarySymptom>("no");
  const [vomiting, setVomiting] = useState<BinarySymptom>("no");
  const [heartRateText, setHeartRateText] = useState("88");
  const [sampleCount, setSampleCount] = useState<SimulationCount>(10000);
  const [modelRun, setModelRun] = useState<ModelRun | null>(null);
  const [customerRun, setCustomerRun] = useState<ModelRun | null>(null);
  const [runNameDraft, setRunNameDraft] = useState("Run 1");
  const [savedRuns, setSavedRuns] = useState<SavedModelRun[]>([]);
  const [selectedSavedRunIds, setSelectedSavedRunIds] = useState<string[]>([]);
  const [compareDockCollapsed, setCompareDockCollapsed] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [customerRunError, setCustomerRunError] = useState<string | null>(null);
  const [customerScopeAccepted, setCustomerScopeAccepted] = useState(false);
  const [customerDisclaimerAccepted, setCustomerDisclaimerAccepted] =
    useState(false);
  const [arcadeOpen, setArcadeOpen] = useState(false);
  const [arcadeBestScore, setArcadeBestScore] = useState(0);
  const [, setPrototypeClicks] = useState(0);
  const prototypeResetRef = useRef<number | null>(null);

  const heartRateBpm = parseHeartRate(heartRateText);
  const ageBand = deriveAgeBand(age);
  const inputs = useMemo<ModelInputs>(
    () => ({
      ...defaultModelInputs,
      ageBand: ageBand ?? "30_44",
      painSeverity,
      fever,
      vomiting,
    }),
    [ageBand, fever, painSeverity, vomiting],
  );
  const readinessState = useMemo(
    () => buildReadinessState(age, heartRateBpm),
    [age, heartRateBpm],
  );
  const currentRunKey = useMemo(
    () => buildModelRunKey(inputs, age, heartRateBpm, sampleCount),
    [age, heartRateBpm, inputs, sampleCount],
  );
  const activeRun = modelRun?.key === currentRunKey ? modelRun : null;
  const activeCustomerRun =
    customerRun?.key === currentRunKey ? customerRun : null;
  const runModel = () => {
    if (!readinessState.canRun || heartRateBpm === null) {
      return;
    }

    try {
      const prediction = predictPooledEmpiricalDisposition(
        toPooledEmpiricalPredictionInputs(inputs, age, heartRateBpm),
      );
      setRunError(null);
      setModelRun({
        key: currentRunKey,
        age,
        heartRateBpm,
        inputs,
        prediction,
        sampleCount,
      });
      setPage("results");
    } catch (error) {
      setRunError(
        error instanceof Error ? error.message : "Prediction failed.",
      );
    }
  };
  const runCustomerModel = () => {
    if (!customerScopeAccepted) {
      setCustomerRunError(
        "Check the scope box before showing the estimate.",
      );
      return;
    }

    if (!customerDisclaimerAccepted) {
      setCustomerRunError(
        "Accept the safety notice before showing the estimate.",
      );
      return;
    }

    if (!readinessState.canRun || heartRateBpm === null) {
      setCustomerRunError(readinessState.error);
      return;
    }

    try {
      const prediction = predictPooledEmpiricalDisposition(
        toPooledEmpiricalPredictionInputs(inputs, age, heartRateBpm),
      );
      setCustomerRunError(null);
      setCustomerRun({
        key: currentRunKey,
        age,
        heartRateBpm,
        inputs,
        prediction,
        sampleCount,
      });
    } catch (error) {
      setCustomerRunError(
        error instanceof Error ? error.message : "Prediction failed.",
      );
    }
  };
  const simulationState = useSimulationWorker(
    activeRun?.inputs ?? inputs,
    page === "results" && activeRun !== null,
    activeRun?.age ?? age,
    activeRun?.heartRateBpm ?? heartRateBpm,
    activeRun?.sampleCount ?? sampleCount,
  );
  const customerSimulationState = useSimulationWorker(
    activeCustomerRun?.inputs ?? inputs,
    page === "customer" && activeCustomerRun !== null,
    activeCustomerRun?.age ?? age,
    activeCustomerRun?.heartRateBpm ?? heartRateBpm,
    activeCustomerRun?.sampleCount ?? sampleCount,
  );
  const showCompareDock = page === "results" && savedRuns.length > 0;

  const saveActiveRun = () => {
    if (activeRun === null) {
      return;
    }

    const nextRunNumber = savedRuns.length + 1;
    const id = `run-${Date.now()}-${nextRunNumber}`;
    const name = runNameDraft.trim() || `Run ${nextRunNumber}`;
    const simulation = simulationState.result;
    const savedRun: SavedModelRun = {
      ...activeRun,
      id,
      name,
      createdAt: new Date().toISOString(),
      simulationSummary: simulation
        ? {
            median: simulation.median,
            p025: simulation.p025,
            p975: simulation.p975,
            sampleCount: simulation.sampleCount,
            seed: simulation.seed,
          }
        : null,
    };

    setSavedRuns((current) => [...current, savedRun]);
    setSelectedSavedRunIds((current) => [...current, id]);
    setRunNameDraft(`Run ${nextRunNumber + 1}`);
    setCompareDockCollapsed(false);
  };

  const handlePrototypeRibbonClick = () => {
    if (prototypeResetRef.current !== null) {
      window.clearTimeout(prototypeResetRef.current);
    }

    setPrototypeClicks((clicks) => {
      const nextClicks = clicks + 1;
      if (nextClicks >= 7) {
        setArcadeOpen(true);
        return 0;
      }
      return nextClicks;
    });
    prototypeResetRef.current = window.setTimeout(
      () => setPrototypeClicks(0),
      2200,
    );
  };

  useEffect(() => {
    return () => {
      if (prototypeResetRef.current !== null) {
        window.clearTimeout(prototypeResetRef.current);
      }
    };
  }, []);

  return (
    <TooltipProvider>
      <div
        className={cn(
          "min-h-svh bg-background text-foreground",
          showCompareDock && "pb-44 max-[760px]:pb-6",
        )}
      >
        <PrototypeRibbon onClick={handlePrototypeRibbonClick} />
        <AppHeader page={page} setPage={setPage} />
        {page === "results" && activeRun !== null ? (
          <ResultsInputBanner run={activeRun} ready={readinessState.canRun} />
        ) : null}
        <main className="mx-auto flex max-w-7xl flex-col gap-10 px-5 py-8 max-[720px]:px-3">
          {page === "landing" && <LandingPage />}
          {page === "customer" && (
            <CustomerPreviewPage
              age={age}
              setAge={setAge}
              heartRateText={heartRateText}
              setHeartRateText={setHeartRateText}
              heartRateBpm={heartRateBpm}
              painSeverity={painSeverity}
              setPainSeverity={setPainSeverity}
              fever={fever}
              setFever={setFever}
              vomiting={vomiting}
              setVomiting={setVomiting}
              sampleCount={sampleCount}
              setSampleCount={setSampleCount}
              readinessState={readinessState}
              customerRunError={customerRunError}
              customerScopeAccepted={customerScopeAccepted}
              setCustomerScopeAccepted={setCustomerScopeAccepted}
              customerDisclaimerAccepted={customerDisclaimerAccepted}
              setCustomerDisclaimerAccepted={setCustomerDisclaimerAccepted}
              runCustomerModel={runCustomerModel}
              run={activeCustomerRun}
              simulationState={customerSimulationState}
            />
          )}
          {page === "explorer" && <ModelExplorerPage setPage={setPage} />}
          {page === "use" && (
            <UseModelPage
              age={age}
              setAge={setAge}
              heartRateText={heartRateText}
              setHeartRateText={setHeartRateText}
              heartRateBpm={heartRateBpm}
              painSeverity={painSeverity}
              setPainSeverity={setPainSeverity}
              fever={fever}
              setFever={setFever}
              vomiting={vomiting}
              setVomiting={setVomiting}
              sampleCount={sampleCount}
              setSampleCount={setSampleCount}
              readinessState={readinessState}
              runError={runError}
              runModel={runModel}
            />
          )}
          {page === "results" && (
            <ResultsPage
              run={activeRun}
              simulationState={simulationState}
              setPage={setPage}
              runName={runNameDraft}
              setRunName={setRunNameDraft}
              savedRunCount={savedRuns.length}
              saveRun={saveActiveRun}
            />
          )}
          {page === "docs" && <TechnicalDocsPage setPage={setPage} />}
        </main>
        {arcadeOpen ? (
          <AmbulanceArcade
            bestScore={arcadeBestScore}
            setBestScore={setArcadeBestScore}
            onClose={() => setArcadeOpen(false)}
          />
        ) : null}
        {showCompareDock ? (
          <CompareDock
            savedRuns={savedRuns}
            selectedRunIds={selectedSavedRunIds}
            setSelectedRunIds={setSelectedSavedRunIds}
            collapsed={compareDockCollapsed}
            setCollapsed={setCompareDockCollapsed}
          />
        ) : null}
      </div>
    </TooltipProvider>
  );
}

function ResultsInputBanner({
  run,
  ready,
}: {
  run: ModelRun;
  ready: boolean;
}) {
  return (
    <div className="border-b border-border bg-card px-5 max-[720px]:px-3">
      <div className="mx-auto flex max-w-7xl justify-end max-[760px]:justify-start">
        <div className="flex w-fit max-w-full flex-wrap items-center justify-end gap-2 border-x border-border bg-muted/30 px-3 py-2 text-xs max-[760px]:w-full max-[760px]:justify-start">
          <span className="font-medium text-foreground">Current inputs</span>
          <BannerDatum label="Age" value={String(run.age)} />
          <BannerDatum label="Band" value={valueLabels[run.inputs.ageBand]} />
          <BannerDatum label="Pain" value={valueLabels[run.inputs.painSeverity]} />
          <BannerDatum label="Fever" value={valueLabels[run.inputs.fever]} />
          <BannerDatum label="Vomiting" value={valueLabels[run.inputs.vomiting]} />
          <BannerDatum label="HR" value={`${run.heartRateBpm} bpm`} />
          <Badge variant={ready ? "default" : "secondary"}>
            {ready ? "Model-ready" : "Input changed"}
          </Badge>
        </div>
      </div>
    </div>
  );
}

function BannerDatum({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-md border border-border bg-background px-2 py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </span>
  );
}

function CompareDock({
  savedRuns,
  selectedRunIds,
  setSelectedRunIds,
  collapsed,
  setCollapsed,
}: {
  savedRuns: SavedModelRun[];
  selectedRunIds: string[];
  setSelectedRunIds: Dispatch<SetStateAction<string[]>>;
  collapsed: boolean;
  setCollapsed: Dispatch<SetStateAction<boolean>>;
}) {
  const selectedRuns = savedRuns.filter((run) => selectedRunIds.includes(run.id));
  const referenceRun = selectedRuns[0];

  const toggleRun = (runId: string, checked: boolean) => {
    setSelectedRunIds((current) => {
      if (checked) {
        return current.includes(runId) ? current : [...current, runId];
      }

      return current.filter((id) => id !== runId);
    });
  };

  if (collapsed) {
    return (
      <div className="fixed bottom-5 left-5 z-40 w-[min(320px,calc(100vw-2rem))] rounded-lg border border-border bg-card p-2 shadow-lg max-[760px]:static max-[760px]:mx-3 max-[760px]:mb-3 max-[760px]:w-auto">
        <Button
          type="button"
          variant="outline"
          className="w-full justify-between"
          aria-expanded={false}
          onClick={() => setCollapsed(false)}
        >
          Compare runs
          <Badge variant="secondary">{savedRuns.length}</Badge>
        </Button>
      </div>
    );
  }

  return (
    <aside
      aria-label="Saved model run comparison"
      className="fixed bottom-5 left-5 z-40 flex w-[min(520px,calc(100vw-2rem))] max-h-[min(78svh,720px)] flex-col gap-3 rounded-lg border border-border bg-card p-3 shadow-lg max-[760px]:static max-[760px]:mx-3 max-[760px]:mb-3 max-[760px]:max-h-none max-[760px]:w-auto"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold leading-tight">Compare saved runs</p>
          <p className="text-xs text-muted-foreground">
            Choose two or more saved runs.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-expanded={true}
          onClick={() => setCollapsed(true)}
        >
          Collapse
        </Button>
      </div>

      <div className="flex max-h-36 flex-col gap-2 overflow-y-auto pr-1">
        {savedRuns.map((run) => {
          const checkboxId = `compare-${run.id}`;
          const checked = selectedRunIds.includes(run.id);

          return (
            <label
              key={run.id}
              htmlFor={checkboxId}
              className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
            >
              <Checkbox
                id={checkboxId}
                checked={checked}
                onCheckedChange={(nextChecked) =>
                  toggleRun(run.id, nextChecked === true)
                }
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{run.name}</span>
                <span className="block text-xs text-muted-foreground">
                  {formatSavedRunTime(run.createdAt)}
                </span>
              </span>
              <Badge variant="outline">
                {formatPercent(run.prediction.probabilityAdmit)}
              </Badge>
            </label>
          );
        })}
      </div>

      <Separator />

      {selectedRuns.length >= 2 && referenceRun ? (
        <div className="flex max-h-72 flex-col gap-2 overflow-y-auto pr-1">
          {selectedRuns.map((run) => (
            <div
              key={run.id}
              className="rounded-lg border border-border bg-background p-3 text-xs"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="min-w-0 truncate font-medium">{run.name}</p>
                <span className="shrink-0 text-muted-foreground">
                  {formatSavedRunTime(run.createdAt)}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 max-[480px]:grid-cols-1">
                <CompareMetric
                  label="P(admit)"
                  value={formatPercent(run.prediction.probabilityAdmit)}
                />
                <CompareMetric
                  label="P(treat_and_release)"
                  value={formatPercent(
                    run.prediction.probabilityTreatAndRelease,
                  )}
                />
                <CompareMetric
                  label="95% interval"
                  value={formatSavedInterval(run.simulationSummary)}
                />
                <CompareMetric
                  label="Simulations"
                  value={run.sampleCount.toLocaleString()}
                />
              </div>
              <p className="mt-2 text-muted-foreground">
                <span className="font-medium text-foreground">
                  Key differences:
                </span>{" "}
                {summarizeRunDifferences(run, referenceRun)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="rounded-lg border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
          Save runs from Results. Then choose at least two here to compare
          probabilities, ranges, and input changes.
        </p>
      )}
    </aside>
  );
}

function CompareMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/30 px-2 py-1.5">
      <p className="text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-medium text-foreground">{value}</p>
    </div>
  );
}

function formatSavedRunTime(createdAt: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(createdAt));
}

function formatSavedInterval(summary: SimulationSummary | null): string {
  if (!summary) {
    return "Pending at save";
  }

  return `${formatPercent(summary.p025)} - ${formatPercent(summary.p975)}`;
}

function summarizeRunDifferences(
  run: SavedModelRun,
  reference: SavedModelRun,
): string {
  if (run.id === reference.id) {
    return "Reference run";
  }

  const differences: string[] = [];
  if (run.age !== reference.age) {
    differences.push(`Age: ${reference.age} -> ${run.age}`);
  }

  runDifferenceFields.forEach((field) => {
    const referenceValue = reference.inputs[field.id];
    const runValue = run.inputs[field.id];
    if (referenceValue !== runValue) {
      differences.push(
        `${field.label}: ${formatRunInputValue(referenceValue)} -> ${formatRunInputValue(
          runValue,
        )}`,
      );
    }
  });

  if (run.heartRateBpm !== reference.heartRateBpm) {
    differences.push(
      `HR: ${reference.heartRateBpm} bpm -> ${run.heartRateBpm} bpm`,
    );
  }

  if (run.sampleCount !== reference.sampleCount) {
    differences.push(
      `Simulations: ${reference.sampleCount.toLocaleString()} -> ${run.sampleCount.toLocaleString()}`,
    );
  }

  return differences.length > 0 ? differences.join("; ") : "No key differences";
}

function formatRunInputValue(value: ModelInputs[keyof ModelInputs]): string {
  return valueLabels[String(value)] ?? String(value);
}

function PrototypeRibbon({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label="Prototype ribbon"
      onClick={onClick}
      className="fixed left-0 top-0 z-50 rounded-br-lg bg-primary px-3 py-1.5 text-xs font-semibold uppercase tracking-normal text-primary-foreground shadow-sm outline-none transition hover:bg-primary/90 focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      PROTOTYPE
    </button>
  );
}

function AmbulanceArcade({
  bestScore,
  setBestScore,
  onClose,
}: {
  bestScore: number;
  setBestScore: Dispatch<SetStateAction<number>>;
  onClose: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const runtimeRef = useRef<ArcadeRuntime>(createArcadeRuntime(bestScore));
  const bestScoreRef = useRef(bestScore);
  const audioMutedRef = useRef(true);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playSoundRef = useRef<(sound: ArcadeSound) => void>(() => undefined);
  const [audioMuted, setAudioMuted] = useState(true);
  const [hud, setHud] = useState<ArcadeHud>(() =>
    arcadeHudFromRuntime(createArcadeRuntime(bestScore)),
  );

  useEffect(() => {
    bestScoreRef.current = bestScore;
    runtimeRef.current.bestScore = bestScore;
    runtimeRef.current.breakdown.bestScore = bestScore;
    setHud(arcadeHudFromRuntime(runtimeRef.current));
  }, [bestScore]);

  useEffect(() => {
    audioMutedRef.current = audioMuted;
    runtimeRef.current.audioMuted = audioMuted;
    setHud(arcadeHudFromRuntime(runtimeRef.current));
  }, [audioMuted]);

  const playArcadeSound = (sound: ArcadeSound) => {
    if (audioMutedRef.current) {
      return;
    }

    const AudioContextConstructor =
      window.AudioContext ||
      (
        window as Window &
          typeof globalThis & { webkitAudioContext?: typeof AudioContext }
      ).webkitAudioContext;
    if (!AudioContextConstructor) {
      return;
    }

    const audioContext =
      audioContextRef.current ?? new AudioContextConstructor();
    audioContextRef.current = audioContext;
    void audioContext.resume();

    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    const now = audioContext.currentTime;
    const settings: Record<
      ArcadeSound,
      { frequency: number; endFrequency: number; duration: number; gain: number }
    > = {
      start: { frequency: 360, endFrequency: 520, duration: 0.09, gain: 0.05 },
      pickup: { frequency: 540, endFrequency: 820, duration: 0.13, gain: 0.055 },
      collision: {
        frequency: 150,
        endFrequency: 82,
        duration: 0.16,
        gain: 0.065,
      },
      "near-miss": {
        frequency: 420,
        endFrequency: 470,
        duration: 0.07,
        gain: 0.035,
      },
    };
    const tone = settings[sound];

    oscillator.type = sound === "collision" ? "sawtooth" : "square";
    oscillator.frequency.setValueAtTime(tone.frequency, now);
    oscillator.frequency.exponentialRampToValueAtTime(
      Math.max(1, tone.endFrequency),
      now + tone.duration,
    );
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(tone.gain, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + tone.duration);
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start(now);
    oscillator.stop(now + tone.duration + 0.02);
  };

  useEffect(() => {
    playSoundRef.current = playArcadeSound;
  });

  const publishRuntimeHud = () => {
    const runtime = runtimeRef.current;
    if (runtime.bestScore > bestScoreRef.current) {
      bestScoreRef.current = runtime.bestScore;
      setBestScore(runtime.bestScore);
    }
    setHud(arcadeHudFromRuntime(runtime));
  };

  const startGame = () => {
    startArcadeRuntime(runtimeRef.current, bestScoreRef.current);
    runtimeRef.current.audioMuted = audioMutedRef.current;
    playSoundRef.current("start");
    publishRuntimeHud();
    const context = canvasRef.current?.getContext("2d");
    if (context) {
      drawArcadeScene(context, runtimeRef.current);
    }
  };

  const togglePause = () => {
    const runtime = runtimeRef.current;
    if (runtime.mode === "playing") {
      pauseArcadeRuntime(runtime);
    } else if (runtime.mode === "paused") {
      resumeArcadeRuntime(runtime);
    }
    publishRuntimeHud();
    const context = canvasRef.current?.getContext("2d");
    if (context) {
      drawArcadeScene(context, runtime);
    }
  };

  const toggleAudioMuted = () => {
    if (audioMutedRef.current) {
      const AudioContextConstructor =
        window.AudioContext ||
        (
          window as Window &
            typeof globalThis & { webkitAudioContext?: typeof AudioContext }
        ).webkitAudioContext;
      if (AudioContextConstructor) {
        const audioContext =
          audioContextRef.current ?? new AudioContextConstructor();
        audioContextRef.current = audioContext;
        void audioContext.resume();
      }
      audioMutedRef.current = false;
      runtimeRef.current.audioMuted = false;
      setAudioMuted(false);
      return;
    }

    audioMutedRef.current = true;
    runtimeRef.current.audioMuted = true;
    setAudioMuted(true);
  };

  const setDirection = (direction: "left" | "right", pressed: boolean) => {
    runtimeRef.current.keys[direction] = pressed;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const originalBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    canvas.width = arcadeWidth;
    canvas.height = arcadeHeight;
    const runtime = runtimeRef.current;
    runtime.bestScore = bestScoreRef.current;
    runtime.audioMuted = audioMutedRef.current;
    const publishHud = () => {
      if (runtime.bestScore > bestScoreRef.current) {
        bestScoreRef.current = runtime.bestScore;
        setBestScore(runtime.bestScore);
      }
      setHud(arcadeHudFromRuntime(runtime));
    };
    const render = () => drawArcadeScene(context, runtime);
    const flushSoundEvents = () => {
      runtime.soundEvents.splice(0).forEach((sound) => {
        playSoundRef.current(sound);
      });
    };
    const stepAndRender = (milliseconds: number) => {
      const steps = Math.max(1, Math.round(milliseconds / (1000 / 60)));
      for (let index = 0; index < steps; index += 1) {
        stepArcadeRuntime(runtime, 1 / 60);
      }
      flushSoundEvents();
      render();
      publishHud();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
        event.preventDefault();
        runtime.keys.left = true;
      } else if (
        event.key === "ArrowRight" ||
        event.key.toLowerCase() === "d"
      ) {
        event.preventDefault();
        runtime.keys.right = true;
      } else if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        if (runtime.mode === "ready" || runtime.mode === "over") {
          startArcadeRuntime(runtime, bestScoreRef.current);
          runtime.audioMuted = audioMutedRef.current;
          playSoundRef.current("start");
          publishHud();
        } else if (runtime.mode === "paused") {
          resumeArcadeRuntime(runtime);
          publishHud();
        }
      } else if (event.key.toLowerCase() === "p") {
        event.preventDefault();
        if (runtime.mode === "playing") {
          pauseArcadeRuntime(runtime);
        } else if (runtime.mode === "paused") {
          resumeArcadeRuntime(runtime);
        }
        publishHud();
      } else if (event.key === "Escape") {
        event.preventDefault();
        if (runtime.mode === "playing") {
          pauseArcadeRuntime(runtime);
          publishHud();
        }
      }
    };
    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
        runtime.keys.left = false;
      } else if (
        event.key === "ArrowRight" ||
        event.key.toLowerCase() === "d"
      ) {
        runtime.keys.right = false;
      }
    };
    const pauseForInactiveTab = () => {
      if (runtime.mode === "playing") {
        pauseArcadeRuntime(runtime);
        render();
        publishHud();
      }
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        pauseForInactiveTab();
      }
    };
    const reducedMotionQuery = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    );
    const updateReducedMotion = () => {
      runtime.reducedMotion = reducedMotionQuery.matches;
    };

    const arcadeWindow = window as Window &
      typeof globalThis & {
        advanceTime?: (milliseconds: number) => void;
        render_game_to_text?: () => string;
      };
    arcadeWindow.advanceTime = stepAndRender;
    arcadeWindow.render_game_to_text = () => renderArcadeToText(runtime);
    updateReducedMotion();

    let animationFrame = 0;
    let lastTimestamp = performance.now();
    const loop = (timestamp: number) => {
      const elapsedSeconds = Math.min(0.05, (timestamp - lastTimestamp) / 1000);
      lastTimestamp = timestamp;
      stepArcadeRuntime(runtime, elapsedSeconds);
      flushSoundEvents();
      render();
      publishHud();
      animationFrame = window.requestAnimationFrame(loop);
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", pauseForInactiveTab);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    reducedMotionQuery.addEventListener("change", updateReducedMotion);
    render();
    animationFrame = window.requestAnimationFrame(loop);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", pauseForInactiveTab);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      reducedMotionQuery.removeEventListener("change", updateReducedMotion);
      document.body.style.overflow = originalBodyOverflow;
      delete arcadeWindow.advanceTime;
      delete arcadeWindow.render_game_to_text;
      void audioContextRef.current?.close();
    };
  }, [setBestScore]);

  const consoleButtonClass =
    "h-10 rounded-lg border-slate-600 bg-slate-900 px-3 text-sm text-slate-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.18),0_2px_0_rgba(15,23,42,0.95)] hover:bg-slate-800 hover:text-white focus-visible:ring-cyan-300/60 disabled:border-slate-800 disabled:bg-slate-950 disabled:text-slate-500 disabled:shadow-none";
  const steeringButtonClass =
    "h-11 min-w-24 rounded-xl border-slate-600 bg-slate-900 text-sm font-semibold text-slate-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.18),0_3px_0_rgba(15,23,42,0.95)] hover:bg-slate-800 hover:text-white focus-visible:ring-cyan-300/60 active:translate-y-0.5 active:shadow-[inset_0_1px_0_rgba(255,255,255,0.18),0_1px_0_rgba(15,23,42,0.95)]";

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/70 p-2 backdrop-blur-md">
      <div className="max-h-[97svh] w-full max-w-7xl overflow-auto rounded-[1.55rem] border border-slate-700 bg-slate-950 p-2 text-slate-100 shadow-[0_24px_76px_rgba(2,6,23,0.7)]">
        <div className="rounded-[1.25rem] border border-slate-800 bg-[radial-gradient(circle_at_20%_0%,rgba(37,99,235,0.22),transparent_32%),linear-gradient(145deg,#172033,#080d17_70%)] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.09)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[0.68rem] font-semibold uppercase tracking-normal text-cyan-300">
                An E-Dispo arcade easter egg
              </p>
              <h2 className="text-xl font-semibold text-white">
                E-Dispatch
              </h2>
              <p className="mt-0.5 max-w-2xl text-xs text-slate-300">
                Retro ambulance runner. Arcade-only: no model inputs, outputs,
                or estimates are used.
              </p>
            </div>
            <div className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-950/65 px-2.5 py-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
              <div className="size-1.5 rounded-full bg-cyan-300 shadow-[0_0_10px_rgba(103,232,249,0.9)]" />
              <div className="size-1.5 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.75)]" />
              <div className="size-1.5 rounded-full bg-emerald-300 shadow-[0_0_10px_rgba(110,231,183,0.8)]" />
            </div>
          </div>

          <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_172px]">
            <div className="rounded-[1.05rem] border border-slate-700 bg-slate-900/80 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_10px_28px_rgba(2,6,23,0.45)]">
              <div className="mb-2 flex items-center justify-between gap-2">
                <DashboardVent />
                <p className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-2.5 py-0.5 text-[0.68rem] font-semibold uppercase tracking-normal text-cyan-200">
                  E-Dispatch AUX
                </p>
                <DashboardVent />
              </div>
              <div className="rounded-xl border border-slate-500/50 bg-black p-1.5 shadow-[0_0_20px_rgba(37,99,235,0.28),inset_0_0_34px_rgba(59,130,246,0.14)]">
                <canvas
                  ref={canvasRef}
                  id="ambulance-arcade-canvas"
                  className="mx-auto aspect-[3/2] w-full rounded-lg border border-slate-800 bg-muted touch-none"
                  style={{ maxWidth: "min(100%, calc(58svh * 1.5), 960px)" }}
                  aria-label="Top-down E-Dispatch arcade canvas"
                />
              </div>
            </div>

            <div className="grid content-start gap-2 rounded-[1.05rem] border border-slate-700 bg-slate-950/65 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] max-[1024px]:grid-cols-2">
              <Button
                type="button"
                variant="outline"
                className={consoleButtonClass}
                onClick={startGame}
              >
                <RotateCcw data-icon="inline-start" />
                {hud.mode === "ready" ? "Start" : "Restart"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className={consoleButtonClass}
                onClick={togglePause}
                disabled={hud.mode === "ready" || hud.mode === "over"}
              >
                {hud.mode === "paused" ? (
                  <Play data-icon="inline-start" />
                ) : (
                  <Pause data-icon="inline-start" />
                )}
                {hud.mode === "paused" ? "Resume" : "Pause"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className={consoleButtonClass}
                onClick={toggleAudioMuted}
              >
                {audioMuted ? (
                  <VolumeX data-icon="inline-start" />
                ) : (
                  <Volume2 data-icon="inline-start" />
                )}
                {audioMuted ? "Unmute" : "Mute"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className={consoleButtonClass}
                onClick={onClose}
              >
                <X data-icon="inline-start" />
                Close
              </Button>
              {hud.mode === "over" ? (
                <TripReceiptDisplay compact breakdown={hud.breakdown} />
              ) : null}
            </div>
          </div>

          <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_236px]">
            <DashboardInstrumentCluster
              combo={hud.combo}
              score={hud.score}
              timeLeft={hud.timeLeft}
            />
            <div className="grid grid-cols-2 content-center gap-2 rounded-[1.05rem] border border-slate-700 bg-slate-950/65 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
              <Button
                type="button"
                variant="outline"
                aria-label="Steer left"
                className={steeringButtonClass}
                onPointerDown={() => setDirection("left", true)}
                onPointerUp={() => setDirection("left", false)}
                onPointerLeave={() => setDirection("left", false)}
                onPointerCancel={() => setDirection("left", false)}
              >
                Left
              </Button>
              <Button
                type="button"
                variant="outline"
                aria-label="Steer right"
                className={steeringButtonClass}
                onPointerDown={() => setDirection("right", true)}
                onPointerUp={() => setDirection("right", false)}
                onPointerLeave={() => setDirection("right", false)}
                onPointerCancel={() => setDirection("right", false)}
              >
                Right
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardVent() {
  return (
    <div
      aria-hidden="true"
      className="flex h-6 w-24 items-center justify-center gap-1 rounded-lg border border-slate-700 bg-slate-950/75 px-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] max-[560px]:hidden"
    >
      {[0, 1, 2, 3, 4].map((slot) => (
        <span key={slot} className="h-4 w-1 rounded-full bg-slate-600" />
      ))}
    </div>
  );
}

function DashboardInstrumentCluster({
  combo,
  score,
  timeLeft,
}: {
  combo: number;
  score: number;
  timeLeft: number;
}) {
  const fuelPercent = clampNumber(timeLeft / arcadeTuning.timeLimit, 0, 1);

  return (
    <div className="grid gap-2 rounded-[1.05rem] border border-slate-700 bg-[linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.96))] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] md:grid-cols-[1.05fr_1.35fr_0.9fr]">
      <FuelGauge percent={fuelPercent} value={`${timeLeft.toFixed(1)}s`} />
      <OdometerGauge value={score} />
      <GearGauge value={Math.max(1, combo)} />
    </div>
  );
}

function FuelGauge({ percent, value }: { percent: number; value: string }) {
  const angle = Math.PI + percent * Math.PI;
  const needleX = 80 + Math.cos(angle) * 54;
  const needleY = 88 + Math.sin(angle) * 54;

  return (
    <div
      aria-label={`Fuel time left ${value}`}
      className="rounded-xl border border-slate-700 bg-slate-950 p-2 shadow-[inset_0_0_18px_rgba(14,165,233,0.12)]"
    >
      <div className="flex items-center justify-between text-[0.68rem] font-semibold uppercase tracking-normal text-cyan-200">
        <span>Fuel</span>
        <span>Time</span>
      </div>
      <svg
        aria-hidden="true"
        className="mt-0.5 h-20 w-full text-cyan-300"
        viewBox="0 0 160 112"
      >
        <path
          d="M26 88 A54 54 0 0 1 134 88"
          fill="none"
          stroke="rgba(148, 163, 184, 0.38)"
          strokeLinecap="round"
          strokeWidth="10"
        />
        <path
          d="M26 88 A54 54 0 0 1 134 88"
          fill="none"
          pathLength="100"
          stroke="currentColor"
          strokeDasharray={`${Math.round(percent * 100)} 100`}
          strokeLinecap="round"
          strokeWidth="6"
        />
        {[0, 1, 2, 3, 4].map((tick) => {
          const tickAngle = Math.PI + (tick / 4) * Math.PI;
          const outerX = 80 + Math.cos(tickAngle) * 62;
          const outerY = 88 + Math.sin(tickAngle) * 62;
          const innerX = 80 + Math.cos(tickAngle) * 48;
          const innerY = 88 + Math.sin(tickAngle) * 48;
          return (
            <line
              key={tick}
              stroke="rgba(226,232,240,0.72)"
              strokeLinecap="round"
              strokeWidth="2"
              x1={outerX}
              x2={innerX}
              y1={outerY}
              y2={innerY}
            />
          );
        })}
        <line
          stroke="#f87171"
          strokeLinecap="round"
          strokeWidth="4"
          x1="80"
          x2={needleX}
          y1="88"
          y2={needleY}
        />
        <circle cx="80" cy="88" fill="#e2e8f0" r="5" />
      </svg>
      <p className="text-center text-xl font-bold tabular-nums text-white">
        {value}
      </p>
    </div>
  );
}

function OdometerGauge({ value }: { value: number }) {
  return (
    <div
      aria-label={`Odometer score ${value}`}
      className="rounded-xl border border-slate-700 bg-slate-950 p-2 shadow-[inset_0_0_20px_rgba(16,185,129,0.1)]"
    >
      <div className="flex items-center justify-between text-[0.68rem] font-semibold uppercase tracking-normal text-cyan-200">
        <span>Odometer</span>
        <span>Score</span>
      </div>
      <div className="mt-3 rounded-lg border border-cyan-300/20 bg-black px-2 py-3 shadow-[inset_0_0_16px_rgba(14,165,233,0.18)]">
        <p className="text-center font-mono text-3xl font-bold leading-none tracking-normal text-cyan-100 tabular-nums max-[560px]:text-2xl">
          {String(value).padStart(5, "0")}
        </p>
      </div>
      <p className="mt-2 text-center text-[0.68rem] font-semibold uppercase tracking-normal text-slate-400">
        Trip points
      </p>
    </div>
  );
}

function GearGauge({ value }: { value: number }) {
  const gear = Math.min(arcadeTuning.scoring.comboMax, value);

  return (
    <div
      aria-label={`Combo gear ${gear}`}
      className="rounded-xl border border-slate-700 bg-slate-950 p-2 shadow-[inset_0_0_18px_rgba(37,99,235,0.12)]"
    >
      <div className="flex items-center justify-between text-[0.68rem] font-semibold uppercase tracking-normal text-cyan-200">
        <span>Gear</span>
        <span>Combo</span>
      </div>
      <div className="mt-3 grid grid-cols-[1fr_auto] items-center gap-3">
        <div className="grid gap-1">
          {[1, 2, 3, 4, 5].map((step) => (
            <div
              key={step}
              className={cn(
                "h-2 rounded-full bg-slate-700",
                step <= gear &&
                  "bg-cyan-300 shadow-[0_0_10px_rgba(103,232,249,0.72)]",
              )}
            />
          ))}
        </div>
        <div className="flex size-16 items-center justify-center rounded-full border border-cyan-300/35 bg-black shadow-[inset_0_0_16px_rgba(14,165,233,0.18)]">
          <p className="font-mono text-2xl font-bold text-white tabular-nums">
            x{gear}
          </p>
        </div>
      </div>
      <p className="mt-2 text-center text-[0.68rem] font-semibold uppercase tracking-normal text-slate-400">
        Shift streak
      </p>
    </div>
  );
}

function TripReceiptDisplay({
  breakdown,
  compact = false,
}: {
  breakdown: ArcadeScoreBreakdown;
  compact?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-cyan-300/25 bg-[#07120f] p-2 font-mono text-cyan-100 shadow-[inset_0_0_18px_rgba(45,212,191,0.16)]",
        compact ? "col-span-full" : "mt-4",
      )}
    >
      <p className="text-[0.68rem] font-bold uppercase tracking-normal text-cyan-300">
        Trip receipt
      </p>
      <div
        className={cn(
          "mt-2 grid gap-1.5 text-xs",
          compact ? "grid-cols-2" : "sm:grid-cols-6",
        )}
      >
        <TripReceiptItem
          label="Distance"
          value={String(breakdown.distance)}
        />
        <TripReceiptItem
          label="Gates"
          value={String(breakdown.gatesCollected)}
        />
        <TripReceiptItem
          label={compact ? "Near" : "Near misses"}
          value={String(breakdown.nearMisses)}
        />
        <TripReceiptItem
          label={compact ? "Combo" : "Combo bonus"}
          value={String(breakdown.comboBonus)}
        />
        <TripReceiptItem label="Final" value={String(breakdown.finalScore)} />
        <TripReceiptItem label="Best" value={String(breakdown.bestScore)} />
      </div>
    </div>
  );
}

function TripReceiptItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0 rounded-md border border-cyan-300/10 bg-cyan-300/5 px-2 py-1.5">
      <p className="truncate text-[0.6rem] font-semibold uppercase tracking-normal text-cyan-300/80">
        {label}
      </p>
      <p className="text-base font-bold text-cyan-50 tabular-nums">{value}</p>
    </div>
  );
}

function AppHeader({
  page,
  setPage,
}: {
  page: Page;
  setPage: (page: Page) => void;
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 pl-24 pr-4 backdrop-blur max-[760px]:px-3 max-[760px]:pt-9">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 max-[760px]:min-h-0 max-[760px]:flex-col max-[760px]:items-stretch max-[760px]:gap-2 max-[760px]:pb-2">
        <button
          type="button"
          className="flex shrink-0 items-center gap-3 rounded-lg py-2 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50 max-[760px]:w-fit max-[760px]:py-0"
          onClick={() => setPage("landing")}
        >
          <span className="flex size-10 items-center justify-center rounded-lg bg-primary text-lg font-semibold text-primary-foreground">
            E
          </span>
          <span className="leading-tight">
            <span className="block whitespace-nowrap text-lg font-semibold">
              E-Dispo
            </span>
            <span className="block text-xs text-muted-foreground max-[430px]:hidden">
              Risk characterization
            </span>
          </span>
        </button>
        <nav
          className="flex min-w-0 flex-wrap justify-end gap-1.5 max-[760px]:grid max-[760px]:w-full max-[760px]:grid-cols-6 max-[760px]:gap-1 max-[360px]:grid-cols-3"
          aria-label="Primary navigation"
        >
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant={page === item.id ? "default" : "ghost"}
                    size="sm"
                    aria-label={item.label}
                    aria-current={page === item.id ? "page" : undefined}
                    title={item.tooltip}
                    className="max-[760px]:h-12 max-[760px]:w-full max-[760px]:min-w-0 max-[760px]:flex-col max-[760px]:gap-1 max-[760px]:px-1 max-[760px]:py-1.5 max-[760px]:text-[0.62rem] max-[760px]:leading-none max-[760px]:[&_svg]:size-4"
                    onClick={() => setPage(item.id)}
                  >
                    <Icon data-icon="inline-start" />
                    <span className="text-[0.8rem] max-[760px]:hidden">
                      {item.label}
                    </span>
                    <span className="hidden max-w-full overflow-hidden text-ellipsis text-[0.62rem] font-medium leading-none max-[760px]:block">
                      {item.mobileLabel}
                    </span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" sideOffset={6}>
                  {item.tooltip}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

function LandingPage() {
  return (
    <div className="flex flex-col gap-14">
      <section className="grid min-h-[calc(100svh-8rem)] grid-cols-[minmax(0,0.92fr)_minmax(360px,1.08fr)] items-center gap-12 max-[900px]:grid-cols-1">
        <div className="flex flex-col gap-8">
          <div className="flex flex-col gap-5">
            <h1 className="max-w-3xl text-7xl font-semibold leading-[0.98] tracking-normal max-[760px]:text-5xl">
              E-Dispo
            </h1>
            <p className="max-w-2xl text-2xl font-medium leading-9 text-foreground max-[760px]:text-xl">
              Answer the questions and hit run!
            </p>
            <p className="max-w-2xl text-lg leading-8 text-muted-foreground">
              This is a prototype. See disclaimer.
            </p>
          </div>
          <div className="grid max-w-xs grid-cols-1 gap-3">
            <LandingMetric label="Model" value="e-dispo-v4.0" />
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Visualize the uncertainty
              </p>
              <h2 className="mt-1 text-2xl font-semibold">
                What are the odds this guy gets admitted?
              </h2>
            </div>
            <Badge variant="outline">10,000 draws</Badge>
          </div>
          <DistributionPreview />
          <div className="mt-5 grid grid-cols-2 gap-3 max-[560px]:grid-cols-1">
            <ProductPanelItem
              icon={Gauge}
              label="Faster than the ambulance"
              value="Estimates the uncertainty quickly."
            />
            <ProductPanelItem
              icon={Activity}
              label="Clear picture of the unknowns"
              value="See the data and make a better decision."
            />
            <ProductPanelItem
              icon={Table2}
              label="Transparency and trust"
              value="Full honesty and clear explanations."
            />
            <ProductPanelItem
              icon={BookOpen}
              label="Technical Docs"
              value="Open, accessible, and complete."
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function ModelExplorerPage({ setPage }: { setPage: (page: Page) => void }) {
  const [activeNodeId, setActiveNodeId] = useState<ExplorerNodeId>("age");
  const activeNode =
    explorerNodes.find((node) => node.id === activeNodeId) ?? explorerNodes[0];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        icon={BarChart3}
        title="Model Explorer"
        description="Click through the model path. See what each piece does in plain language."
        action={
          <Button type="button" onClick={() => setPage("use")}>
            Use these inputs
            <ArrowRight data-icon="inline-end" />
          </Button>
        }
      />
      <section className="grid grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Conceptual model diagram</CardTitle>
            <CardDescription>
              Observed inputs feed the model. Then simulation shows the range
              around the endpoint estimate.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ModelDiagram
              activeNodeId={activeNodeId}
              setActiveNodeId={setActiveNodeId}
            />
          </CardContent>
        </Card>
        <EvidencePanel node={activeNode} />
      </section>
      <section className="grid grid-cols-3 gap-4 max-[900px]:grid-cols-1">
        <RulePanel title="Readable flow">
          The diagram starts with observed inputs, then moves through the
          logistic equation, simulation, and endpoint.
        </RulePanel>
        <RulePanel title="No raw table here">
          The Explorer avoids dense model tables. Technical Docs carry detailed
          review material.
        </RulePanel>
        <RulePanel title="Click any node">
          Each node opens a short plain-language explanation, then the model
          rule and technical detail when relevant.
        </RulePanel>
      </section>
    </div>
  );
}

function ModelDiagram({
  activeNodeId,
  setActiveNodeId,
}: {
  activeNodeId: ExplorerNodeId;
  setActiveNodeId: (nodeId: ExplorerNodeId) => void;
}) {
  const inputNodes = explorerNodes.filter((node) => node.group === "Input");
  const modelNodes = explorerNodes.filter((node) => node.group === "Model");
  const outputNodes = explorerNodes.filter((node) => node.group === "Output");

  return (
    <div className="grid grid-cols-[minmax(180px,1fr)_24px_minmax(170px,0.9fr)_24px_minmax(150px,0.75fr)] items-center gap-2 max-[900px]:grid-cols-1">
      <DiagramGroup title="Observed inputs">
        {inputNodes.map((node) => (
          <DiagramNode
            key={node.id}
            node={node}
            selected={activeNodeId === node.id}
            onClick={() => setActiveNodeId(node.id)}
          />
        ))}
      </DiagramGroup>
      <FlowArrow />
      <DiagramGroup title="Model processing">
        {modelNodes.map((node) => (
          <DiagramNode
            key={node.id}
            node={node}
            selected={activeNodeId === node.id}
            onClick={() => setActiveNodeId(node.id)}
          />
        ))}
      </DiagramGroup>
      <FlowArrow />
      <DiagramGroup title="Endpoint">
        {outputNodes.map((node) => (
          <DiagramNode
            key={node.id}
            node={node}
            selected={activeNodeId === node.id}
            onClick={() => setActiveNodeId(node.id)}
          />
        ))}
      </DiagramGroup>
    </div>
  );
}

function DiagramGroup({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col gap-3 rounded-lg border border-border bg-muted/30 p-3">
      <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {title}
      </p>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}

function DiagramNode({
  node,
  selected,
  onClick,
}: {
  node: ExplorerNode;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = node.icon;

  return (
    <button
      type="button"
      className={
        selected
          ? "flex w-full items-center gap-3 rounded-lg border border-primary bg-primary px-3 py-3 text-left text-primary-foreground shadow-sm outline-none transition focus-visible:ring-3 focus-visible:ring-ring/50"
          : "flex w-full items-center gap-3 rounded-lg border border-border bg-card px-3 py-3 text-left shadow-sm outline-none transition hover:border-primary/40 hover:bg-background focus-visible:ring-3 focus-visible:ring-ring/50"
      }
      onClick={onClick}
      aria-pressed={selected}
    >
      <span
        className={
          selected
            ? "flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/15"
            : "flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
        }
      >
        <Icon className="size-5" />
      </span>
      <span>
        <span className="block text-sm font-semibold">{node.label}</span>
        <span
          className={
            selected
              ? "block text-xs text-primary-foreground/80"
              : "block text-xs text-muted-foreground"
          }
        >
          {node.group}
        </span>
      </span>
    </button>
  );
}

function FlowArrow() {
  return (
    <div className="flex items-center justify-center text-primary max-[900px]:rotate-90">
      <ArrowRight className="size-5" />
    </div>
  );
}

function EvidencePanel({ node }: { node: ExplorerNode }) {
  const roleLabel =
    node.group === "Input"
      ? "What this input tells the model"
      : "What this piece does";

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          <span>{node.label}</span>
          <Badge variant="outline">{node.group}</Badge>
        </CardTitle>
        <CardDescription>
          Lay review panel for the selected model piece.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <EvidenceDetail label={roleLabel} value={node.role} />
        <EvidenceDetail
          label="How it usually moves the estimate"
          value={node.direction}
        />
        <EvidenceDetail
          label="How the app turns it into a model value"
          value={node.rule}
        />
        <EvidenceDetail label="Where this comes from" value={node.source} />
        <EvidenceDetail label="What to keep in mind" value={node.uncertainty} />
        <EvidenceDetail label="Why it belongs here" value={node.why} />
        {node.beta ? (
          <div className="rounded-lg bg-primary/10 p-3 text-sm font-medium text-primary">
            {node.beta}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function EvidenceDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm leading-6">{value}</p>
    </div>
  );
}

function ResultsPage({
  run,
  simulationState,
  setPage,
  runName,
  setRunName,
  savedRunCount,
  saveRun,
}: {
  run: ModelRun | null;
  simulationState: SimulationWorkerState;
  setPage: (page: Page) => void;
  runName: string;
  setRunName: Dispatch<SetStateAction<string>>;
  savedRunCount: number;
  saveRun: () => void;
}) {
  const simulation = simulationState.result;
  const pointEstimate = run?.prediction.probabilityAdmit ?? null;
  const complement = run?.prediction.probabilityTreatAndRelease ?? null;

  if (run === null) {
    return (
      <div className="flex flex-col gap-5">
        <PageHeader
          icon={Gauge}
          title="Results"
          description="See the range"
          action={
            <Button type="button" onClick={() => setPage("use")}>
              Use the Model
              <ArrowRight data-icon="inline-end" />
            </Button>
          }
        />
        <Alert>
          <Info />
          <AlertTitle>No stored run yet</AlertTitle>
          <AlertDescription>
            Complete the required fields on Use the Model. Then run the model
            to build the estimate range.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Gauge}
        title="Results"
        description="See the range"
        action={
          <Button
            type="button"
            variant="outline"
            onClick={() => setPage("use")}
          >
            Edit inputs
          </Button>
        }
      />
      <Alert>
        <Info />
        <AlertTitle>Educational and statistical use only</AlertTitle>
        <AlertDescription>
          This prototype is not medical advice, clinical decision support,
          diagnosis, triage, or discharge-safety guidance.
        </AlertDescription>
      </Alert>
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>Save model run</CardTitle>
          <CardDescription>
            This labels the run only. Do not enter a person name.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-3 max-[640px]:grid-cols-1">
            <div className="flex flex-col gap-2">
              <label htmlFor="run-name" className="text-sm font-medium">
                Run name
              </label>
              <input
                id="run-name"
                type="text"
                value={runName}
                onChange={(event) => setRunName(event.target.value)}
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              />
              <p className="text-sm text-muted-foreground">
                Use a neutral label like Run 1 or After HR change.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{savedRunCount} saved</Badge>
              <Button type="button" onClick={saveRun}>
                Save run
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="overflow-hidden rounded-lg">
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            <span>Estimate range</span>
            <Badge variant="outline">
              {run.sampleCount.toLocaleString()} simulations
            </Badge>
            <Badge variant="secondary">seed {modelMetadata.seed}</Badge>
          </CardTitle>
          <CardDescription>
            Each bar counts model runs for the saved input profile.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="min-w-0 overflow-hidden rounded-lg border border-border bg-background p-4">
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
                <div className="flex min-h-[460px] items-center justify-center rounded-lg border border-border bg-muted/40">
                  <div className="flex flex-col items-center gap-3 text-center">
                    <Activity className="size-8 animate-pulse text-primary" />
                    <p className="text-sm text-muted-foreground">
                      Building estimate range
                    </p>
                  </div>
                </div>
              ) : null}
              {simulationState.status === "complete" && simulation ? (
                <Suspense
                  fallback={
                    <div className="flex min-h-[460px] items-center justify-center text-sm text-muted-foreground">
                      Loading chart
                    </div>
                  }
                >
                  <HistogramChart data={simulation.histogram} height={430} />
                </Suspense>
              ) : null}
            </div>
            <div className="flex flex-col gap-4">
              <div className="rounded-lg border border-border bg-background p-4 text-sm leading-6 text-muted-foreground">
                <p className="font-medium text-foreground">How to read this</p>
                <p className="mt-2">
                  The main estimate is P(admit), the model probability for
                  same-hospital inpatient admission for this input profile.
                </p>
                <p className="mt-2">
                  The histogram shows possible estimates from the simulation.
                  A simulation means many repeated model runs with small changes
                  to the fitted model numbers.
                </p>
                <p className="mt-2">
                  The 80% interval is the middle 80% of simulated model
                  estimates. The 95% interval is wider, so it includes more
                  simulated estimates.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3">
                <ResultMetric
                  label="P(admit): main estimate"
                  value={
                    pointEstimate === null
                      ? "Pending"
                      : formatPercent(pointEstimate)
                  }
                />
                <ResultMetric
                  label="P(treat_and_release): 1 - P(admit)"
                  value={
                    complement === null ? "Pending" : formatPercent(complement)
                  }
                />
                <ResultMetric
                  label="80% interval"
                  value={
                    simulation
                      ? `${formatPercent(simulation.p10)} to ${formatPercent(simulation.p90)}`
                      : "Pending"
                  }
                />
                <ResultMetric
                  label="95% interval"
                  value={
                    simulation
                      ? `${formatPercent(simulation.p025)} to ${formatPercent(simulation.p975)}`
                      : "Pending"
                  }
                />
              </div>
              <div className="rounded-lg border border-border bg-background p-4">
                <p className="text-sm font-medium">Run metadata</p>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm max-[420px]:grid-cols-1">
                  <DefinitionRow
                    label="Simulations"
                    value={run.sampleCount.toLocaleString()}
                  />
                  <DefinitionRow
                    label="Seed"
                    value={String(modelMetadata.seed)}
                  />
                </div>
              </div>
              {simulation ? (
                <ResultMetric
                  label="Middle simulation estimate"
                  value={formatPercent(simulation.median)}
                />
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>
      <StoryView
        age={run.age}
        heartRateBpm={run.heartRateBpm}
        inputs={run.inputs}
        prediction={run.prediction}
        simulation={simulation}
      />
      <section className="grid grid-cols-[minmax(0,1fr)_360px] gap-5 max-[980px]:grid-cols-1">
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Active terms</CardTitle>
            <CardDescription>
              Technical weights used to make the main estimate.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Term</TableHead>
                    <TableHead>Mean contribution</TableHead>
                    <TableHead>SE contribution</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {run.prediction.activeTerms.map((term) => (
                    <TableRow key={term.key}>
                      <TableCell className="font-medium">
                        {term.label}
                      </TableCell>
                      <TableCell>{formatCoefficient(term.mean)}</TableCell>
                      <TableCell>{term.standardError.toFixed(3)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>Endpoint</CardTitle>
            <CardDescription>
              What the probability is estimating.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted-foreground">
            P(admit) estimates same-hospital inpatient admission after
            exclusions. Routine ED home disposition is the comparison endpoint.
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function StoryView({
  age,
  heartRateBpm,
  inputs,
  prediction,
  simulation,
}: {
  age: number;
  heartRateBpm: number | null;
  inputs: ModelInputs;
  prediction: PredictionResult | null;
  simulation: SimulationResult | null;
}) {
  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>Plain-English summary</CardTitle>
        <CardDescription>
          This summary repeats the chart in words.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-base leading-8">
        {prediction && simulation && heartRateBpm !== null ? (
          <>
            <p>
              For age {age}, {valueLabels[inputs.painSeverity].toLowerCase()}{" "}
              pain, fever {valueLabels[inputs.fever].toLowerCase()}, vomiting{" "}
              {valueLabels[inputs.vomiting].toLowerCase()}, and HR{" "}
              {heartRateBpm} bpm, the middle simulation estimate is{" "}
              <strong>{formatPercent(simulation.median)}</strong>.
            </p>
            <p>
              In the simulation, the middle 80% of model estimates ran from{" "}
              <strong>
                {formatPercent(simulation.p10)} to{" "}
                {formatPercent(simulation.p90)}
              </strong>
              . The wider 95% range ran from{" "}
              <strong>
                {formatPercent(simulation.p025)} to{" "}
                {formatPercent(simulation.p975)}
              </strong>
              .
            </p>
          </>
        ) : (
          <p className="text-muted-foreground">
            Complete the required observed fields to generate the story view.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function DistributionPreview() {
  const bars = [12, 18, 34, 58, 84, 112, 92, 74, 54, 36, 28, 18];

  return (
    <div className="mt-5 flex min-h-[300px] items-end gap-3 rounded-lg border border-border bg-background p-5">
      {bars.map((height, index) => (
        <div
          key={`${height}-${index}`}
          className="flex flex-1 items-end rounded-md bg-primary/10"
          style={{ height: `${height + 42}px` }}
        >
          <div
            className="w-full rounded-md bg-primary"
            style={{ height: `${height}px`, opacity: 0.32 + index * 0.035 }}
          />
        </div>
      ))}
    </div>
  );
}

function LandingMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-xl font-semibold">{value}</p>
    </div>
  );
}

function ProductPanelItem({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-background p-4">
      <Icon className="size-5 text-primary" />
      <p className="mt-3 text-sm font-medium">{label}</p>
      <p className="mt-1 text-sm text-muted-foreground">{value}</p>
    </div>
  );
}

function RulePanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center gap-2">
        <ShieldCheck className="size-5 text-primary" />
        <h2 className="font-semibold">{title}</h2>
      </div>
      <p className="mt-3 leading-7 text-muted-foreground">{children}</p>
    </div>
  );
}

const arcadeWidth = 720;
const arcadeHeight = 480;
const arcadeRoadLeft = 150;
const arcadeRoadWidth = 420;
const arcadeLaneWidth = arcadeRoadWidth / 3;
const arcadePlayerY = 368;
const arcadePlayerWidth = 46;
const arcadePlayerHeight = 74;
const arcadeTuning = {
  timeLimit: 36,
  speedRange: {
    min: 210,
    max: 392,
    distanceRamp: 0.014,
  },
  steeringSpeed: 348,
  spawnIntervals: {
    phase1: 1.1,
    phase2: 0.92,
    phase3: 0.76,
    jitter: 0.2,
    recovery: 1.35,
  },
  gateFrequency: {
    phase1: 0.18,
    phase2: 0.22,
    phase3: 0.18,
  },
  scoring: {
    distancePerPixel: 0.12,
    gate: 250,
    nearMiss: 90,
    comboStep: 45,
    comboMax: 5,
    comboWindow: 2.35,
  },
  phaseThresholds: {
    phase2Distance: 900,
    phase3Distance: 2100,
  },
  gateTimeBonus: 10,
  nearMissGap: 98,
} as const;
const arcadeBrand = {
  blue: "#2563eb",
  teal: "#0f766e",
  red: "#b42318",
  dark: "#0f172a",
  road: "#334155",
  lane: "#e2e8f0",
  grass: "#e7f6f4",
  grassAlt: "#d1ece7",
} as const;

function createArcadeRuntime(bestScore = 0): ArcadeRuntime {
  return {
    audioMuted: true,
    bestScore,
    breakdown: createArcadeBreakdown(bestScore),
    collisionFlash: 0,
    combo: 0,
    comboBonus: 0,
    comboTimer: 0,
    currentPattern: "none",
    distance: 0,
    entities: [],
    eventLog: ["Ready"],
    effects: [],
    elapsedTime: 0,
    gateTimer: 0,
    gatesCollected: 0,
    idCounter: 0,
    keys: { left: false, right: false },
    mode: "ready",
    nearMisses: 0,
    obstacleTimer: 0.68,
    phase: 1,
    playerX: arcadeRoadLeft + arcadeRoadWidth / 2,
    reducedMotion: false,
    roadOffset: 0,
    runFinalized: false,
    score: 0,
    seed: 20260430,
    shakeTime: 0,
    soundEvents: [],
    speed: arcadeTuning.speedRange.min,
    timeLeft: arcadeTuning.timeLimit,
  };
}

function startArcadeRuntime(runtime: ArcadeRuntime, bestScore = runtime.bestScore) {
  const audioMuted = runtime.audioMuted;
  const reducedMotion = runtime.reducedMotion;
  Object.assign(runtime, createArcadeRuntime(bestScore), {
    audioMuted,
    mode: "playing" as ArcadeMode,
    reducedMotion,
  });
  pushArcadeEvent(runtime, "Run started");
}

function pauseArcadeRuntime(runtime: ArcadeRuntime) {
  if (runtime.mode !== "playing") {
    return;
  }
  runtime.mode = "paused";
  runtime.keys.left = false;
  runtime.keys.right = false;
  pushArcadeEvent(runtime, "Paused");
}

function resumeArcadeRuntime(runtime: ArcadeRuntime) {
  if (runtime.mode !== "paused") {
    return;
  }
  runtime.mode = "playing";
  pushArcadeEvent(runtime, "Resumed");
}

function arcadeHudFromRuntime(runtime: ArcadeRuntime): ArcadeHud {
  return {
    audioMuted: runtime.audioMuted,
    bestScore: runtime.bestScore,
    breakdown: buildArcadeBreakdown(runtime),
    combo: runtime.combo,
    mode: runtime.mode,
    score: Math.floor(runtime.score),
    phase: runtime.phase,
    timeLeft: Math.max(0, runtime.timeLeft),
  };
}

function stepArcadeRuntime(runtime: ArcadeRuntime, elapsedSeconds: number) {
  updateArcadeVisualTimers(runtime, elapsedSeconds);

  if (runtime.mode !== "playing") {
    return;
  }

  runtime.elapsedTime += elapsedSeconds;
  runtime.timeLeft -= elapsedSeconds;
  if (runtime.timeLeft <= 0) {
    runtime.timeLeft = 0;
    finishArcadeRun(runtime, "Time up");
    return;
  }

  runtime.phase = getArcadePhase(runtime.distance);
  runtime.speed = Math.min(
    arcadeTuning.speedRange.max,
    arcadeTuning.speedRange.min +
      runtime.distance * arcadeTuning.speedRange.distanceRamp,
  );
  runtime.distance += runtime.speed * elapsedSeconds;
  runtime.score = calculateArcadeScore(runtime);
  runtime.roadOffset =
    (runtime.roadOffset + runtime.speed * elapsedSeconds) % 52;

  const steer = (runtime.keys.right ? 1 : 0) - (runtime.keys.left ? 1 : 0);
  runtime.playerX = clampNumber(
    runtime.playerX + steer * arcadeTuning.steeringSpeed * elapsedSeconds,
    arcadeRoadLeft + 34,
    arcadeRoadLeft + arcadeRoadWidth - 34,
  );

  runtime.obstacleTimer -= elapsedSeconds;
  if (runtime.obstacleTimer <= 0) {
    const pattern = selectArcadePattern(runtime);
    spawnArcadePattern(runtime, pattern);
    runtime.obstacleTimer = nextArcadePatternInterval(runtime, pattern);
  }

  runtime.entities.forEach((entity) => {
    entity.y += runtime.speed * elapsedSeconds;
  });

  const playerBox = {
    x: runtime.playerX - arcadePlayerWidth / 2,
    y: arcadePlayerY - arcadePlayerHeight / 2,
    width: arcadePlayerWidth,
    height: arcadePlayerHeight,
  };
  runtime.entities = runtime.entities.filter((entity) => {
    const entityBox = {
      x: entity.x - entity.width / 2,
      y: entity.y - entity.height / 2,
      width: entity.width,
      height: entity.height,
    };

    if (boxesOverlap(playerBox, entityBox)) {
      if (entity.type === "gate") {
        awardArcadeGate(runtime, entity);
        return false;
      }

      addArcadeEffect(runtime, "collision", entity.x, entity.y, "Crash", 0.5);
      runtime.collisionFlash = 0.28;
      runtime.shakeTime = runtime.reducedMotion ? 0 : 0.24;
      runtime.combo = 0;
      runtime.comboTimer = 0;
      runtime.soundEvents.push("collision");
      finishArcadeRun(runtime, "Collision");
      return true;
    }

    if (
      entity.type === "traffic" &&
      !entity.nearMissAwarded &&
      isArcadeNearMiss(playerBox, entityBox)
    ) {
      entity.nearMissAwarded = true;
      awardArcadeNearMiss(runtime, entity);
    }

    return entity.y < arcadeHeight + 90;
  });
  runtime.score = calculateArcadeScore(runtime);
}

function getArcadePhase(distance: number): ArcadePhase {
  if (distance >= arcadeTuning.phaseThresholds.phase3Distance) {
    return 3;
  }
  if (distance >= arcadeTuning.phaseThresholds.phase2Distance) {
    return 2;
  }
  return 1;
}

function selectArcadePattern(runtime: ArcadeRuntime): ArcadePatternId {
  const phase = runtime.phase;
  const gateChance =
    phase === 1
      ? arcadeTuning.gateFrequency.phase1
      : phase === 2
        ? arcadeTuning.gateFrequency.phase2
        : arcadeTuning.gateFrequency.phase3;
  if (runtime.distance > 420 && arcadeRandom(runtime) < gateChance) {
    return "gate-after-obstacle";
  }

  if (phase === 1) {
    return selectArcadePatternFrom(runtime, [
      "single-left",
      "single-center",
      "single-right",
      "recovery-gap",
    ]);
  }

  if (phase === 2) {
    return selectArcadePatternFrom(runtime, [
      "single-left",
      "single-center",
      "single-right",
      "two-lane-gap-left",
      "two-lane-gap-center",
      "two-lane-gap-right",
      "recovery-gap",
    ]);
  }

  return selectArcadePatternFrom(runtime, [
    "single-left",
    "single-center",
    "single-right",
    "two-lane-gap-left",
    "two-lane-gap-center",
    "two-lane-gap-right",
    "two-lane-gap-center",
    "recovery-gap",
  ]);
}

function selectArcadePatternFrom(
  runtime: ArcadeRuntime,
  patterns: ArcadePatternId[],
): ArcadePatternId {
  return patterns[Math.floor(arcadeRandom(runtime) * patterns.length)];
}

function nextArcadePatternInterval(
  runtime: ArcadeRuntime,
  pattern: ArcadePatternId,
): number {
  if (pattern === "recovery-gap" || pattern.startsWith("two-lane")) {
    return arcadeTuning.spawnIntervals.recovery;
  }

  const base =
    runtime.phase === 1
      ? arcadeTuning.spawnIntervals.phase1
      : runtime.phase === 2
        ? arcadeTuning.spawnIntervals.phase2
        : arcadeTuning.spawnIntervals.phase3;
  return base + arcadeRandom(runtime) * arcadeTuning.spawnIntervals.jitter;
}

function spawnArcadePattern(runtime: ArcadeRuntime, pattern: ArcadePatternId) {
  runtime.currentPattern = pattern;
  pushArcadeEvent(runtime, `Pattern ${pattern}`);

  if (pattern === "recovery-gap") {
    return;
  }

  if (pattern === "gate-after-obstacle") {
    const blockedLane = Math.floor(arcadeRandom(runtime) * 3);
    const gateLane = (blockedLane + 1 + Math.floor(arcadeRandom(runtime) * 2)) % 3;
    spawnArcadeEntity(runtime, "traffic", blockedLane, -48);
    spawnArcadeEntity(runtime, "gate", gateLane, -190);
    return;
  }

  const laneBySinglePattern: Partial<Record<ArcadePatternId, number>> = {
    "single-left": 0,
    "single-center": 1,
    "single-right": 2,
  };
  const singleLane = laneBySinglePattern[pattern];
  if (singleLane !== undefined) {
    spawnArcadeEntity(runtime, "traffic", singleLane, -48);
    return;
  }

  const safeLaneByTwoLanePattern: Partial<Record<ArcadePatternId, number>> = {
    "two-lane-gap-left": 0,
    "two-lane-gap-center": 1,
    "two-lane-gap-right": 2,
  };
  const safeLane = safeLaneByTwoLanePattern[pattern];
  if (safeLane === undefined) {
    return;
  }

  [0, 1, 2].forEach((lane) => {
    if (lane !== safeLane) {
      spawnArcadeEntity(runtime, "traffic", lane, -48);
    }
  });
}

function spawnArcadeEntity(
  runtime: ArcadeRuntime,
  type: ArcadeEntity["type"],
  lane: number,
  y: number,
) {
  const laneCenter = arcadeRoadLeft + arcadeLaneWidth * (lane + 0.5);
  runtime.idCounter += 1;
  runtime.entities.push({
    id: runtime.idCounter,
    lane,
    type,
    x: laneCenter,
    y,
    width: type === "gate" ? 104 : 54,
    height: type === "gate" ? 42 : 72,
  });
}

function awardArcadeGate(runtime: ArcadeRuntime, entity: ArcadeEntity) {
  runtime.timeLeft += arcadeTuning.gateTimeBonus;
  runtime.gatesCollected += 1;
  awardArcadeCombo(runtime, entity.x, entity.y, "Gate");
  addArcadeEffect(
    runtime,
    "pickup",
    entity.x,
    entity.y,
    `+${arcadeTuning.gateTimeBonus}s`,
    0.72,
  );
  runtime.soundEvents.push("pickup");
  pushArcadeEvent(runtime, `Data Gate +${arcadeTuning.gateTimeBonus}s`);
}

function awardArcadeNearMiss(runtime: ArcadeRuntime, entity: ArcadeEntity) {
  runtime.nearMisses += 1;
  awardArcadeCombo(runtime, entity.x, entity.y, "Near miss");
  addArcadeEffect(runtime, "near-miss", entity.x, entity.y, "Near miss", 0.58);
  runtime.soundEvents.push("near-miss");
  pushArcadeEvent(runtime, "Near miss");
}

function awardArcadeCombo(
  runtime: ArcadeRuntime,
  x: number,
  y: number,
  label: string,
) {
  runtime.combo = Math.min(
    arcadeTuning.scoring.comboMax,
    runtime.combo > 0 ? runtime.combo + 1 : 1,
  );
  runtime.comboTimer = arcadeTuning.scoring.comboWindow;

  if (runtime.combo > 1) {
    const bonus = (runtime.combo - 1) * arcadeTuning.scoring.comboStep;
    runtime.comboBonus += bonus;
    addArcadeEffect(runtime, "combo", x, y + 24, `${label} x${runtime.combo}`, 0.7);
  }
}

function isArcadeNearMiss(
  playerBox: { x: number; y: number; width: number; height: number },
  entityBox: { x: number; y: number; width: number; height: number },
): boolean {
  const verticalOverlap =
    entityBox.y < playerBox.y + playerBox.height &&
    entityBox.y + entityBox.height > playerBox.y;
  const horizontalGap = Math.max(
    entityBox.x - (playerBox.x + playerBox.width),
    playerBox.x - (entityBox.x + entityBox.width),
    0,
  );
  return (
    verticalOverlap &&
    horizontalGap > 0 &&
    horizontalGap <= arcadeTuning.nearMissGap
  );
}

function updateArcadeVisualTimers(runtime: ArcadeRuntime, elapsedSeconds: number) {
  runtime.collisionFlash = Math.max(0, runtime.collisionFlash - elapsedSeconds);
  runtime.shakeTime = Math.max(0, runtime.shakeTime - elapsedSeconds);
  runtime.effects = runtime.effects
    .map((effect) => ({ ...effect, age: effect.age + elapsedSeconds }))
    .filter((effect) => effect.age < effect.duration);

  if (runtime.comboTimer > 0) {
    runtime.comboTimer = Math.max(0, runtime.comboTimer - elapsedSeconds);
    if (runtime.comboTimer === 0) {
      runtime.combo = 0;
    }
  }
}

function addArcadeEffect(
  runtime: ArcadeRuntime,
  type: ArcadeEffectType,
  x: number,
  y: number,
  text: string,
  duration: number,
) {
  runtime.idCounter += 1;
  runtime.effects.push({
    id: runtime.idCounter,
    type,
    x,
    y,
    text,
    age: 0,
    duration,
  });
}

function calculateArcadeScore(runtime: ArcadeRuntime): number {
  return (
    Math.floor(runtime.distance * arcadeTuning.scoring.distancePerPixel) +
    runtime.gatesCollected * arcadeTuning.scoring.gate +
    runtime.nearMisses * arcadeTuning.scoring.nearMiss +
    runtime.comboBonus
  );
}

function createArcadeBreakdown(bestScore: number): ArcadeScoreBreakdown {
  return {
    distance: 0,
    gatesCollected: 0,
    nearMisses: 0,
    comboBonus: 0,
    finalScore: 0,
    bestScore,
  };
}

function buildArcadeBreakdown(runtime: ArcadeRuntime): ArcadeScoreBreakdown {
  const finalScore = Math.floor(calculateArcadeScore(runtime));
  return {
    distance: Math.floor(runtime.distance * arcadeTuning.scoring.distancePerPixel),
    gatesCollected: runtime.gatesCollected,
    nearMisses: runtime.nearMisses,
    comboBonus: runtime.comboBonus,
    finalScore,
    bestScore: Math.max(runtime.bestScore, finalScore),
  };
}

function finishArcadeRun(runtime: ArcadeRuntime, reason: string) {
  if (runtime.runFinalized) {
    return;
  }
  runtime.mode = "over";
  runtime.keys.left = false;
  runtime.keys.right = false;
  runtime.combo = 0;
  runtime.comboTimer = 0;
  runtime.score = calculateArcadeScore(runtime);
  runtime.breakdown = buildArcadeBreakdown(runtime);
  runtime.bestScore = Math.max(runtime.bestScore, runtime.breakdown.finalScore);
  runtime.breakdown.bestScore = runtime.bestScore;
  runtime.runFinalized = true;
  pushArcadeEvent(runtime, reason);
}

function pushArcadeEvent(runtime: ArcadeRuntime, event: string) {
  runtime.eventLog = [...runtime.eventLog.slice(-7), event];
}

function arcadeRandom(runtime: ArcadeRuntime): number {
  runtime.seed = (runtime.seed * 1664525 + 1013904223) >>> 0;
  return runtime.seed / 4294967296;
}

function boxesOverlap(
  first: { x: number; y: number; width: number; height: number },
  second: { x: number; y: number; width: number; height: number },
): boolean {
  return (
    first.x < second.x + second.width &&
    first.x + first.width > second.x &&
    first.y < second.y + second.height &&
    first.y + first.height > second.y
  );
}

function drawArcadeScene(
  context: CanvasRenderingContext2D,
  runtime: ArcadeRuntime,
) {
  context.clearRect(0, 0, arcadeWidth, arcadeHeight);
  context.save();
  if (runtime.shakeTime > 0 && !runtime.reducedMotion) {
    const shake = Math.sin(runtime.elapsedTime * 95) * 3;
    context.translate(shake, -shake * 0.35);
  }

  context.fillStyle = arcadeBrand.grass;
  context.fillRect(0, 0, arcadeWidth, arcadeHeight);
  context.fillStyle = arcadeBrand.grassAlt;
  context.fillRect(0, 0, arcadeRoadLeft, arcadeHeight);
  context.fillRect(
    arcadeRoadLeft + arcadeRoadWidth,
    0,
    arcadeRoadLeft,
    arcadeHeight,
  );
  drawRoadsideSigns(context, runtime);

  context.fillStyle = arcadeBrand.road;
  context.fillRect(arcadeRoadLeft, 0, arcadeRoadWidth, arcadeHeight);
  context.fillStyle = "#94a3b8";
  context.fillRect(arcadeRoadLeft - 8, 0, 8, arcadeHeight);
  context.fillRect(arcadeRoadLeft + arcadeRoadWidth, 0, 8, arcadeHeight);

  context.strokeStyle = arcadeBrand.lane;
  context.lineWidth = 4;
  context.setLineDash([24, 28]);
  const laneDividers = [1, 2];
  laneDividers.forEach((laneIndex) => {
    const x = arcadeRoadLeft + arcadeLaneWidth * laneIndex;
    context.beginPath();
    context.moveTo(x, -52 + runtime.roadOffset);
    context.lineTo(x, arcadeHeight + 52);
    context.stroke();
  });
  context.setLineDash([]);

  runtime.entities.forEach((entity) => {
    if (entity.type === "gate") {
      drawGate(context, entity);
    } else {
      drawTraffic(context, entity);
    }
  });
  drawArcadeEffects(context, runtime);
  drawAmbulance(context, runtime.playerX, arcadePlayerY, runtime);
  context.restore();
  drawArcadeFlash(context, runtime);

  if (runtime.mode !== "playing") {
    drawArcadeOverlay(context, runtime);
  }
}

function drawTraffic(context: CanvasRenderingContext2D, entity: ArcadeEntity) {
  const x = entity.x - entity.width / 2;
  const y = entity.y - entity.height / 2;
  context.fillStyle = arcadeBrand.teal;
  roundedRect(context, x, y, entity.width, entity.height, 8);
  context.fill();
  context.fillStyle = "#ccfbf1";
  roundedRect(context, x + 8, y + 10, entity.width - 16, 18, 5);
  context.fill();
  context.fillStyle = "#0f172a";
  context.fillRect(x - 4, y + 12, 5, 16);
  context.fillRect(x + entity.width - 1, y + 12, 5, 16);
  context.fillRect(x - 4, y + entity.height - 28, 5, 16);
  context.fillRect(x + entity.width - 1, y + entity.height - 28, 5, 16);
}

function drawGate(context: CanvasRenderingContext2D, entity: ArcadeEntity) {
  const x = entity.x - entity.width / 2;
  const y = entity.y - entity.height / 2;
  const pulse = 1 + Math.sin(entity.y * 0.04) * 0.06;
  context.save();
  context.translate(entity.x, entity.y);
  context.scale(pulse, pulse);
  context.translate(-entity.x, -entity.y);
  context.strokeStyle = arcadeBrand.red;
  context.lineWidth = 6;
  context.beginPath();
  context.moveTo(x, y + entity.height);
  context.lineTo(x, y + 10);
  context.lineTo(x + entity.width, y + 10);
  context.lineTo(x + entity.width, y + entity.height);
  context.stroke();
  context.fillStyle = "#fee2e2";
  roundedRect(context, x + 25, y - 6, entity.width - 50, 26, 7);
  context.fill();
  context.fillStyle = arcadeBrand.red;
  context.beginPath();
  context.arc(entity.x - 16, y + 7, 7, 0, Math.PI * 2);
  context.arc(entity.x + 16, y + 7, 7, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = "#7f1d1d";
  context.font = "700 14px Geist, Arial, sans-serif";
  context.textAlign = "center";
  context.fillText("+10s", entity.x, y + 34);
  context.restore();
}

function drawAmbulance(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  runtime: ArcadeRuntime,
) {
  const left = x - arcadePlayerWidth / 2;
  const top = y - arcadePlayerHeight / 2;
  context.fillStyle = "#ffffff";
  roundedRect(context, left, top, arcadePlayerWidth, arcadePlayerHeight, 9);
  context.fill();
  context.strokeStyle = arcadeBrand.blue;
  context.lineWidth = 3;
  context.stroke();
  context.fillStyle = "#dbeafe";
  roundedRect(context, left + 8, top + 8, arcadePlayerWidth - 16, 18, 5);
  context.fill();
  const sirenPhase = Math.sin(runtime.elapsedTime * 18) > 0;
  context.fillStyle = sirenPhase ? arcadeBrand.red : arcadeBrand.blue;
  roundedRect(context, left + 13, top - 5, 8, 8, 3);
  context.fill();
  context.fillStyle = sirenPhase ? arcadeBrand.blue : arcadeBrand.red;
  roundedRect(context, left + 25, top - 5, 8, 8, 3);
  context.fill();
  context.globalAlpha = runtime.reducedMotion ? 0.22 : 0.34;
  context.fillStyle = sirenPhase ? arcadeBrand.blue : arcadeBrand.red;
  context.beginPath();
  context.ellipse(x, top + 3, 28, 9, 0, 0, Math.PI * 2);
  context.fill();
  context.globalAlpha = 1;
  context.fillStyle = arcadeBrand.blue;
  roundedRect(context, left + 11, top + 35, 24, 21, 5);
  context.fill();
  context.fillStyle = "#ffffff";
  context.font = "800 18px Geist, Arial, sans-serif";
  context.textAlign = "center";
  context.fillText("E", x, top + 52);
  context.fillStyle = arcadeBrand.dark;
  context.fillRect(left - 4, top + 16, 5, 16);
  context.fillRect(left + arcadePlayerWidth - 1, top + 16, 5, 16);
  context.fillRect(left - 4, top + arcadePlayerHeight - 30, 5, 16);
  context.fillRect(
    left + arcadePlayerWidth - 1,
    top + arcadePlayerHeight - 30,
    5,
    16,
  );
}

function drawRoadsideSigns(
  context: CanvasRenderingContext2D,
  runtime: ArcadeRuntime,
) {
  const signs = [
    { label: "E-Dispatch", x: 36, width: 92 },
    { label: "Route Check", x: 584, width: 98 },
    { label: "Data Gate +10s", x: 26, width: 118 },
  ];

  signs.forEach((sign, index) => {
    const y = ((runtime.distance * 0.12 + index * 190) % 650) - 120;
    context.fillStyle = "#64748b";
    context.fillRect(sign.x + sign.width / 2 - 3, y + 24, 6, 42);
    context.fillStyle = index === 2 ? "#fee2e2" : "#eff6ff";
    roundedRect(context, sign.x, y, sign.width, 34, 6);
    context.fill();
    context.strokeStyle = index === 2 ? arcadeBrand.red : arcadeBrand.blue;
    context.lineWidth = 2;
    context.stroke();
    context.fillStyle = index === 2 ? "#7f1d1d" : "#1e3a8a";
    context.font = "700 11px Geist, Arial, sans-serif";
    context.textAlign = "center";
    context.fillText(sign.label, sign.x + sign.width / 2, y + 22);
  });
}

function drawArcadeEffects(
  context: CanvasRenderingContext2D,
  runtime: ArcadeRuntime,
) {
  runtime.effects.forEach((effect) => {
    const progress = effect.age / effect.duration;
    const lift = runtime.reducedMotion ? 8 : 26;
    const y = effect.y - progress * lift;
    context.globalAlpha = Math.max(0, 1 - progress);
    context.fillStyle =
      effect.type === "collision"
        ? arcadeBrand.red
        : effect.type === "pickup"
          ? "#7f1d1d"
          : arcadeBrand.blue;
    context.font = "800 16px Geist, Arial, sans-serif";
    context.textAlign = "center";
    context.fillText(effect.text, effect.x, y);
    context.globalAlpha = 1;
  });
}

function drawArcadeFlash(
  context: CanvasRenderingContext2D,
  runtime: ArcadeRuntime,
) {
  if (runtime.collisionFlash <= 0) {
    return;
  }
  context.fillStyle = `rgba(180, 35, 24, ${Math.min(0.26, runtime.collisionFlash)})`;
  context.fillRect(0, 0, arcadeWidth, arcadeHeight);
}

function drawArcadeOverlay(
  context: CanvasRenderingContext2D,
  runtime: ArcadeRuntime,
) {
  context.fillStyle = "rgba(15, 23, 42, 0.66)";
  context.fillRect(0, 0, arcadeWidth, arcadeHeight);
  context.fillStyle = "rgba(255, 255, 255, 0.94)";
  roundedRect(context, arcadeWidth / 2 - 190, 154, 380, 174, 10);
  context.fill();
  context.textAlign = "center";
  context.fillStyle = arcadeBrand.blue;
  context.font = "800 29px Geist, Arial, sans-serif";
  context.fillText(
    runtime.mode === "over"
      ? "Game over"
      : runtime.mode === "paused"
        ? "Paused"
        : "E-Dispatch",
    arcadeWidth / 2,
    198,
  );
  context.fillStyle = arcadeBrand.dark;
  context.font = "600 17px Geist, Arial, sans-serif";
  context.fillText(
    runtime.mode === "over"
      ? `Score ${Math.floor(runtime.score)}  Best ${runtime.bestScore}`
      : runtime.mode === "paused"
        ? "Press P or Enter to resume."
        : "Press Space or Start. Arrow keys steer.",
    arcadeWidth / 2,
    234,
  );
  context.font = "500 14px Geist, Arial, sans-serif";
  const helperText =
    runtime.mode === "over"
      ? "Restart for another short run."
      : "Arcade-only easter egg. Red gates add +10 seconds.";
  context.fillText(
    helperText,
    arcadeWidth / 2,
    264,
  );
  if (runtime.mode === "over") {
    const breakdown = buildArcadeBreakdown(runtime);
    context.font = "700 13px Geist, Arial, sans-serif";
    context.fillStyle = arcadeBrand.teal;
    context.fillText(
      `Distance ${breakdown.distance}  Gates ${breakdown.gatesCollected}  Near misses ${breakdown.nearMisses}  Combo ${breakdown.comboBonus}`,
      arcadeWidth / 2,
      292,
    );
  }
}

function renderArcadeToText(runtime: ArcadeRuntime): string {
  const breakdown = buildArcadeBreakdown(runtime);
  return JSON.stringify({
    note: "E-Dispatch is an arcade-only easter egg. It is separate from model inputs, outputs, saved runs, predictions, and Results logic. Coordinates use origin top-left; x increases right; y increases down.",
    controls:
      "ArrowLeft/ArrowRight or A/D steer; Space or Enter starts/restarts/resumes; P pauses/resumes; Escape pauses while playing.",
    mode: runtime.mode,
    audioMuted: runtime.audioMuted,
    bestScore: runtime.bestScore,
    score: Math.floor(runtime.score),
    timeLeft: Number(Math.max(0, runtime.timeLeft).toFixed(2)),
    phase: runtime.phase,
    currentPattern: runtime.currentPattern,
    combo: runtime.combo,
    scoring: {
      distance: breakdown.distance,
      gatesCollected: breakdown.gatesCollected,
      nearMisses: breakdown.nearMisses,
      comboBonus: breakdown.comboBonus,
      finalScore: breakdown.finalScore,
      bestScore: breakdown.bestScore,
    },
    player: {
      x: Number(runtime.playerX.toFixed(1)),
      y: arcadePlayerY,
      width: arcadePlayerWidth,
      height: arcadePlayerHeight,
    },
    activeEntities: runtime.entities
      .slice(0, 10)
      .map((entity) => ({
        type: entity.type,
        lane: entity.lane,
        x: Number(entity.x.toFixed(1)),
        y: Number(entity.y.toFixed(1)),
        width: entity.width,
        height: entity.height,
        nearMissAwarded: Boolean(entity.nearMissAwarded),
      })),
    recentEffects: runtime.effects.map((effect) => ({
      type: effect.type,
      text: effect.text,
      x: Number(effect.x.toFixed(1)),
      y: Number(effect.y.toFixed(1)),
      age: Number(effect.age.toFixed(2)),
    })),
    recentEvents: runtime.eventLog.slice(-8),
  });
}

function roundedRect(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + safeRadius, y);
  context.arcTo(x + width, y, x + width, y + height, safeRadius);
  context.arcTo(x + width, y + height, x, y + height, safeRadius);
  context.arcTo(x, y + height, x, y, safeRadius);
  context.arcTo(x, y, x + width, y, safeRadius);
  context.closePath();
}

export default App;
