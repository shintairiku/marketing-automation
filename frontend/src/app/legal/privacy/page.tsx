import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'プライバシーポリシー | ブログAI',
  description: 'ブログAIのプライバシーポリシーです。個人情報の取扱いについてご確認ください。',
};

export default function PrivacyPolicyPage() {
  return (
    <article className="prose prose-stone prose-sm sm:prose-base max-w-none">
      <h1>BlogAI プライバシーポリシー</h1>
      <p className="text-stone-500 not-prose text-sm">最終更新日: 2026年3月1日</p>

      <hr />

      <p>
        株式会社新大陸（以下「当社」といいます）は、当社が提供する「BlogAI」（以下「本サービス」といいます）におけるユーザーの個人情報およびその他の情報の取扱いについて、以下のとおりプライバシーポリシー（以下「本ポリシー」といいます）を定めます。
      </p>

      <hr />

      <h2>第1条（基本方針）</h2>
      <ol>
        <li>当社は、個人情報の保護に関する法律（以下「個人情報保護法」といいます）その他の関連法令を遵守し、ユーザーの個人情報を適切に取り扱います。</li>
        <li>当社は、個人情報の取得、利用、管理について、適切な安全管理措置を講じます。</li>
      </ol>

      <hr />

      <h2>第2条（収集する情報）</h2>
      <p>当社は、本サービスの提供にあたり、以下の情報を収集します。</p>

      <h3>2-1. ユーザーから直接提供される情報</h3>
      <ul>
        <li>メールアドレス、氏名等のアカウント登録情報</li>
        <li>会社名、事業内容等の会社情報</li>
        <li>記事生成のために入力されたキーワード、テーマ、プロンプト等</li>
        <li>アップロードされた画像</li>
        <li>WordPress連携のための認証情報</li>
        <li>お問い合わせ内容</li>
      </ul>

      <h3>2-2. サービス利用時に自動的に収集される情報</h3>
      <ul>
        <li>IPアドレス、ブラウザの種類、デバイス情報</li>
        <li>アクセスログ（アクセス日時、閲覧ページ等）</li>
        <li>サービスの利用状況（記事生成回数、機能利用頻度等）</li>
        <li>Cookie情報</li>
      </ul>

      <h3>2-3. AI生成に関連する情報</h3>
      <ul>
        <li>AI生成コンテンツ（テキスト、画像）</li>
        <li>生成プロセスのログ（使用モデル、トークン数、生成ステータス等）</li>
      </ul>

      <h3>2-4. 決済に関する情報</h3>
      <ul>
        <li>Stripeを通じた決済情報（クレジットカード情報は当社のサーバーに保存されず、Stripe社が管理します）</li>
        <li>サブスクリプションの契約状況、請求履歴</li>
      </ul>

      <hr />

      <h2>第3条（情報の利用目的）</h2>
      <p>当社は、収集した情報を以下の目的で利用します。</p>
      <ol>
        <li>本サービスの提供、運営、維持、改善</li>
        <li>ユーザーのアカウント管理および認証</li>
        <li>AI記事生成・画像生成の処理、品質向上、ならびにアルゴリズムおよび機械学習モデルの改善</li>
        <li>利用料金の請求およびサブスクリプション管理</li>
        <li>利用状況の分析およびサービス品質の向上</li>
        <li>ユーザーからのお問い合わせへの対応</li>
        <li>本サービスに関する重要な通知（規約変更、メンテナンス等）</li>
        <li>不正利用の検知および防止</li>
        <li>法令に基づく対応</li>
      </ol>

      <hr />

      <h2>第4条（第三者への情報提供）</h2>
      <ol>
        <li>当社は、次の各号のいずれかに該当する場合を除き、ユーザーの個人データを第三者に提供しません。
          <ol>
            <li>ユーザー本人の同意がある場合</li>
            <li>法令に基づく場合</li>
            <li>人の生命、身体または財産の保護のために必要がある場合であって、ユーザーご本人の同意を得ることが困難であるとき</li>
            <li>公衆衛生の向上または児童の健全な育成の推進のために特に必要がある場合であって、ユーザーご本人の同意を得ることが困難であるとき</li>
            <li>国の機関もしくは地方公共団体またはその委託を受けた者が法令に定める事務を遂行することに対して協力する必要がある場合であって、ユーザーご本人の同意を得ることにより当該事務の遂行に支障を及ぼすおそれがあるとき</li>
            <li>合併、会社分割、事業譲渡その他の事由による事業承継に伴い個人情報が提供される場合</li>
          </ol>
        </li>
        <li>当社は、本サービスの提供に必要な範囲で、外部事業者に対して個人データの取扱いを伴うサービスの提供を受けることがあります。この場合、当該外部事業者による取扱いが個人情報保護法上の「委託」に該当するときは、当社は当該事業者に対して必要かつ適切な監督を行います。</li>
      </ol>

      <hr />

      <h2>第5条（外部サービスとの連携）</h2>
      <p>
        本サービスは、サービスの提供に必要な範囲で、以下の外部サービスを利用しており、各サービスに対して情報が送信されます。これらの外部サービス提供者は、本サービスの提供に必要な範囲でユーザー情報を取り扱う場合があります。当社は、各外部サービス提供者の個人情報保護体制および利用規約を確認したうえで利用しています。
      </p>

      <h3>OpenAI（AI記事生成・Web検索）</h3>
      <ul>
        <li><strong>送信される情報</strong>: ユーザーが入力したプロンプト、キーワード、テーマ、アップロード画像</li>
        <li><strong>利用目的</strong>: AI記事生成、テキスト翻訳、Web検索</li>
        <li><strong>プライバシーポリシー</strong>: <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener noreferrer">https://openai.com/policies/privacy-policy</a></li>
      </ul>

      <h3>Google Cloud / Vertex AI（画像生成・ストレージ）</h3>
      <ul>
        <li><strong>送信される情報</strong>: 画像生成プロンプト、アップロード画像</li>
        <li><strong>利用目的</strong>: AI画像生成（Imagen）、画像の保管（Cloud Storage）</li>
        <li><strong>プライバシーポリシー</strong>: <a href="https://cloud.google.com/terms/cloud-privacy-notice" target="_blank" rel="noopener noreferrer">https://cloud.google.com/terms/cloud-privacy-notice</a></li>
      </ul>

      <h3>Stripe（決済処理）</h3>
      <ul>
        <li><strong>送信される情報</strong>: メールアドレス、決済情報</li>
        <li><strong>利用目的</strong>: サブスクリプション決済処理、請求管理</li>
        <li>クレジットカード情報は当社のサーバーには保存されず、Stripe社のPCI DSS準拠環境で管理されます</li>
        <li><strong>プライバシーポリシー</strong>: <a href="https://stripe.com/jp/privacy" target="_blank" rel="noopener noreferrer">https://stripe.com/jp/privacy</a></li>
      </ul>

      <h3>Clerk（ユーザー認証）</h3>
      <ul>
        <li><strong>送信される情報</strong>: メールアドレス、氏名、認証情報</li>
        <li><strong>利用目的</strong>: ユーザー認証、アカウント管理</li>
        <li><strong>プライバシーポリシー</strong>: <a href="https://clerk.com/legal/privacy" target="_blank" rel="noopener noreferrer">https://clerk.com/legal/privacy</a></li>
      </ul>

      <h3>Supabase（データベース）</h3>
      <ul>
        <li><strong>送信される情報</strong>: ユーザーデータ、記事データ、利用履歴</li>
        <li><strong>利用目的</strong>: データの保管、リアルタイム同期</li>
        <li><strong>プライバシーポリシー</strong>: <a href="https://supabase.com/privacy" target="_blank" rel="noopener noreferrer">https://supabase.com/privacy</a></li>
      </ul>

      <h3>Vercel（ホスティング・アナリティクス）</h3>
      <ul>
        <li><strong>送信される情報</strong>: アクセスログ、利用状況データ</li>
        <li><strong>利用目的</strong>: フロントエンドホスティング、アクセス分析</li>
        <li><strong>プライバシーポリシー</strong>: <a href="https://vercel.com/legal/privacy-policy" target="_blank" rel="noopener noreferrer">https://vercel.com/legal/privacy-policy</a></li>
      </ul>

      <hr />

      <h2>第6条（Cookieおよびトラッキング技術）</h2>
      <ol>
        <li>本サービスでは、ユーザー体験の向上およびサービス改善のため、Cookie（クッキー）およびこれに類するトラッキング技術を使用しています。</li>
        <li>使用するCookieの種類は以下のとおりです。
          <ul>
            <li><strong>必須Cookie</strong>: ユーザー認証、セッション管理に必要なCookie</li>
            <li><strong>機能Cookie</strong>: ユーザーの設定・環境設定を記憶するためのCookie</li>
            <li><strong>分析Cookie</strong>: サービスの利用状況を分析するためのCookie（Vercel Analytics）</li>
          </ul>
        </li>
        <li>ユーザーは、ブラウザの設定によりCookieの受入れを拒否することができます。ただし、必須Cookieを無効にした場合、本サービスの一部が正常に動作しない場合があります。</li>
      </ol>

      <hr />

      <h2>第7条（データの保管・保護）</h2>
      <ol>
        <li>当社は、収集した情報の漏洩、紛失、改ざん、不正アクセス等を防止するため、以下の安全管理措置を講じています。
          <ul>
            <li>通信の暗号化（SSL/TLS）</li>
            <li>データベースアクセスの認証・認可制御（Row Level Security）</li>
            <li>WordPress認証情報の暗号化保存</li>
            <li>定期的なセキュリティ監査</li>
            <li>個人情報の取扱いに関する社内体制の整備および従業員教育の実施</li>
            <li>個人情報へのアクセス権限の適切な管理</li>
          </ul>
        </li>
        <li>クレジットカード情報は、PCI DSS準拠のStripe社のシステムで管理され、当社のサーバーには保存されません。</li>
      </ol>

      <hr />

      <h2>第8条（データの保持期間）</h2>
      <ol>
        <li>当社は、利用目的の達成に必要な期間、ユーザーの情報を保持します。</li>
        <li>アカウント削除後、ユーザーの個人情報は以下の期間保持した後、削除します。
          <ul>
            <li><strong>アカウント情報</strong>: 退会後30日以内に削除</li>
            <li><strong>生成記事・コンテンツ</strong>: 退会後30日以内に削除。ただし、バックアップシステム上に一定期間保存されることがあります。</li>
            <li><strong>決済に関する情報</strong>: 法令に定められた期間（最大7年間）保持</li>
            <li><strong>アクセスログ</strong>: 最大1年間保持</li>
          </ul>
        </li>
        <li>法令上の義務がある場合、必要な範囲で上記期間を超えて情報を保持することがあります。</li>
      </ol>

      <hr />

      <h2>第9条（ユーザーの権利）</h2>
      <ol>
        <li>ユーザーは、当社に対して、自己の個人情報について以下の請求を行うことができます。
          <ul>
            <li><strong>開示請求</strong>: 当社が保有する個人情報の開示</li>
            <li><strong>訂正請求</strong>: 不正確な個人情報の訂正</li>
            <li><strong>利用停止請求</strong>: 個人情報の利用停止または消去</li>
            <li><strong>第三者提供停止請求</strong>: 個人情報の第三者への提供の停止</li>
          </ul>
        </li>
        <li>上記の請求は、本ポリシー第13条に定める連絡先にご連絡ください。当社は、ご本人確認のうえ、合理的な期間内に対応いたします。</li>
        <li>ユーザーは、アカウント設定画面から、自己のアカウント情報の一部を確認・変更することができます。</li>
      </ol>

      <hr />

      <h2>第10条（海外へのデータ移転）</h2>
      <ol>
        <li>本サービスで利用する外部サービス（OpenAI、Google Cloud、Stripe、Clerk、Supabase、Vercel）のサーバーは、日本国外に所在する場合があります。</li>
        <li>ユーザーは、本サービスの利用により、自己の情報が日本国外のサーバーに送信・保管される可能性があることを理解し、同意するものとします。</li>
        <li>当社は、外部サービスの選定にあたり、適切な個人情報保護措置が講じられていることを確認しています。</li>
      </ol>

      <hr />

      <h2>第11条（未成年者の利用）</h2>
      <ol>
        <li>本サービスは、18歳以上の方を対象としています。</li>
        <li>18歳未満の方が本サービスを利用する場合は、法定代理人（親権者等）の同意を得たうえでご利用ください。</li>
      </ol>

      <hr />

      <h2>第12条（ポリシーの変更）</h2>
      <ol>
        <li>当社は、必要に応じて本ポリシーを変更することがあります。</li>
        <li>重要な変更を行う場合は、本サービス上での通知その他の適切な方法でユーザーに周知いたします。</li>
        <li>変更後のプライバシーポリシーは、本サービス上に掲示した時点から効力を生じるものとします。</li>
      </ol>

      <hr />

      <h2>第13条（お問い合わせ）</h2>
      <p>個人情報の取扱いに関するお問い合わせ、開示・訂正・利用停止等の請求は、以下の連絡先までお願いいたします。</p>
      <div className="not-prose overflow-x-auto">
        <table className="w-full text-sm border border-stone-200 rounded-lg">
          <tbody>
            <tr className="border-b border-stone-200">
              <td className="px-4 py-2.5 bg-stone-50 font-medium text-stone-600 w-48">個人情報取扱事業者</td>
              <td className="px-4 py-2.5 text-stone-700">株式会社新大陸</td>
            </tr>
            <tr className="border-b border-stone-200">
              <td className="px-4 py-2.5 bg-stone-50 font-medium text-stone-600 w-48">個人情報保護管理責任者</td>
              <td className="px-4 py-2.5 text-stone-700">代表取締役 鈴木 宏佳</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 bg-stone-50 font-medium text-stone-600 w-48">メールアドレス</td>
              <td className="px-4 py-2.5 text-stone-700">
                <a href="mailto:customer@shintairiku.jp" className="text-blue-600 hover:underline">customer@shintairiku.jp</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <hr />

      <p className="text-stone-500">以上</p>
      <p className="text-stone-500">制定日: 2026年3月1日</p>
    </article>
  );
}
