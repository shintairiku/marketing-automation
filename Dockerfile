# Dockerfile for Next.js with Bun

# 1. Base Stage: Node.js と Bun のセットアップ
FROM node:22.14.0 AS base
WORKDIR /app
# Bun をグローバルにインストール
RUN npm install -g bun

# 2. Dependencies Stage: 依存関係のインストール
FROM base AS deps
# package.json と bun.lockb をコピー
COPY package.json bun.lockb ./
# 依存関係をインストール (開発依存も含む)
RUN bun install --frozen-lockfile

# 3. Builder Stage: アプリケーションのビルド
FROM deps AS builder
# アプリケーションのソースコードをコピー
COPY . .
# Next.js アプリケーションをビルド
RUN bun run build

# 4. Development Stage: 開発環境用ステージ
FROM deps AS development
# アプリケーションのソースコードをコピー (依存関係インストール後に再度コピー)
COPY . .
# 開発サーバー用のポートを開放
EXPOSE 3000
# 開発サーバーを起動
CMD ["bun", "run", "dev"]

# 5. Production Stage: 本番環境用ステージ
FROM node:22.14.0-alpine AS production
WORKDIR /app
# 環境変数を本番用に設定
ENV NODE_ENV production
# standalone 出力に必要なファイルを builder ステージからコピー
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# 本番サーバー用のポートを開放
EXPOSE 3000
# node ユーザーで実行
USER node
# アプリケーションを起動 (standalone モード)
CMD ["node", "server.js"]

