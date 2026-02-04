# Agent-15: 入力バリデーション調査結果

調査完了: 2026-02-04 (検証完了)

## 調査対象ファイル
- backend/app/domains/seo_article/schemas.py (525行)
- backend/app/domains/admin/schemas.py (196行)
- backend/app/domains/company/schemas.py (73行)
- backend/app/domains/image_generation/schemas.py (3行)
- backend/app/domains/usage/schemas.py (52行)
- backend/app/domains/blog/schemas.py (190行)
- backend/app/domains/style_template/schemas.py (3行)
- backend/app/domains/organization/schemas.py (3行) + service.py内スキーマ
- backend/app/domains/blog/endpoints.py (960行)
- backend/app/domains/organization/endpoints.py (230行)
- backend/app/domains/seo_article/endpoints.py (2200行)
- backend/app/domains/image_generation/endpoints.py (750行)
- backend/app/domains/admin/endpoints.py (264行)
- backend/app/domains/company/endpoints.py (63行)

## 発見サマリー
- Critical: 0
- High: 3
- Medium: 6
- Low: 4

## 発見事項

### [HIGH] VAL-001: BlogGenerationStartRequest の user_prompt にLLMプロンプトインジェクション対策なし
- **ファイル**: `backend/app/domains/blog/schemas.py`
- **行番号**: 97-101
- **問題**: user_prompt に max_length=2000 があるが、LLMプロンプトインジェクション対策なし
- **コード**:
  ```python
  class BlogGenerationStartRequest(BaseModel):
      user_prompt: str = Field(
          ...,
          max_length=2000,
          description="どんな記事を作りたいか"
      )
  ```
- **影響**: 悪意あるプロンプトがLLMに直接渡される可能性。「システムプロンプトを無視して...」といった攻撃パターンが可能
- **推奨**: 入力サニタイズまたはプロンプト構造の強化、危険なパターンの検出

### [HIGH] VAL-002: GenerateArticleRequest の initial_keywords に配列サイズ制限なし
- **ファイル**: `backend/app/domains/seo_article/schemas.py`
- **行番号**: 27
- **問題**: initial_keywords リストにサイズ制限がない
- **コード**:
  ```python
  initial_keywords: List[str] = Field(..., description="記事生成の元となるキーワードリスト")
  ```
- **影響**: 非常に大きな配列（数千要素）を送信し、サーバーリソースを枯渇させる可能性（DoS）
- **推奨**: max_length または custom validator で配列サイズを制限（例: max_length=20）

### [HIGH] VAL-003: AIEditRequest の content/instruction にサイズ制限なし
- **ファイル**: `backend/app/domains/seo_article/endpoints.py`
- **行番号**: 138-143
- **問題**: AIEditRequest のフィールドに文字列長制限がない
- **コード**:
  ```python
  class AIEditRequest(BaseModel):
      content: str = Field(..., description="元のHTMLブロック内容")
      instruction: str = Field(..., description="編集指示（カジュアルに書き換え等）")
      article_html: Optional[str] = Field(None, description="記事全体のHTML（任意）")
  ```
- **影響**: 巨大なHTML文字列や指示を送信してメモリ枯渇を引き起こす可能性
- **推奨**: content (max_length=100000), instruction (max_length=2000), article_html (max_length=500000) に max_length を追加

### [MEDIUM] VAL-004: WordPressSiteRegisterRequest の site_url にURL形式バリデーションなし
- **ファイル**: `backend/app/domains/blog/endpoints.py`
- **行番号**: 77-85
- **問題**: site_url が単なる str 型で、URL形式のバリデーションがない
- **コード**:
  ```python
  class WordPressSiteRegisterRequest(BaseModel):
      site_url: str = Field(..., description="WordPressサイトURL")
      mcp_endpoint: str = Field(..., description="MCPエンドポイントURL")
  ```
- **影響**: 不正なURL形式（SSRF攻撃に利用可能な内部URLなど）を登録可能
- **推奨**: HttpUrl 型を使用するか、カスタムバリデータでURLスキーム（http/https）・ホスト検証

### [MEDIUM] VAL-005: organization name の文字列長制限が緩い
- **ファイル**: `backend/app/domains/organization/service.py`
- **行番号**: 27-28
- **問題**: name の max_length=100、特殊文字の制限なし
- **コード**:
  ```python
  class OrganizationCreate(BaseModel):
      name: str = Field(..., min_length=1, max_length=100)
  ```
- **影響**: UI破壊やログ汚染の可能性。改行や特殊文字によるUI表示崩れ
- **推奨**: 50文字程度に短縮、regex パターンで英数字・日本語・スペースのみ許可

### [MEDIUM] VAL-006: image_settings が Dict[Any] で型検証なし
- **ファイル**: `backend/app/domains/seo_article/schemas.py`
- **行番号**: 40
- **問題**: image_settings が Optional[dict] で内部構造のバリデーションなし
- **コード**:
  ```python
  image_settings: Optional[dict] = Field(None, description="画像生成設定")
  ```
- **影響**: 任意のネストされたデータを送信可能、深いネストによるスタックオーバーフローやJSON爆弾の可能性
- **推奨**: 専用の ImageSettings Pydantic モデルを定義

