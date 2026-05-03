export const literatureSources = [
  {
    id: "tripod-ai",
    label: "TRIPOD+AI statement",
    url: "https://www.bmj.com/content/385/bmj-2023-078378",
    note: "Transparent prediction-model reporting for regression and machine-learning models.",
  },
  {
    id: "probast-ai",
    label: "PROBAST+AI",
    url: "https://www.bmj.com/content/388/bmj-2024-082505",
    note: "Risk of bias, quality, and applicability checks for prediction models.",
  },
  {
    id: "fda-cds-2026",
    label: "FDA Clinical Decision Support Software guidance",
    url: "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software",
    note:
      "Safety and regulatory boundary reference for avoiding directive clinical deployment language.",
  },
  {
    id: "decide-ai",
    label: "DECIDE-AI",
    url: "https://www.nature.com/articles/s41591-022-01772-9",
    note:
      "Reference for later early-stage live evaluation planning if the project moves beyond offline validation.",
  },
  {
    id: "cdc-nhamcs",
    label: "CDC NHAMCS documentation",
    url: "https://www.cdc.gov/nchs/nhamcs/documentation/index.html",
    note: "Primary free public data path for the course appendix.",
  },
  {
    id: "nhamcs-2022-ed",
    label: "2022 NHAMCS ED public-use documentation",
    url: "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/nhamcs/doc22-ed-508.pdf",
    note: "Emergency department public-use file documentation.",
  },
  {
    id: "nhamcs-2022-summary-tables",
    label: "2022 NHAMCS ED summary tables",
    url: "https://www.cdc.gov/nchs/data/nhamcs/web_tables/2022-nhamcs-ed-web-tables.pdf",
    note:
      "Contextual disposition counts and warning that more than one disposition may be reported per visit.",
  },
  {
    id: "nhamcs-2022-prf",
    label: "2022 NHAMCS ED patient record form",
    url: "https://www.cdc.gov/nchs/data/nhamcs/2022-nhamcs-ed-prf-sample-card-508.pdf",
    note:
      "Disposition category source for observation-to-hospitalization, observation-to-discharge, outpatient follow-up, transfer, and nonroutine exits.",
  },
  {
    id: "nhamcs-2022-data",
    label: "2022 NHAMCS ED public-use data",
    url: "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHAMCS/ed2022.zip",
    note: "Raw public-use ED data archive for the offline empirical appendix pipeline.",
  },
  {
    id: "nhamcs-2022-stata",
    label: "2022 NHAMCS ED Stata files",
    url: "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/stata/ed2022-stata.zip",
    note: "CDC Stata archive used by the offline coefficient and cohort-count pipeline.",
  },
  {
    id: "ahrq-neds",
    label: "AHRQ NEDS file specifications",
    url: "https://hcup-us.ahrq.gov/db/nation/neds/nedsfilespecs.jsp",
    note: "Large-scale ED disposition endpoint reference.",
  },
  {
    id: "ahrq-neds-edevent",
    label: "AHRQ NEDS EDevent note",
    url: "https://hcup-us.ahrq.gov/db/vars/edevent/nedsnote.jsp",
    note:
      "Endpoint crosswalk for treated and released, same-hospital admission, transfer, death, and unknown destination.",
  },
  {
    id: "mimic-iv-ed",
    label: "MIMIC-IV-ED",
    url: "https://physionet.org/content/mimic-iv-ed/2.2/",
    note: "Richer ED workflow prototyping and disposition values.",
  },
  {
    id: "fda-multiple-endpoints",
    label: "FDA multiple endpoints guidance",
    url: "https://www.fda.gov/media/162416/download",
    note:
      "Methodological caution for composite endpoints and component outcome interpretation.",
  },
  {
    id: "lhs",
    label: "Latin Hypercube uncertainty analysis",
    url: "https://www.sciencedirect.com/science/article/abs/pii/S0951832003000589",
    note: "Monte Carlo uncertainty propagation with stratified sampling and sensitivity analysis.",
  },
  {
    id: "vite",
    label: "Vite guide",
    url: "https://vite.dev/guide/",
    note: "Static React application build path.",
  },
  {
    id: "shadcn",
    label: "shadcn/ui Vite installation",
    url: "https://ui.shadcn.com/docs/installation/vite",
    note: "Source-owned accessible component setup.",
  },
]

export const dataCrosswalkRows = [
  {
    variable: "Disposition endpoint",
    nhamcs: "Direct disposition flags with OBSHOS/OBSDIS split",
    neds: "Direct EDevent fields with same-hospital admission and transfer split",
    mimic: "Direct disposition values; observation linkage only if locally available",
    strength: "Direct",
  },
  {
    variable: "Abdominal pain complaint",
    nhamcs: "Reason-for-visit codes",
    neds: "ICD-10/CCSR proxy",
    mimic: "Chief complaint and diagnosis proxy",
    strength: "Direct/proxy",
  },
  {
    variable: "Pain severity",
    nhamcs: "PAINSCALE proxy/direct field",
    neds: "Unavailable in core data",
    mimic: "Triage pain score proxy",
    strength: "Direct/proxy",
  },
  {
    variable: "Onset and pain pattern",
    nhamcs: "Weak or unavailable",
    neds: "Unavailable",
    mimic: "Possible only through text proxy",
    strength: "Proxy/unavailable",
  },
]
