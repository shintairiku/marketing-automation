import { test, expect } from '@playwright/test';

test.describe.serial('会社情報管理機能のテスト', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test('新規会社を登録できること', async ({ page }) => {
    // <nav>タグ（ナビゲーションバー）にホバーして、メニューを展開します
    await page.locator('nav').first().hover();    

    // 会社情報設定ボタンをクリック
    await page.getByRole('link', { name: '会社情報設定' }).click();
    await page.getByRole('button', { name: '会社情報を追加'}).click();

    // フォームに情報を入力
    await page.getByLabel('会社名').fill('テスト株式会社');
    await page.getByLabel('企業HP URL').fill('https://example.com');

    await page.getByLabel('事業内容').fill('札幌市および近郊エリアを対象に、注文住宅の設計・施工・アフターサポートまでを一貫して提供する工務店です。 特に「子育て世代」のご家族に焦点を当て、自然素材（無垢材、漆喰、珪藻土など）を標準仕様とした健康住宅を専門としています。冬の厳しい札幌の気候に対応するため、国の基準を大幅に上回る高気密・高断熱性能を担保しつつ、木の温もりを感じられる安全な住まいづくりをサービスの中核としています。');

    // 画像で必須項目になっている項目を入力します
    await page.getByLabel('USP（企業の強み・差別化ポイント）').fill('100%自然素材へのこだわり: 床や柱などの構造材だけでなく、壁紙の接着剤や塗料、目に見えない断熱材（セルロースファイバー等）に至るまで、化学物質を徹底的に排除した素材のみを使用します。これにより、シックハウス症候群やアレルギーの不安がない、赤ちゃんがハイハイしても安全な空気環境を提供します。 「子育て」を軸にした設計提案: 「子供の成長」と「家事の効率化」を両立する動線を最優先に設計します。例えば、「リビング学習」を前提としたスタディカウンターの設置や、キッチンから家全体が見渡せる間取り、泥んこになって帰ってきても玄関から直接お風呂場に行ける「どろんこ動線」など、子育て経験に基づいた実用的な提案を強みとしています。');
    
    await page.getByLabel('ターゲット・ペルソナ').fill('夫婦');

    // 登録ボタンをクリック
    await page.getByRole('button', { name: '作成' }).click();

    // 登録した会社が一覧に表示されることを確認
    await expect(page.getByText('テスト株式会社').nth(2)).toBeVisible();
  });

  test('必須項目が未入力の場合にエラーが表示されること', async ({ page }) => {
    await page.locator('nav').first().hover();    
    await page.getByRole('link', { name: '会社情報設定' }).click();
    await page.getByRole('button', { name: '会社情報を追加'}).click();

    // 何も入力せずに登録ボタンをクリック
    await page.getByRole('button', { name: '作成' }).click();

    // エラーメッセージが表示されることを確認
    await expect(page.locator('text=必須項目をすべて入力してください')).toBeVisible();
  });

  test('会社情報を編集できること', async ({ page }) => {
    await page.locator('nav').first().hover();
    await page.getByRole('link', { name: '会社情報設定' }).click();
                            
    // デフォルトを除いた2段目の会社の編集の鉛筆ボタンが/^$/となっているので注意（debugで検証）
    await page.getByRole('button').filter({ hasText: /^$/}).nth(4).click();

    await page.getByLabel('会社名').fill('テスト株式会社（編集済み）');

    await page.getByRole('button', { name: '更新' }).click();
    
    await expect(page.getByRole('button', { name: '更新' })).toBeHidden();

    await expect(page.getByText('テスト株式会社（編集済み）').first()).toBeVisible();
  });

  test('会社を削除できること', async ({ page }) => {
    // 削除確認ダイアログ（「本当に削除しますか？」）を自動で承認する
    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    await page.locator('nav').first().hover();
    await page.getByRole('link', { name: '会社情報設定' }).click();
                            
    // 削除のゴミ箱ボタンが/^$/となっているので注意（debugで検証）
    await page.getByRole('button').filter({ hasText: /^$/}).nth(5).click();

    // 一覧からカードが消えたこと（非表示になったこと）を確認
    await expect(page.getByText('テスト株式会社（編集済み）').first()).toBeHidden();
  });
});