### [MEDIUM] VAL-007: blog_context が Dict[str, Any] で検証なし
- **ファイル**: `backend/app/domains/blog/schemas.py`
- **行番号**: 68
- **問題**: blog_context が Dict[str, Any] で任意データを保存可能
- **コード**:
  ```python
  blog_context: Dict[str, Any] = Field(default_factory=dict)
  ```
- **影響**: 巨大なJSONオブジェクトをDBに保存してストレージを枯渇させる可能性
- **推奨**: blog_context のサイズ制限（JSONシリアライズ後のバイト数制限）またはスキーマ定義

### [MEDIUM] VAL-008: ファイルアップロードのサイズ・タイプ検証が不完全
- **ファイル**: `backend/app/domains/blog/endpoints.py`
- **行番号**: 620-670
- **問題**: upload_image エンドポイントでファイルサイズの事前チェックがない
- **コード**:
  ```python
  async def upload_image(...):
      content = await file.read()  # ファイル全体を読み込んでからサイズチェック
  ```
- **影響**: 巨大なファイルアップロードでメモリ枯渇
- **推奨**: UploadFile のサイズを事前にチェック（MAX_FILE_SIZE = 10MB 等）、Content-Type 検証を強化

### [MEDIUM] VAL-009: process_id/article_id のUUID形式バリデーションなし
- **ファイル**: `backend/app/domains/blog/endpoints.py`, `seo_article/endpoints.py`
- **問題**: パスパラメータの process_id, article_id が単なる str 型
- **影響**: 不正な形式の ID でDBクエリを実行（パフォーマンス影響、潜在的なSQLインジェクション経路）
- **推奨**: UUID 型バリデーションを追加（FastAPI Path パラメータで UUID 型を指定）

### [LOW] VAL-010: company schemas に website_url の HttpUrl 検証あり（良好）
- **ファイル**: `backend/app/domains/company/schemas.py`
- **行番号**: 22
- **問題**: なし - HttpUrl 型が使用されている（これは良い実装）
- **コード**:
  ```python
  website_url: HttpUrl = Field(..., description="企業HP URL")
  ```
- **備考**: 他のURL フィールドも同様にすべき

### [LOW] VAL-011: image_generation/schemas.py がほぼ空
- **ファイル**: `backend/app/domains/image_generation/schemas.py`
- **行番号**: 1-3
- **問題**: スキーマが endpoints.py 内に定義されており、一貫性がない
- **影響**: コード整理の問題。セキュリティ上の直接的影響は低い
- **推奨**: スキーマを schemas.py に移動して一元管理

### [LOW] VAL-012: style_template/schemas.py, organization/schemas.py が空
- **ファイル**: `backend/app/domains/style_template/schemas.py`, `organization/schemas.py`
- **問題**: スキーマがそれぞれのドメインファイルではなく service.py や endpoints.py に散在
- **影響**: メンテナンス性の低下
- **推奨**: スキーマを専用ファイルに統合

### [LOW] VAL-013: GeneratedArticleStateRead 等のスタブクラス
- **ファイル**: `backend/app/domains/seo_article/endpoints.py`
- **行番号**: 66-70
- **問題**: スタブ実装が残っている
- **コード**:
  ```python
  class GeneratedArticleStateRead(BaseModel):
      status: str = "stub"
  ```
- **影響**: 未完成の機能がプロダクションに存在
- **推奨**: 実装完了またはエンドポイント無効化

## 良い実装

以下の実装は適切にセキュリティを考慮している:

1. **CompanyInfoBase** に max_length が適切に設定されている（name:200, description:2000, usp:1000 など）
2. **OrganizationCreate/Update** に min_length, max_length が設定されている
3. **BlogGenerationStartRequest** に user_prompt の max_length が設定されている
4. **company schemas** で HttpUrl 型が使用されている
5. **GenerateArticleRequest** の num_* フィールドに ge=1 制約がある
6. **Field** の examples が提供されている（ドキュメント目的）
7. **InvitationCreate** で EmailStr が使用されている（メール形式バリデーション）

## 推奨修正優先順位

### 高優先度（High）
1. すべての List[str] フィールドに max_items 制約を追加
2. LLMに渡される入力（user_prompt, instruction）にサニタイズ処理を追加
3. AIEditRequest に max_length 制約を追加

### 中優先度（Medium）
4. URL フィールドは HttpUrl 型に統一（特にWordPress関連）
5. Dict[str, Any] フィールドには専用スキーマまたはサイズ制限を定義
6. ファイルアップロードに事前サイズチェックを追加（MAX_FILE_SIZE 定数を設定）
7. UUID パラメータに型バリデーションを追加

### 低優先度（Low）
8. スキーマ定義を各ドメインの schemas.py に集約
9. スタブクラスの整理

## 追加の推奨事項

### LLMプロンプトインジェクション対策
```python
def sanitize_llm_input(text: str) -> str:
    """LLMプロンプトインジェクション対策のための入力サニタイズ"""
    # システムプロンプト上書き試行のパターン
    dangerous_patterns = [
        r"ignore\s+(all\s+)?(previous|above)\s+instructions",
        r"disregard\s+(all\s+)?(previous|above)\s+instructions",
        r"system\s*:\s*",
        r"<\|system\|>",
        r"\[INST\]",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Invalid input detected")
    return text
```

### ファイルアップロードサイズチェック
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file_size(file: UploadFile):
    # ファイルサイズを事前チェック
    file.file.seek(0, 2)  # End of file
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
```
