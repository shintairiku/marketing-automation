"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Edit3, Plus, Save, Trash2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type { EditableOutline, MainSection } from "../../types/outline";

type Props = {
  value: EditableOutline;
  onChange: (next: EditableOutline) => void;
  onCancel?: () => void;
  onSaveAndStart: (edited: {
    title: string;
    suggested_tone?: string;
    sections: Array<{
      heading: string;
      estimated_chars: number;
      subsections: Array<{ heading: string; estimated_chars?: number }>;
    }>;
  }) => void;
  disabled?: boolean;
};

export default function MainSectionEditor({ value, onChange, onCancel, onSaveAndStart, disabled }: Props) {
  const [touched, setTouched] = useState(false);

  const sections = useMemo(() => value.sections || [], [value.sections]);

  const errors = useMemo(() => {
    const errs: string[] = [];
    if (!value.title || !value.title.trim()) errs.push("タイトルを入力してください");
    if (!sections.length) errs.push("少なくとも1つのセクションが必要です");
    if (sections.some((s) => !s.heading || !s.heading.trim())) errs.push("空の見出しがあります");
    return errs;
  }, [value.title, sections]);

  const updateSection = (index: number, patch: Partial<MainSection>) => {
    setTouched(true);
    const next: EditableOutline = {
      ...value,
      sections: sections.map((s, i) => (i === index ? { ...s, ...patch } : s)),
    };
    onChange(next);
  };

  const addSection = () => {
    setTouched(true);
    const next: EditableOutline = {
      ...value,
      sections: [...sections, { heading: "", estimated_chars: 300 }],
    };
    onChange(next);
  };

  const removeSection = (index: number) => {
    setTouched(true);
    const next: EditableOutline = {
      ...value,
      sections: sections.filter((_, i) => i !== index),
    };
    onChange(next);
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

  const onSave = () => {
    // Fill defaults, strip empty headings
    const cleaned = sections
      .filter((s) => s.heading && s.heading.trim())
      .map((s) => ({
        heading: s.heading.trim(),
        estimated_chars: s.estimated_chars && s.estimated_chars > 0 ? s.estimated_chars : 300,
        subsections: (s.__subsections || []).filter(Boolean).map((h) => ({ heading: h })),
      }));

    onSaveAndStart({
      title: value.title,
      suggested_tone: value.suggested_tone || "",
      sections: cleaned,
    });
  };

  return (
    <Card className="border border-blue-200 bg-blue-50/40">
      <CardContent className="p-4 space-y-4">
        <div>
          <h4 className="font-medium mb-2 flex items-center gap-2">
            <Edit3 className="w-4 h-4" />
            アウトライン（メインセクションのみ）
          </h4>
          <div className="grid grid-cols-1 gap-2">
            <div>
              <label className="text-sm font-medium block mb-1">記事タイトル</label>
              <Input
                value={value.title || ""}
                onChange={(e) => onChange({ ...value, title: e.target.value })}
                placeholder="記事のタイトルを入力..."
                disabled={disabled}
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">推奨トーン</label>
              <Input
                value={value.suggested_tone || ""}
                onChange={(e) => onChange({ ...value, suggested_tone: e.target.value })}
                placeholder="例：丁寧で読みやすい解説調"
                disabled={disabled}
              />
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium">セクション構成（H2相当）</label>
            <div className="text-xs text-muted-foreground">サブセクションは非表示のまま保持されます</div>
          </div>

          <div className="space-y-2">
            {sections.map((s, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-white rounded border">
                <Badge variant="outline" className="shrink-0">
                  {i + 1}
                </Badge>
                <Input
                  className="flex-1"
                  value={s.heading}
                  onChange={(e) => updateSection(i, { heading: e.target.value })}
                  placeholder={`セクション ${i + 1} の見出し`}
                  disabled={disabled}
                />
                <Input
                  type="number"
                  className="w-28"
                  value={s.estimated_chars ?? 300}
                  onChange={(e) => updateSection(i, { estimated_chars: Math.max(0, Number(e.target.value) || 0) })}
                  placeholder="文字数"
                  min={0}
                  disabled={disabled}
                />
                <div className="flex items-center gap-1">
                  <Button variant="outline" size="icon" onClick={() => moveSection(i, -1)} disabled={i === 0 || disabled}>
                    <ArrowUp className="w-4 h-4" />
                  </Button>
                  <Button variant="outline" size="icon" onClick={() => moveSection(i, 1)} disabled={i === sections.length - 1 || disabled}>
                    <ArrowDown className="w-4 h-4" />
                  </Button>
                  <Button variant="destructive" size="icon" onClick={() => removeSection(i)} disabled={disabled}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3">
            <Button type="button" variant="secondary" onClick={addSection} disabled={disabled} className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              セクションを追加
            </Button>
          </div>
        </div>

        {touched && errors.length > 0 && (
          <div className="text-sm text-red-600">
            {errors.map((e, idx) => (
              <div key={idx}>• {e}</div>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button variant="outline" onClick={onCancel} className="flex items-center gap-1" disabled={disabled}>
              <XCircle className="w-4 h-4" />
              キャンセル
            </Button>
          )}
          <Button onClick={onSave} disabled={disabled || errors.length > 0} className="flex items-center gap-1">
            <Save className="w-4 h-4" />
            この内容で執筆開始
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

