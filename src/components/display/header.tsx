import { Search, Menu } from "lucide-react"

export default function Header() {
    return (
      <header className="flex min-h-[60px] items-center justify-between bg-[#F9F9F9] shadow-lg px-4 z-10">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gray-200"></div>
          <h1 className="text-xl font-medium">shintairiku</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input type="text" placeholder="search/" className="h-10 rounded-md border border-gray-300 pl-9 pr-4" />
          </div>
          <button className="ml-2 rounded-md border border-gray-300 p-2">
            <Menu className="h-5 w-5" />
          </button>
          <div className="ml-2 h-8 w-8 rounded-full bg-gray-200"></div>
        </div>
      </header>
    )
}
