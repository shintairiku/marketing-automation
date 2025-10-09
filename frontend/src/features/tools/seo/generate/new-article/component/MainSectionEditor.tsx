"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Edit3, Plus, Save, Trash2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { getOutlineApprovalMessage } from '@/utils/flow-config';

import type { EditableOutline, EditableOutlineSection } from "../../types/outline";

type NormalizedOutlineSection = {
  heading: string;
  level: number;
  description?: string;
  estimated_chars: number;
  subsections: NormalizedOutlineSection[];
};

type Props = {
  value: EditableOutline;
  onChange: (next: EditableOutline) => void;
  onCancel?: () => void;
  onSaveAndStart: (edited: {
    title: string;
    suggested_tone?: string;
    top_level_heading: number;
    sections: NormalizedOutlineSection[];
  }) => void;
  disabled?: boolean;
};

const ensureSubsections = (section: EditableOutlineSection | undefined): EditableOutlineSection[] => {
  if (!section) return [];
  return Array.isArray(section.subsections) ? section.subsections : [];
};

export default function MainSectionEditor({ value, onChange, onCancel, onSaveAndStart, disabled }: Props) {
  const [touched, setTouched] = useState(false);

  const sections = useMemo(() => value.sections ?? [], [value.sections]);
  const childLevelBase = useMemo(() => Math.min(value.topLevel + 1, 6), [value.topLevel]);
  const childLevelSecondary = useMemo(() => Math.min(childLevelBase + 1, 6), [childLevelBase]);

  const errors = useMemo(() => {
    const errs: string[] = [];
    if (!value.title || !value.title.trim()) errs.push("タイトルを入力してください");
    if (!sections.length) errs.push("少なくとも1つの大見出しが必要です");
    if (sections.some((s) => !s.heading || !s.heading.trim())) errs.push("空の大見出しがあります");
    return errs;
  }, [value.title, sections]);

  const updateSection = (index: number, patch: Partial<EditableOutlineSection>) => {
    setTouched(true);
    const nextSections = sections.map((section, i) => {
      if (i !== index) {
        return section;
      }
      const currentSubsections = ensureSubsections(section);
      return {
        ...section,
        subsections: patch.subsections ? ensureSubsections({ subsections: patch.subsections } as EditableOutlineSection) : currentSubsections,
        ...patch,
      } as EditableOutlineSection;
    });
    onChange({ ...value, sections: nextSections });
  };

  const addSection = () => {
    setTouched(true);
    const newSection: EditableOutlineSection = {
      heading: "",
      level: value.topLevel,
      description: "",
      estimated_chars: 300,
      subsections: [],
    };
    onChange({ ...value, sections: [...sections, newSection] });
  };

  const removeSection = (index: number) => {
    setTouched(true);
    onChange({ ...value, sections: sections.filter((_, i) => i !== index) });
  };

  const moveSection = (index: number, dir: -1 | 1) => {
    const target = index + dir;
    if (target < 0 || target >= sections.length) return;
    setTouched(true);
    const nextSections = sections.slice();
    const tmp = nextSections[index];
    nextSections[index] = nextSections[target];
    nextSections[target] = tmp;
    onChange({ ...value, sections: nextSections });
  };

  const addSubsection = (sectionIndex: number) => {
    setTouched(true);
    const baseLevel = childLevelBase;
    const template: EditableOutlineSection = {
      heading: "",
      level: baseLevel,
      description: "",
      estimated_chars: baseLevel > value.topLevel ? 200 : 300,
      subsections: [],
    };
    const nextSections = sections.map((section, i) =>
      i === sectionIndex
        ? { ...section, subsections: [...ensureSubsections(section), template] }
        : section,
    );
    onChange({ ...value, sections: nextSections });
  };

  const updateSubsection = (
    sectionIndex: number,
    subsectionIndex: number,
    patch: Partial<EditableOutlineSection>,
  ) => {
    setTouched(true);
    const nextSections = sections.map((section, i) => {
      if (i !== sectionIndex) return section;
      const subsections = ensureSubsections(section).map((sub, subIdx) => {
        if (subIdx !== subsectionIndex) return sub;
        return {
          ...sub,
          subsections: patch.subsections ? ensureSubsections({ subsections: patch.subsections } as EditableOutlineSection) : ensureSubsections(sub),
          ...patch,
        } as EditableOutlineSection;
      });
      return { ...section, subsections };
    });
    onChange({ ...value, sections: nextSections });
  };

  const removeSubsection = (sectionIndex: number, subsectionIndex: number) => {
    setTouched(true);
    const nextSections = sections.map((section, i) =>
      i === sectionIndex
        ? {
            ...section,
            subsections: ensureSubsections(section).filter((_, idx) => idx !== subsectionIndex),
          }
        : section,
    );
    onChange({ ...value, sections: nextSections });
  };

  const moveSubsection = (sectionIndex: number, subsectionIndex: number, dir: -1 | 1) => {
    const target = subsectionIndex + dir;
    const currentSection = sections[sectionIndex];
    const subsections = ensureSubsections(currentSection);
    if (target < 0 || target >= subsections.length) return;
    setTouched(true);
    const nextSubsections = subsections.slice();
    const tmp = nextSubsections[subsectionIndex];
    nextSubsections[subsectionIndex] = nextSubsections[target];
    nextSubsections[target] = tmp;
    updateSection(sectionIndex, { subsections: nextSubsections });
  };

  const sanitizeSection = (
    section: EditableOutlineSection,
    expectedLevel: number,
  ): NormalizedOutlineSection | null => {
    const heading = section.heading?.trim();
    if (!heading) return null;

    const rawLevel = typeof section.level === "number" ? section.level : expectedLevel;
    const normalizedLevel = Math.max(expectedLevel, Math.min(rawLevel, 6));
    const description = section.description?.trim();
    const estimatedRaw = typeof section.estimated_chars === "number" ? section.estimated_chars : 0;
    const fallbackChars = normalizedLevel > value.topLevel ? 200 : 300;
    const estimated_chars = estimatedRaw > 0 ? estimatedRaw : fallbackChars;
    const subsectionsSource = ensureSubsections(section);
    const nextExpected = Math.min(normalizedLevel + 1, 6);
    const normalizedSubsections = subsectionsSource
      .map((sub) => sanitizeSection(sub, nextExpected))
      .filter((subsection): subsection is NormalizedOutlineSection => subsection !== null);

    return {
      heading,
      level: normalizedLevel,
      description: description || undefined,
      estimated_chars,
      subsections: normalizedSubsections,
    };
  };

  const onSave = () => {
    const cleanedSections = sections
      .map((section) => sanitizeSection(section, value.topLevel))
      .filter((section): section is NormalizedOutlineSection => section !== null);

    onSaveAndStart({
      title: value.title.trim(),
      suggested_tone: value.suggested_tone?.trim() || undefined,
      top_level_heading: value.topLevel,
      sections: cleanedSections,
    });
  };

  const childLevelOptions = useMemo(() => {
    if (childLevelBase === childLevelSecondary) {
      return [childLevelBase];
    }
    return [childLevelBase, childLevelSecondary];
  }, [childLevelBase, childLevelSecondary]);

  return (
    <Card className="border border-blue-200 bg-blue-50/40">
      <CardContent className="p-4 space-y-5">
        <div>
          <h4 className="mb-2 flex items-center gap-2 font-medium">
            <Edit3 className="h-4 w-4" />
            アウトライン編集
          </h4>
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">記事タイトル</label>
              <Input
                value={value.title || ""}
                onChange={(e) => onChange({ ...value, title: e.target.value })}
                placeholder="記事のタイトルを入力..."
                disabled={disabled}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">推奨トーン</label>
              <Input
                value={value.suggested_tone || ""}
                onChange={(e) => onChange({ ...value, suggested_tone: e.target.value })}
                placeholder="例：丁寧で読みやすい解説調"
                disabled={disabled}
              />
            </div>
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-dashed border-blue-300 bg-blue-100/40 p-3 text-sm text-blue-900">
          <div className="flex flex-wrap items-center gap-3">
            <span>大見出し:</span>
            <Badge variant="outline" className="bg-white text-blue-700">
              H{value.topLevel}
            </Badge>
            <span>小見出し候補:</span>
            <Badge variant="outline" className="bg-white text-blue-700">
              H{childLevelBase}
            </Badge>
            {childLevelOptions.length > 1 && (
              <Badge variant="outline" className="bg-white text-blue-700">
                H{childLevelSecondary}
              </Badge>
            )}
          </div>
          <p>
            大見出しごとに関連する小見出しを追加し、文章構成を具体化してください。小見出しの順序は執筆時にそのまま使用されます。
          </p>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">セクション構成（H{value.topLevel}）</label>
            <div className="text-xs text-muted-foreground">小見出しは各大見出しごとに追加できます</div>
          </div>

          <div className="space-y-3">
            {sections.map((section, index) => {
              const subsections = ensureSubsections(section);
              return (
                <div key={index} className="space-y-4 rounded border bg-white p-3 shadow-sm">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start">
                    <div className="flex items-start gap-3 md:flex-1">
                      <Badge variant="outline" className="mt-1 shrink-0">
                        H{value.topLevel}
                      </Badge>
                      <div className="flex-1 space-y-2">
                        <Input
                          value={section.heading}
                          onChange={(e) => updateSection(index, { heading: e.target.value })}
                          placeholder={`大見出し ${index + 1} のタイトル`}
                          disabled={disabled}
                        />
                        <Textarea
                          value={section.description ?? ""}
                          onChange={(e) => updateSection(index, { description: e.target.value })}
                          placeholder="この見出しで伝える要点や補足（任意）"
                          disabled={disabled}
                          className="min-h-[70px]"
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 md:flex-col md:items-end">
                      <Input
                        type="number"
                        className="w-28"
                        value={section.estimated_chars ?? 300}
                        onChange={(e) =>
                          updateSection(index, {
                            estimated_chars: Math.max(0, Number(e.target.value) || 0),
                          })
                        }
                        placeholder="文字数"
                        min={0}
                        disabled={disabled}
                      />
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => moveSection(index, -1)}
                          disabled={disabled || index === 0}
                        >
                          <ArrowUp className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => moveSection(index, 1)}
                          disabled={disabled || index === sections.length - 1}
                        >
                          <ArrowDown className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="destructive"
                          size="icon"
                          onClick={() => removeSection(index)}
                          disabled={disabled}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {subsections.map((subsection, subIndex) => {
                      const levelValue = `h${subsection.level}`;
                      return (
                        <div
                          key={subIndex}
                          className="space-y-3 rounded border border-dashed border-blue-200 bg-blue-50/70 p-3"
                        >
                          <div className="flex flex-col gap-3 md:flex-row md:items-start">
                            <div className="flex items-start gap-2 md:flex-1">
                              <Badge variant="outline" className="mt-1 shrink-0 bg-white">
                                H{subsection.level}
                              </Badge>
                              <div className="flex-1 space-y-2">
                                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                                  <Select
                                    value={levelValue}
                                    onValueChange={(val) =>
                                      updateSubsection(index, subIndex, {
                                        level: Number(val.replace("h", "")),
                                      })
                                    }
                                    disabled={disabled}
                                  >
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {childLevelOptions.map((lvl) => (
                                        <SelectItem key={lvl} value={`h${lvl}`}>
                                          H{lvl}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Input
                                    type="number"
                                    value={subsection.estimated_chars ?? 200}
                                    onChange={(e) =>
                                      updateSubsection(index, subIndex, {
                                        estimated_chars: Math.max(0, Number(e.target.value) || 0),
                                      })
                                    }
                                    placeholder="目安文字数"
                                    min={0}
                                    disabled={disabled}
                                  />
                                </div>
                                <Input
                                  value={subsection.heading}
                                  onChange={(e) =>
                                    updateSubsection(index, subIndex, { heading: e.target.value })
                                  }
                                  placeholder="小見出しのタイトル"
                                  disabled={disabled}
                                />
                                <Textarea
                                  value={subsection.description ?? ""}
                                  onChange={(e) =>
                                    updateSubsection(index, subIndex, { description: e.target.value })
                                  }
                                  placeholder="この小見出しで触れる内容（任意）"
                                  disabled={disabled}
                                  className="min-h-[60px]"
                                />
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => moveSubsection(index, subIndex, -1)}
                                disabled={disabled || subIndex === 0}
                              >
                                <ArrowUp className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => moveSubsection(index, subIndex, 1)}
                                disabled={disabled || subIndex === subsections.length - 1}
                              >
                                <ArrowDown className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="destructive"
                                size="icon"
                                onClick={() => removeSubsection(index, subIndex)}
                                disabled={disabled}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => addSubsection(index)}
                      disabled={disabled}
                      className="flex items-center gap-2"
                    >
                      <Plus className="h-4 w-4" />
                      小見出しを追加
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>

          <div>
            <Button
              type="button"
              variant="secondary"
              onClick={addSection}
              disabled={disabled}
              className="flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              大見出しを追加
            </Button>
          </div>
        </div>

        {touched && errors.length > 0 && (
          <div className="space-y-1 text-sm text-red-600">
            {errors.map((error, idx) => (
              <div key={idx}>• {error}</div>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button variant="outline" onClick={onCancel} className="flex items-center gap-1" disabled={disabled}>
              <XCircle className="h-4 w-4" />
              キャンセル
            </Button>
          )}
          <Button
            onClick={onSave}
            disabled={disabled || errors.length > 0}
            className="flex items-center gap-1"
          >
            <Save className="h-4 w-4" />
            {getOutlineApprovalMessage()}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
