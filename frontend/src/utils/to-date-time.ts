export function toDateTime(secs: number | string | null | undefined) {
  // nullまたはundefinedの場合はnullを返す
  if (secs === null || secs === undefined) {
    return null;
  }
  
  try {
    // 文字列の場合は数値に変換
    const seconds = typeof secs === 'string' ? parseInt(secs, 10) : secs;
    
    // 数値に変換できない場合はnullを返す
    if (isNaN(seconds)) {
      console.error(`Invalid timestamp value: ${secs}`);
      return null;
    }
    
    // ミリ秒に変換して新しいDateオブジェクトを作成
    return new Date(seconds * 1000);
  } catch (error) {
    console.error(`Error converting timestamp: ${secs}`, error);
    return null;
  }
}