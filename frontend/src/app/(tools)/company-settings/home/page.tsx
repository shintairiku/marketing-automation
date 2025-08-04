export default function CompanySettingsHomePage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">会社設定</h1>
        <p className="text-muted-foreground">
          SEO記事生成で使用する会社情報とスタイルガイドを管理します。
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <a 
          href="/company-settings/company"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
        >
          <h2 className="text-xl font-semibold mb-2">会社情報設定</h2>
          <p className="text-gray-600">
            会社概要、USP、ターゲットペルソナなど、SEO記事生成に必要な会社情報を管理します。
          </p>
        </a>
        
        <a 
          href="/company-settings/style-guide"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
        >
          <h2 className="text-xl font-semibold mb-2">スタイルガイド設定</h2>
          <p className="text-gray-600">
            記事の文体、トーン、構成などのスタイルテンプレートを管理します。
          </p>
        </a>
      </div>
    </div>
  );
}