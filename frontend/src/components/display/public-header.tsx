import Image from 'next/image';
import Link from 'next/link';

export default function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-stone-200 bg-white/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4 sm:px-6">
        <Link href="/auth" className="flex items-center gap-2">
          <Image src="/icon.png" alt="ブログAI" width={28} height={28} />
          <span className="text-sm font-semibold text-stone-700">ブログAI</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm text-stone-500">
          <Link href="/legal/terms" className="hover:text-stone-800 transition-colors">
            利用規約
          </Link>
          <Link href="/legal/privacy" className="hover:text-stone-800 transition-colors">
            プライバシーポリシー
          </Link>
        </nav>
      </div>
    </header>
  );
}
