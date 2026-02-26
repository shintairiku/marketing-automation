# -*- coding: utf-8 -*-
"""
Blog Memory seed CSV generator

Creates:
- blog_memory_meta_seed.csv
- blog_memory_items_seed.csv

Both files are placed under test/blog_memory_seed/.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
META_CSV = OUT_DIR / "blog_memory_meta_seed.csv"
ITEMS_CSV = OUT_DIR / "blog_memory_items_seed.csv"
TOTAL_ARTICLES = 120


TEMPLATES = [
    {
        "kind": "student",
        "topic": "高専生の勉強方法",
        "audiences": ["高専1-2年生", "高専3年生", "高専4-5年生", "編入志望者"],
        "goals": ["最短で成果を出す", "継続できる仕組みを作る", "再現性を高める"],
    },
    {
        "kind": "event",
        "topic": "生成AI活用セミナー告知",
        "audiences": ["高校生と保護者", "既存顧客", "見込み顧客", "地域参加者"],
        "goals": ["参加率を上げる", "イベント概要を明確にする", "申込導線を改善する"],
    },
    {
        "kind": "employee",
        "topic": "社員紹介インタビュー",
        "audiences": ["採用候補者", "既存顧客", "新規取引先", "社内メンバー"],
        "goals": ["人柄を伝える", "専門性を伝える", "組織理解を深める"],
    },
    {
        "kind": "case",
        "topic": "導入事例レポート",
        "audiences": ["見込み顧客", "既存顧客", "業界関係者"],
        "goals": ["成果を具体化する", "再現手順を示す", "信頼を高める"],
    },
    {
        "kind": "product",
        "topic": "機能アップデート案内",
        "audiences": ["既存ユーザー", "管理者ユーザー", "サポート担当者"],
        "goals": ["変更点を明確にする", "移行の不安を減らす", "利用率を上げる"],
    },
    {
        "kind": "culture",
        "topic": "社内カルチャー紹介",
        "audiences": ["採用候補者", "新入社員", "社外パートナー"],
        "goals": ["価値観を伝える", "働くイメージを持たせる", "共感を増やす"],
    },
    {
        "kind": "webinar",
        "topic": "ウェビナー開催案内",
        "audiences": ["マーケ担当者", "営業担当者", "プロダクト担当者"],
        "goals": ["集客を強化する", "内容を分かりやすくする", "申込率を上げる"],
    },
    {
        "kind": "partner",
        "topic": "パートナー連携発表",
        "audiences": ["既存顧客", "業界メディア", "提携候補企業"],
        "goals": ["提携価値を伝える", "期待効果を示す", "信頼感を高める"],
    },
    {
        "kind": "csr",
        "topic": "地域イベント参加レポート",
        "audiences": ["地域住民", "自治体関係者", "社員家族"],
        "goals": ["活動内容を可視化する", "社会的意義を伝える", "継続参加につなげる"],
    },
    {
        "kind": "onboarding",
        "topic": "新入社員オンボーディング紹介",
        "audiences": ["新入社員", "配属先マネージャー", "人事担当者"],
        "goals": ["定着率を上げる", "立ち上がりを早める", "期待役割を明確化する"],
    },
]

TOOLS = [
    "web_search",
    "wp_get_recent_posts",
    "wp_get_post_types",
    "wp_get_categories",
]


def build_meta_row(i: int) -> dict[str, str]:
    tpl = TEMPLATES[(i - 1) % len(TEMPLATES)]
    audience = tpl["audiences"][(i - 1) % len(tpl["audiences"])]
    goal = tpl["goals"][(i - 1) % len(tpl["goals"])]
    topic = tpl["topic"]
    kind = tpl["kind"]

    if kind == "event":
        title = f"{topic}｜開催案内 {i:03d}"
        short_summary = (
            f"{audience}向けに、日時・会場・参加メリット・申込方法を整理。"
            f"{goal}観点で訴求ポイントを明確化する。"
        )
        user_prompt = (
            f"{audience}向けのイベント告知記事を作りたいです。"
            f"テーマは「{topic}」。{goal}を重視してください。"
        )
    elif kind == "employee":
        title = f"{topic}｜担当者インタビュー {i:03d}"
        short_summary = (
            f"{audience}向けに、担当領域・仕事の工夫・今後の挑戦を紹介。"
            f"{goal}につながる構成にする。"
        )
        user_prompt = (
            f"{audience}向けに社員紹介記事を書きたいです。"
            f"「{topic}」として、具体的なエピソードを入れてください。"
        )
    elif kind == "case":
        title = f"{topic}｜活用事例 {i:03d}"
        short_summary = (
            "導入前課題・実施内容・成果指標を時系列で整理。"
            f"{goal}にフォーカスして再現可能なポイントを示す。"
        )
        user_prompt = (
            f"{audience}向けに「{topic}」の記事を作成したいです。"
            "ビフォーアフターと数値成果をわかりやすく入れてください。"
        )
    elif kind in {"product", "onboarding"}:
        title = f"{topic}ガイド {i:03d}"
        short_summary = (
            f"{audience}向けに、変更点・手順・注意点を簡潔に解説。"
            f"{goal}に必要なチェックリストを含める。"
        )
        user_prompt = (
            f"{audience}向けに「{topic}」の説明記事を作りたいです。"
            "手順を箇条書きで明確にしてください。"
        )
    else:
        title = f"{topic} 実践ガイド {i:03d}"
        short_summary = (
            f"{audience}向けに、{goal}ための手順を3ステップで整理。"
            "準備・実行・振り返りまで具体例付きで解説する。"
        )
        user_prompt = (
            f"{audience}に向けて「{topic}」の記事を書きたいです。"
            f"{goal}観点で、すぐ実行できる内容にしてください。"
        )

    reference_url = f"https://example.com/blog/reference-{i:03d}"
    return {
        "seed_no": str(i),
        "title": title,
        "short_summary": short_summary,
        "user_prompt": user_prompt,
        "reference_url": reference_url,
        "topic": topic,
        "audience": audience,
    }


def build_tool_result_content(meta_row: dict[str, str], i: int) -> str:
    tool_name = TOOLS[(i - 1) % len(TOOLS)]
    now_utc = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=i)
    payload = {
        "tool_name": tool_name,
        "status": "ok",
        "input": {
            "process_id": "__PROCESS_ID__",
            "q": f"{meta_row['topic']} {meta_row['audience']} 実例",
            "max_results": 5,
        },
        "output": {
            "items": [
                {
                    "title": f"{meta_row['topic']} の基本",
                    "url": f"https://example.com/source/{i:03d}/1",
                    "snippet": "要点整理と学習手順を簡潔に説明している。"
                },
                {
                    "title": f"{meta_row['topic']} の失敗例",
                    "url": f"https://example.com/source/{i:03d}/2",
                    "snippet": "よくある失敗と対策をケース別に解説している。"
                },
            ],
        },
        "ts": now_utc.isoformat().replace("+00:00", "Z"),
    }
    return json.dumps(payload, ensure_ascii=False)


def build_item_rows(meta_row: dict[str, str], i: int) -> list[dict[str, str]]:
    kind = TEMPLATES[(i - 1) % len(TEMPLATES)]["kind"]
    user_input = meta_row["user_prompt"]
    if kind == "event":
        source = (
            f"参考情報: {meta_row['reference_url']} / "
            f"{meta_row['topic']} の開催概要、参加特典、申込導線を確認。"
        )
        system_note = (
            f"読者={meta_row['audience']}。冒頭で開催概要を提示し、"
            "日時・場所・対象・申込方法を表形式か箇条書きで明記。"
        )
        assistant_output = (
            "導入: 参加者の課題に共感。"
            "本編: 開催概要・タイムテーブル・登壇内容・参加メリット。"
            "終盤: 申込ボタンと締切を明示。"
        )
        final_summary = (
            f"{meta_row['title']} の要点: 誰向けに何が得られるイベントかを明確にし、"
            "申し込みまでの行動を迷わせない構成にした。"
        )
        qa_user_input = (
            "Q(q1): 開催日時と会場を教えてください。\n"
            f"A: 2026-03-{(i % 20) + 1:02d} 19:00 / {'オンライン' if i % 2 else '東京会場'}\n\n"
            "Q(q2): 告知画像はありますか？\n"
            "InputType: image_upload\n"
            f"A: uploaded:event-banner-{i:03d}.webp"
        )
    elif kind == "employee":
        source = (
            f"参考情報: {meta_row['reference_url']} / "
            "担当業務、経歴、価値観、プロジェクト実績を確認。"
        )
        system_note = (
            f"読者={meta_row['audience']}。人物像が伝わるように、"
            "背景・現在・今後の挑戦の順で構成する。"
        )
        assistant_output = (
            "導入: 配属背景を紹介。"
            "本編: 担当業務・成功体験・チームでの工夫。"
            "終盤: 読者へのメッセージと採用/問い合わせ導線。"
        )
        final_summary = (
            f"{meta_row['title']} の要点: 社員の人柄と専門性を具体エピソードで示し、"
            "組織理解につながる記事にした。"
        )
        qa_user_input = (
            "Q(q1): 担当領域と最近の成果を教えてください。\n"
            f"A: SaaS導入支援。直近四半期で解約率を{(i % 5) + 1}%改善しました。\n\n"
            "Q(q2): プロフィール写真はありますか？\n"
            "InputType: image_upload\n"
            f"A: uploaded:employee-{i:03d}.webp"
        )
    else:
        source = (
            f"参考情報: {meta_row['reference_url']} / "
            f"{meta_row['topic']} の基礎と実践例を確認。"
        )
        system_note = (
            f"読者={meta_row['audience']}。結論先出し・箇条書き中心・"
            "行動チェックリスト付きで構成する。"
        )
        assistant_output = (
            f"導入: {meta_row['topic']}の課題を明確化。"
            "本編: 3ステップ（準備/実行/振り返り）。"
            "終盤: 1週間の実践計画テンプレートを提示。"
        )
        final_summary = (
            f"{meta_row['title']} の要点: 学習目的を定義し、"
            "小さな実行単位に分解して継続することで成果につなげる。"
        )
        qa_user_input = (
            "Q(q1): 開催形式はオンラインですか？\n"
            f"A: {'オンライン開催です' if i % 2 == 1 else 'オフライン開催です'}\n\n"
            "Q(q2): 告知画像はありますか？\n"
            "InputType: image_upload\n"
            f"A: uploaded:seminar-{i:03d}.webp"
        )

    tool_result = build_tool_result_content(meta_row, i)

    rows = []
    for role, content in [
        ("user_input", user_input),
        ("user_input", qa_user_input),
        ("source", source),
        ("system_note", system_note),
        ("assistant_output", assistant_output),
        ("final_summary", final_summary),
        ("tool_result", tool_result),
    ]:
        rows.append(
            {
                "seed_no": str(i),
                "role": role,
                "content": content,
            }
        )
    return rows


def main() -> None:
    meta_rows: list[dict[str, str]] = []
    item_rows: list[dict[str, str]] = []

    for i in range(1, TOTAL_ARTICLES + 1):
        meta_row = build_meta_row(i)
        meta_rows.append(meta_row)
        item_rows.extend(build_item_rows(meta_row, i))

    with META_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed_no",
                "title",
                "short_summary",
                "user_prompt",
                "reference_url",
                "topic",
                "audience",
            ],
        )
        writer.writeheader()
        writer.writerows(meta_rows)

    with ITEMS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed_no",
                "role",
                "content",
            ],
        )
        writer.writeheader()
        writer.writerows(item_rows)

    print(f"generated: {META_CSV}")
    print(f"generated: {ITEMS_CSV}")
    print(f"meta rows: {len(meta_rows)}")
    print(f"item rows: {len(item_rows)}")


if __name__ == "__main__":
    main()
