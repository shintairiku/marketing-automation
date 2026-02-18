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
# NEXT_PUBLIC_* 変数はビルド時に必要（クライアントJSにインライン化される）
# Server-onlyシークレット (STRIPE_SECRET_KEY等) はランタイムで注入するため ARG に含めない
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_APP_URL
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_GCS_BUCKET_NAME
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_APP_URL=${NEXT_PUBLIC_APP_URL}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV NEXT_PUBLIC_GCS_BUCKET_NAME=${NEXT_PUBLIC_GCS_BUCKET_NAME}
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