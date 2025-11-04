/**
 * Outline normalization utilities.
 *
 * 背景:
 * - エージェントが返すアウトラインは、`subsections` でネストされているのに
 *   `level` が一律で (例: 全て 2 や 3 のまま) というケースがある。
 * - 旧実装は「ネストが深い＝見出しレベルも深いはず」と推測して `parent.level + 1`
 *   に矯正していたため、H2/H3 しかないはずの構成が UI で H4/H5/H6 へ暴走していた。
 *
 * 方針:
 * - 宣言された `level` を基本的に尊重しつつ、スタックを使ってツリーを再構築する。
 * - 階層構造は宣言された順序から計算し直し、兄弟関係・親子関係のみ整理する。
 * - `level` の補正は `[topLevel, 6]` に収める最小限のクランプに留める。
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
  const numeric = Number.isFinite(value) ? Math.trunc(value) : minLevel;
  const clamped = Math.min(Math.max(numeric, MIN_HEADING_LEVEL), MAX_HEADING_LEVEL);
  return Math.max(clamped, minLevel);
};

const fallbackEstimatedChars = (level: number, topLevel: number) =>
  level > topLevel ? 200 : 300;

const collectSections = (
  sections: OutlineSectionInput[] | null | undefined,
  acc: OutlineSectionInput[] = []
): OutlineSectionInput[] => {
  if (!Array.isArray(sections)) return acc;
  for (const section of sections) {
    if (!section || typeof section !== 'object') continue;
    acc.push(section);
    if (Array.isArray(section.subsections) && section.subsections.length > 0) {
      collectSections(section.subsections, acc);
    }
  }
  return acc;
};

export const normalizeOutlineSections = (
  sections: OutlineSectionInput[] | null | undefined,
  rawTopLevel: number | null | undefined
): NormalizedOutlineSection[] => {
  const topLevel = clampHeadingLevel(
    Number.isFinite(rawTopLevel) ? Number(rawTopLevel) : FALLBACK_TOP_LEVEL,
    FALLBACK_TOP_LEVEL
  );

  const flat = collectSections(sections);
  if (flat.length === 0) {
    return [];
  }

  const roots: NormalizedOutlineSection[] = [];
  const stack: NormalizedOutlineSection[] = [];

  for (const rawSection of flat) {
    const heading =
      typeof rawSection?.heading === 'string' ? rawSection.heading.trim() : '';
    if (!heading) continue;

    const declaredLevel = clampHeadingLevel(
      Number.isFinite(rawSection?.level) ? Number(rawSection.level) : topLevel,
      topLevel
    );

    const description =
      typeof rawSection?.description === 'string'
        ? rawSection.description.trim()
        : '';
    const estimatedRaw = Number.isFinite(rawSection?.estimated_chars)
      ? Number(rawSection.estimated_chars)
      : NaN;
    const estimated_chars =
      estimatedRaw > 0 ? Math.trunc(estimatedRaw) : fallbackEstimatedChars(declaredLevel, topLevel);

    const node: NormalizedOutlineSection = {
      heading,
      level: declaredLevel,
      description: description || undefined,
      estimated_chars,
      subsections: [],
    };

    // スタックの上から、現在のノードより level が高いものをすべてポップする。
    // これにより兄弟関係・親子関係を正しく保つ。
    while (stack.length > 0 && declaredLevel <= stack[stack.length - 1].level) {
      stack.pop();
    }

    const parent = stack.length > 0 ? stack[stack.length - 1] : null;
    if (parent && declaredLevel > parent.level) {
      parent.subsections.push(node);
    } else {
      roots.push(node);
    }

    stack.push(node);
  }

  return roots;
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

