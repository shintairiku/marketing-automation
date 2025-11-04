/**
 * Utility functions for normalizing outline data structures returned by agents.
 *
 * Some agent responses contain deeply nested `subsections` whose declared
 * heading `level` does not increase with depth (e.g. multiple nested H3 items).
 * The previous UI logic tried to "fix" these cases by forcing deeper nodes to
 * bump their levels (parent level + 1). That escalated large trees into H4/H5/H6
 * even when the agent only intended H2/H3, which caused the front-end to render
 * excessive heading levels.
 *
 * This module rebuilds the hierarchy purely from the declared `level` values
 * while preserving order. Nodes that would otherwise regress or jump multiple
 * levels are clamped to a sensible range so that:
 *   - Top-level headings stay at the requested outline level (usually H2 or H3)
 *   - Siblings retain their intended `level`
 *   - Children cannot skip more than one level deeper than their parent
 *
 * The resulting structure prevents runaway H4/H5/H6 chains while still handling
 * imperfect agent output gracefully.
 */

export type OutlineSectionInput = {
  heading?: string | null;
  level?: number | null;
  description?: string | null;
  estimated_chars?: number | null;
  subsections?: OutlineSectionInput[] | null;
};

export type NormalizedOutlineSection = {
  heading: string;
  level: number;
  description?: string;
  estimated_chars: number;
  subsections: NormalizedOutlineSection[];
};

export type NormalizedOutline = {
  title: string;
  suggested_tone?: string;
  top_level_heading: number;
  sections: NormalizedOutlineSection[];
};

const FALLBACK_TOP_LEVEL = 2;
const MIN_HEADING_LEVEL = 1;
const MAX_HEADING_LEVEL = 6;

const clampHeadingLevel = (value: number, minLevel: number) => {
  const clamped = Number.isFinite(value)
    ? Math.min(Math.max(Math.trunc(value), MIN_HEADING_LEVEL), MAX_HEADING_LEVEL)
    : minLevel;
  return Math.max(clamped, minLevel);
};

const fallbackEstimatedChars = (level: number, topLevel: number) => {
  return level > topLevel ? 200 : 300;
};

const flattenSections = (
  sections: OutlineSectionInput[] | null | undefined,
  collector: OutlineSectionInput[] = []
): OutlineSectionInput[] => {
  if (!Array.isArray(sections)) {
    return collector;
  }
  for (const section of sections) {
    if (!section || typeof section !== 'object') continue;
    collector.push(section);
    if (Array.isArray(section.subsections) && section.subsections.length > 0) {
      flattenSections(section.subsections, collector);
    }
  }
  return collector;
};

export const normalizeOutlineSections = (
  sections: OutlineSectionInput[] | null | undefined,
  rawTopLevel: number | null | undefined
): NormalizedOutlineSection[] => {
  const topLevel = clampHeadingLevel(
    Number.isFinite(rawTopLevel) ? Number(rawTopLevel) : FALLBACK_TOP_LEVEL,
    FALLBACK_TOP_LEVEL
  );
  const flat = flattenSections(sections);
  if (flat.length === 0) {
    return [];
  }

  const normalized: NormalizedOutlineSection[] = [];
  const stack: NormalizedOutlineSection[] = [];

  for (const rawSection of flat) {
    const heading =
      typeof rawSection?.heading === 'string' ? rawSection.heading.trim() : '';
    if (!heading) {
      // Skip empty headings rather than emitting blank nodes
      continue;
    }

    const rawLevel = Number.isFinite(rawSection?.level)
      ? Number(rawSection.level)
      : topLevel;
    let level = clampHeadingLevel(rawLevel, topLevel);

    // Move up the stack until the new level is strictly deeper than the parent
    while (stack.length > 0 && level <= stack[stack.length - 1].level) {
      stack.pop();
    }

    const parent = stack.length > 0 ? stack[stack.length - 1] : null;
    if (!parent) {
      level = topLevel;
    } else {
      const maxAllowed = Math.min(parent.level + 1, MAX_HEADING_LEVEL);
      if (level <= parent.level) {
        level = Math.min(parent.level + 1, MAX_HEADING_LEVEL);
      } else if (level > maxAllowed) {
        level = maxAllowed;
      }
    }

    const description =
      typeof rawSection?.description === 'string'
        ? rawSection.description.trim()
        : '';
    const estimatedRaw = Number.isFinite(rawSection?.estimated_chars)
      ? Number(rawSection.estimated_chars)
      : NaN;
    const estimated_chars =
      estimatedRaw > 0 ? Math.trunc(estimatedRaw) : fallbackEstimatedChars(level, topLevel);

    const node: NormalizedOutlineSection = {
      heading,
      level,
      description: description || undefined,
      estimated_chars,
      subsections: [],
    };

    if (!parent) {
      normalized.push(node);
    } else {
      parent.subsections.push(node);
    }

    stack.push(node);
  }

  return normalized;
};

export const normalizeOutline = (outline: any): NormalizedOutline | null => {
  if (!outline || typeof outline !== 'object') {
    return null;
  }

  const title =
    typeof outline.title === 'string' && outline.title.trim().length > 0
      ? outline.title.trim()
      : '生成されたアウトライン';

  const suggested_tone =
    typeof outline.suggested_tone === 'string' && outline.suggested_tone.trim().length > 0
      ? outline.suggested_tone.trim()
      : undefined;

  const topLevel = clampHeadingLevel(
    Number.isFinite(outline.top_level_heading)
      ? Number(outline.top_level_heading)
      : FALLBACK_TOP_LEVEL,
    FALLBACK_TOP_LEVEL
  );

  const sections = normalizeOutlineSections(outline.sections, topLevel);

  return {
    title,
    suggested_tone,
    top_level_heading: topLevel,
    sections,
  };
};

