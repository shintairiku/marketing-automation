import { test, expect } from '@playwright/test';

test.describe('会社登録機能のテスト', () => {
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
    await page.getByLabel('事業内容').fill('テスト用の会社説明');

    // 【追加】画像で必須項目になっている項目を入力します
    await page.getByLabel('USP（企業の強み・差別化ポイント）').fill('テスト用のUSP');
    await page.getByLabel('ターゲット・ペルソナ').fill('テスト用のターゲットペルソナ');

    // 登録ボタンをクリック
    await page.getByRole('button', { name: '作成' }).click();

    // 登録成功のメッセージが表示されることを確認
    await expect(page.locator('text=会社情報を作成しました')).toBeVisible();

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
});