export type StepInfo = {
  id: string;
  number: number;
  title: string;
}

export const SEO_STEPS: StepInfo[] = [
    { id: 'theme', number: 1, title: 'テーマ' },
    { id: 'headline', number: 2, title: 'ヘッドライン' },
    { id: 'description', number: 3, title: 'ディスクリプション' },
    { id: 'edit', number: 4, title: '編集' },
    { id: 'post', number: 5, title: '投稿' },
  ]; 

export type TabOption = {
    label: string
    value: string
}