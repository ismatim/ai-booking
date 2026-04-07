"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Calendar, Users, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/bookings", label: "Bookings", icon: Calendar },
  { href: "/consultants", label: "Consultants", icon: UserCheck },
  { href: "/users", label: "Users", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col w-56 shrink-0 border-r bg-background min-h-screen">
      <div className="p-4">
        <p className="text-xs font-semibold uppercase text-muted-foreground tracking-wider px-2">
          Navigation
        </p>
      </div>
      <Separator />
      <nav className="flex flex-col gap-1 p-3">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Button
            key={href}
            variant={pathname === href || pathname.startsWith(href + "/") ? "secondary" : "ghost"}
            className={cn(
              "w-full justify-start gap-2",
              (pathname === href || pathname.startsWith(href + "/")) && "font-semibold"
            )}
            asChild
          >
            <Link href={href}>
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          </Button>
        ))}
      </nav>
    </aside>
  );
}
