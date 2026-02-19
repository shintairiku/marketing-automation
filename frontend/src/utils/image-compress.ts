/**
 * クライアントサイド画像圧縮ユーティリティ
 *
 * Canvas API を使って画像をリサイズ・JPEG 圧縮する。
 * Next.js/Vercel のボディサイズ上限 (~4.5MB) を超えないようにするため、
 * アップロード前にブラウザ側で圧縮する。
 *
 * バックエンドでは別途 WebP 変換 + リサイズを行うため、
 * ここではアップロード経路を通すための最低限の圧縮を目的とする。
 */

/** 長辺の最大ピクセル数 */
const MAX_DIMENSION = 2048;

/** 圧縮後の最大ファイルサイズ (bytes) — プロキシのボディ上限に収まるよう余裕を持たせる */
const MAX_FILE_SIZE = 3 * 1024 * 1024; // 3MB

/** この閾値以下のファイルは圧縮をスキップ */
const SKIP_THRESHOLD = 800 * 1024; // 800KB

/**
 * 画像ファイルをリサイズ + JPEG 圧縮して返す。
 *
 * - 800KB 以下のファイルはそのまま返す（圧縮不要）
 * - 長辺が MAX_DIMENSION を超える場合はリサイズ
 * - 品質を段階的に下げて MAX_FILE_SIZE 以内に収める
 *
 * @param file 元の画像ファイル
 * @returns 圧縮済みの File オブジェクト（または元ファイル）
 */
export async function compressImage(file: File): Promise<File> {
  // 十分小さいファイルはスキップ
  if (file.size <= SKIP_THRESHOLD) {
    return file;
  }

  return new Promise<File>((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);

      let { width, height } = img;

      // リサイズ（長辺が MAX_DIMENSION を超える場合）
      if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
        const scale = MAX_DIMENSION / Math.max(width, height);
        width = Math.round(width * scale);
        height = Math.round(height * scale);
      }

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        // Canvas 未サポート時は元ファイルをそのまま返す
        resolve(file);
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      // 品質を段階的に下げて圧縮
      const tryCompress = (quality: number) => {
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              // Blob 生成失敗時は元ファイルを返す
              resolve(file);
              return;
            }

            // まだ大きい場合は品質を下げてリトライ
            if (blob.size > MAX_FILE_SIZE && quality > 0.4) {
              tryCompress(quality - 0.15);
              return;
            }

            const baseName = file.name.replace(/\.[^.]+$/, "");
            resolve(
              new File([blob], baseName + ".jpg", { type: "image/jpeg" })
            );
          },
          "image/jpeg",
          quality
        );
      };

      tryCompress(0.85);
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      // 読み込み失敗時は元ファイルをそのまま返す（バックエンドでエラーになる）
      reject(new Error("画像の読み込みに失敗しました"));
    };

    img.src = objectUrl;
  });
}

/**
 * 複数の画像ファイルを並列で圧縮する。
 * 個々の圧縮が失敗した場合は元ファイルをそのまま使用する。
 */
export async function compressImages(files: File[]): Promise<File[]> {
  return Promise.all(
    files.map((file) =>
      compressImage(file).catch(() => file)
    )
  );
}
