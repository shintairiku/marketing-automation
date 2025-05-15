# Dockerfile for Next.js with Bun

# 1. Base Stage: Node.js と Bun のセットアップ
FROM node:22-alpine AS base
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
# 環境変数をビルド時に渡せるように ARG で定義
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG STRIPE_SECRET_KEY
ARG SUPABASE_SERVICE_ROLE_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
ENV STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
ENV SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
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
FROM node:22-alpine AS production
WORKDIR /app
# 環境変数を本番用に設定
ENV NODE_ENV production
# Bun をグローバルにインストール (本番環境でもビルド成果物の実行にnode以外が必要な場合があるため)
# ただし、Next.jsのstandaloneモードでは通常不要。server.js を node で直接実行する。
# RUN npm install -g bun

# standalone 出力に必要なファイルを builder ステージからコピー
COPY --from=builder --chown=node:node /app/.next/standalone ./
# COPY --from=builder /app/public ./public # この行を削除 (standaloneに含まれるため)
# COPY --from=builder --chown=node:node /app/.next/static ./.next/static # この行も削除 (standaloneに含まれるため)

# ポートを開放
EXPOSE 3000
# node ユーザーで実行
USER node
# アプリケーションを起動 (standalone モード)
CMD ["node", "server.js"] 