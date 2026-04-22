"use client";
import { AppSidebar } from "@/components/app-sidebar";
import { SiteHeader } from "@/components/site-header";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { DataTable } from "@/components/data-table";
import { useEffect, useState } from "react";

export default function AdminPage() {
  const [data, setData] = useState([]);

  useEffect(() => {
    const loadData = () => {
      fetch("/api/messages")
        .then((response) => response.json())
        .then((data) => {
          console.log("Fetched data:", data);
          setData(data);
        })
        .catch((error) => {
          console.error("Error fetching data:", error);
        });
    };
    loadData();
  }, []);

  return (
    <SidebarProvider
      style={{
        "--sidebar-width": "calc(var(--spacing) * 72)",
        "--header-height": "calc(var(--spacing) * 12)",
      }}
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              <DataTable data={data} />
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
