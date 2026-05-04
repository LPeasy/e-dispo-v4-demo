import { Badge } from "@/components/ui/badge"
import {
  Field,
  FieldDescription,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  calculatePas5Acuity,
  pas5Questions,
  type Pas5AnswerId,
  type Pas5Inputs,
  type Pas5QuestionId,
} from "@/model/aap3Acuity"

export function Pas5AcuityInput({
  value,
  onChange,
  idPrefix,
}: {
  value: Pas5Inputs
  onChange: (value: Pas5Inputs) => void
  idPrefix: string
}) {
  const result = calculatePas5Acuity(value)

  const setAnswer = (questionId: Pas5QuestionId, answerId: Pas5AnswerId) => {
    onChange({
      ...value,
      [questionId]: answerId,
    })
  }

  return (
    <FieldSet className="rounded-lg border border-border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <FieldLegend>Patient-perceived acuity proxy</FieldLegend>
          <FieldDescription className="mt-1">
            Five self-report questions. In e-dispo-v4.1, A1/A2 activate the
            high-acuity surrogate term; A3/A4/A5 are the reference side.
          </FieldDescription>
        </div>
        <Badge variant="outline">PAS-5</Badge>
      </div>
      <div className="mt-4 grid gap-4">
        {pas5Questions.map((question) => (
          <Field key={question.id} className="gap-2">
            <FieldLabel id={`${idPrefix}-${question.id}-label`}>
              {question.label}
            </FieldLabel>
            <ToggleGroup
              type="single"
              value={value[question.id]}
              onValueChange={(nextValue) => {
                const option = question.options.find(
                  (candidate) => candidate.id === nextValue,
                )
                if (option) {
                  setAnswer(question.id, option.id)
                }
              }}
              aria-labelledby={`${idPrefix}-${question.id}-label`}
              className="grid grid-cols-4 gap-2 max-[980px]:grid-cols-2 max-[520px]:grid-cols-1"
              variant="outline"
            >
              {question.options.map((option) => (
                <ToggleGroupItem
                  key={option.id}
                  value={option.id}
                  className="h-auto min-h-12 justify-start whitespace-normal px-3 py-2 text-left text-xs leading-5"
                >
                  <span className="flex w-full items-center justify-between gap-2">
                    <span>{option.label}</span>
                    <span className="shrink-0 rounded-md border border-border bg-background px-1.5 py-0.5 text-[0.7rem] text-muted-foreground">
                      {option.score}
                    </span>
                  </span>
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </Field>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-4 gap-2 rounded-lg border border-border bg-card p-3 text-sm max-[760px]:grid-cols-2">
        <Pas5ResultDatum label="Score" value={`${result.score}/15`} />
        <Pas5ResultDatum label="Class" value={result.acuityClass} />
        <Pas5ResultDatum
          label="High-acuity proxy"
          value={result.highAcuityProxy ? "Yes" : "No"}
        />
        <Pas5ResultDatum
          label="Guardrails"
          value={result.guardrailCount === 0 ? "None" : String(result.guardrailCount)}
        />
      </div>
    </FieldSet>
  )
}

function Pas5ResultDatum({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
      <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 truncate font-semibold text-foreground">{value}</p>
    </div>
  )
}
