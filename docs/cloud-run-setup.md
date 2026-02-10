# Cloud Run IAM 設定手順

## Step 2: Invokerロール付与

```bash
gcloud run services add-iam-policy-binding marketing-automation --member="serviceAccount:vercel-invoker@marketing-automation-461305.iam.gserviceaccount.com" --role="roles/run.invoker" --region=asia-northeast1 --project=marketing-automation-461305
```

## Step 3: SAキー生成

```bash
gcloud iam service-accounts keys create sa-key.json --iam-account=vercel-invoker@marketing-automation-461305.iam.gserviceaccount.com
```

Base64エンコード:

```bash
base64 -w 0 sa-key.json
```

## Step 4: Vercel環境変数

| 変数名 | 値 |
|--------|---|
| `CLOUD_RUN_AUDIENCE_URL` | `https://marketing-automation-742231208085.asia-northeast1.run.app` |
| `GOOGLE_SA_KEY_BASE64` | Step 3のBase64出力 |

## Step 6: Cloud Run非公開化 (テスト後に実行)

```bash
gcloud run services remove-iam-policy-binding marketing-automation --member="allUsers" --role="roles/run.invoker" --region=asia-northeast1 --project=marketing-automation-461305
```

## ロールバック (問題発生時)

```bash
gcloud run services add-iam-policy-binding marketing-automation --member="allUsers" --role="roles/run.invoker" --region=asia-northeast1 --project=marketing-automation-461305
```
