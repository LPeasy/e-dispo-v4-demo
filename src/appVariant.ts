import {
  GENERAL_E_DISPO_PUBLIC_MODEL_ID,
} from "@/data/generalEDispoModel"
import {
  E_DISPO_V4_1_PAS5_MODEL_ID,
} from "@/data/eDispoV4Model"
import type { RunnableModelId } from "@/model/types"

export type AppVariant = "e_dispo_v4" | "general_e_dispo"

export type AppVariantConfig = {
  variant: AppVariant
  modelId: RunnableModelId
  siteTitle: string
  shortModelLabel: string
  publicPath: string
  scope: string
}

function parseAppVariant(value: string | undefined): AppVariant {
  return value === "general_e_dispo" ? "general_e_dispo" : "e_dispo_v4"
}

export const appVariant = parseAppVariant(import.meta.env.VITE_APP_VARIANT)

export const appVariantConfig: AppVariantConfig =
  appVariant === "general_e_dispo"
    ? {
        variant: "general_e_dispo",
        modelId: GENERAL_E_DISPO_PUBLIC_MODEL_ID,
        siteTitle: "General E-Dispo",
        shortModelLabel: "general-E-Dispo v1 sex-adjusted",
        publicPath: "general-e-dispo-demo",
        scope:
          "All-sex/all-age non-trauma NHAMCS educational/statistical model.",
      }
    : {
        variant: "e_dispo_v4",
        modelId: E_DISPO_V4_1_PAS5_MODEL_ID,
        siteTitle: "E-Dispo",
        shortModelLabel: "e-dispo-v4.1",
        publicPath: "e-dispo-v4-demo",
        scope:
          "Adult male non-traumatic abdominal-pain educational/statistical model.",
      }

export const isGeneralEDispoVariant =
  appVariantConfig.variant === "general_e_dispo"
