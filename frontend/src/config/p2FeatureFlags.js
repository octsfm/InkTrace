const readBool = (value, defaultValue = false) => {
  if (value === undefined || value === null || value === '') {
    return defaultValue
  }
  return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase())
}

export const P2_FEATURE_FLAGS = {
  enable_multi_chapter: readBool(import.meta.env.VITE_P2_ENABLE_MULTI_CHAPTER, false),
  enable_citation_link: readBool(import.meta.env.VITE_P2_ENABLE_CITATION_LINK, false),
  enable_style_dna: readBool(import.meta.env.VITE_P2_ENABLE_STYLE_DNA, false),
  enable_auto_queue: readBool(import.meta.env.VITE_P2_ENABLE_AUTO_QUEUE, false),
  enable_mentions: readBool(import.meta.env.VITE_P2_ENABLE_MENTIONS, false),
  enable_opening_agent: readBool(import.meta.env.VITE_P2_ENABLE_OPENING_AGENT, false),
  enable_outline_assist: readBool(import.meta.env.VITE_P2_ENABLE_OUTLINE_ASSIST, false),
  enable_selection_rewrite: readBool(import.meta.env.VITE_P2_ENABLE_SELECTION_REWRITE, false),
  enable_cost_dashboard: readBool(import.meta.env.VITE_P2_ENABLE_COST_DASHBOARD, false),
  enable_analysis_dashboard: readBool(import.meta.env.VITE_P2_ENABLE_ANALYSIS_DASHBOARD, false)
}

export function isP2FeatureEnabled(flagName) {
  if (!flagName) {
    return true
  }
  return Boolean(P2_FEATURE_FLAGS[flagName])
}

