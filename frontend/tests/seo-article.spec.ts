import { test, expect } from '@playwright/test';

test.describe.serial('SEO記事生成機能のテスト', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test.skip('新規SEO記事を生成できること', async ({ page }) => {
    // <nav>タグ（ナビゲーションバー）にホバーして、メニューを展開します
    await page.locator('nav').first().hover();    

    // SEO記事作成・管理ボタンをクリック
    await page.getByRole('link', { name: 'SEO記事作成・管理' }).click();

    await expect(page.getByRole('heading', { name: '新規SEO記事作成' })).toBeVisible();

    // フォームに情報を入力
    const keywordInput = page.getByPlaceholder(/Webマーケティング/);
    
    // 1つ目のキーワード
    await keywordInput.fill('札幌');
    await keywordInput.press('Enter');
    // 2つ目のキーワード
    await keywordInput.fill('注文住宅');
    await keywordInput.press('Enter');
    // 3つ目のキーワード
    await keywordInput.fill('自然素材');
    await keywordInput.press('Enter');
    // 4つ目のキーワード
    await keywordInput.fill('子育て');
    await keywordInput.press('Enter'); 

    // 「画像生成・挿入機能」のトグルをONにする
    await page.getByRole('switch').first().click();
     // 「高度アウトラインモード」のトグルをONにする
    await page.getByRole('switch').nth(1).click();

    const styleCombo = page.getByRole('combobox').filter({hasText:'スタイルテンプレートを選択'});
    await styleCombo.click()
    await page.getByRole('option', { name: 'デフォルトスタイル' }).click();    
    

    const ageCombo = page.getByRole('combobox').filter({hasText:'年代層を選択'});
    await ageCombo.click();
    await page.getByRole('option', { name: '30代' }).click();

    const pelsonaCombo = page.getByRole('combobox').filter({hasText:'事前設定済みのペルソナ（推奨）'})
    await pelsonaCombo.click();
    await page.getByRole('option', { name: '事前設定済みのペルソナ（推奨）' }).click();

    // 1. スライダーの要素を取得
    const slider = page.getByRole('slider')
    // 2. スライダーにフォーカスを当てる
    await slider.click();
    // 3. 'Home'キーを押して値を最小値にリセットする
    await slider.press('Home');
    // 4. 'ArrowRight'キーを2回押し、値を '3' にする (1 -> 2 -> 3)
    await slider.press('ArrowRight');
    await slider.press('ArrowRight');

    // 記事生成を開始
    await page.getByRole('button', { name: '記事生成を開始' }).click();

    // ローディングモーダルが表示されることを確認
    await expect(page.getByText('記事生成プロセスを開始しています...')).toBeVisible();

    // 生成プロセスページにリダイレクトされることを確認
    await page.waitForURL(/\/seo\/generate\/new-article\/[^/]+/, { timeout: 10000 });
    
    // 生成プロセスページで「記事生成プロセス」の見出しが表示されることを確認
    await expect(page.getByRole('heading', { name: '記事生成プロセス' })).toBeVisible({ timeout: 15000 });
  });

  test('SEOキーワードが未入力の場合にボタンが無効化されること', async ({ page }) => {
    await page.locator('nav').first().hover();
    await page.getByRole('link', { name: 'SEO記事作成・管理' }).click();

    await expect(page.getByRole('heading', { name: '新規SEO記事作成' })).toBeVisible();

    // 何も入力していない状態で、ボタンが無効化されていることを確認
    const startButton = page.getByRole('button', { name: '記事生成を開始' });
    await expect(startButton).toBeDisabled();
  });

  test('ターゲット年代層が未選択の場合にボタンが無効化されること', async ({ page }) => {
    await page.locator('nav').first().hover();
    await page.getByRole('link', { name: 'SEO記事作成・管理' }).click();

    await expect(page.getByRole('heading', { name: '新規SEO記事作成' })).toBeVisible();

    // キーワードのみ入力
    const keywordInput = page.getByPlaceholder(/Webマーケティング/);
    await keywordInput.fill('テストキーワード');
    await keywordInput.press('Enter');

    // 年代層を選択していない状態で、ボタンが無効化されていることを確認
    const startButton = page.getByRole('button', { name: '記事生成を開始' });
    await expect(startButton).toBeDisabled();
  });

  test('必須項目が入力されるとボタンが有効になること', async ({ page }) => {
    await page.locator('nav').first().hover();
    await page.getByRole('link', { name: 'SEO記事作成・管理' }).click();

    await expect(page.getByRole('heading', { name: '新規SEO記事作成' })).toBeVisible();

    // 初期状態ではボタンが無効化されていることを確認
    const startButton = page.getByRole('button', { name: '記事生成を開始' });
    await expect(startButton).toBeDisabled();

    // キーワードを入力
    const keywordInput = page.getByPlaceholder(/Webマーケティング/);
    await keywordInput.fill('テストキーワード');
    await keywordInput.press('Enter');

    // まだ年代層が未選択なので、ボタンは無効のまま
    await expect(startButton).toBeDisabled();

    // 年代層を選択
    const ageCombo = page.getByRole('combobox').filter({hasText:'年代層を選択'});
    await ageCombo.click();
    await page.getByRole('option', { name: '30代' }).click();

    // 必須項目がすべて入力されたので、ボタンが有効になることを確認
    await expect(startButton).toBeEnabled();
  });
});