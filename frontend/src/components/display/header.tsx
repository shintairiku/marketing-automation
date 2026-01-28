import Image from "next/image";
import { Menu, Search } from "lucide-react";

import { SignedIn, SignedOut, SignInButton,UserButton } from "@clerk/nextjs";

export default function Header() {
    return (
      <header className="flex justify-between items-center h-[45px] bg-primary fixed top-0 left-0 right-0 z-50 px-3">
        <div className="flex items-center ">
          <div className="flex items-center gap-5">
              <Image src="/logo.png" alt="logo" width={32} height={32} />
              <p className="text-white text-lg font-bold">BlogAI</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <SignedIn>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
          <SignedOut>
            <SignInButton />
          </SignedOut>
        </div>
      </header>
    )
}
