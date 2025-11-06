import { test as setup, expect } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// .env.test を読み込む（config同様）
dotenv.config({ path: path.resolve(__dirname, '..', '.env.test') });

// 認証情報を保存するファイルのパス
const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {  
  // まずホームページに移動
  await page.goto('http://localhost:3000');
  
  // ログインボタンをクリック
  await page.getByRole('button', { name: 'ログイン' }).click();
  
  // Googleで続ける
  await page.getByRole('button', { name: 'Googleで続ける' }).click();
  
  // メールアドレス入力
  // （タイムアウトを少し長めに設定）
  await page.getByRole('textbox', { name: 'Email or phone' }).fill(process.env.TEST_USER_EMAIL!, { timeout: 10000 });
  await page.getByRole('button', { name: 'Next' }).click();

  // パスワードを入力
  await page.getByRole('textbox', { name: 'Enter your password' }).fill(process.env.TEST_USER_PASSWORD!);
  await page.getByRole('button', { name: 'Next' }).click();
  
  // ログインが完了し、ダッシュボードにいることを確認
  await page.waitForURL('**/dashboard');
  
  // 現在のブラウザの認証情報（Cookieなど）をファイルに保存
  await page.context().storageState({ path: authFile });
});