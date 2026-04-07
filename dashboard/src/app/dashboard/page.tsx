import type { Metadata } from "next";
import { apiFetch } from "@/lib/api";
import type { Stats, Booking } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = {
  title: "Dashboard | AI Booking Admin",
};

async function getStats(): Promise<Stats> {
  const res = await apiFetch<{ success: boolean; data: Stats }>("/admin/stats", {
    cache: "no-store",
  });
  return res.data;
}

async function getAllBookings(): Promise<Booking[]> {
  const res = await apiFetch<{ success: boolean; count: number; data: Booking[] }>(
    "/admin/bookings/all",
    { cache: "no-store" }
  );
  return res.data;
}

function StatusBadge({ status }: { status: Booking["status"] }) {
  const variant =
    status === "confirmed" ? "success" : status === "cancelled" ? "danger" : "warning";
  return <Badge variant={variant}>{status}</Badge>;
}

export default async function DashboardPage() {
  let stats: Stats = { total: 0, confirmed: 0, cancelled: 0, pending: 0 };
  let bookings: Booking[] = [];

  try {
    [stats, bookings] = await Promise.all([getStats(), getAllBookings()]);
  } catch {
    // silently continue with empty defaults if API is unavailable
  }

  const recent = bookings
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 10);

  const statCards = [
    { label: "Total Bookings", value: stats.total, color: "text-blue-600" },
    { label: "Confirmed", value: stats.confirmed, color: "text-green-600" },
    { label: "Cancelled", value: stats.cancelled, color: "text-red-600" },
    { label: "Pending", value: stats.pending, color: "text-yellow-600" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map(({ label, value, color }) => (
          <Card key={label}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className={`text-3xl font-bold ${color}`}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Bookings</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Scheduled At</TableHead>
                <TableHead>Created At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    No bookings found
                  </TableCell>
                </TableRow>
              ) : (
                recent.map((booking) => (
                  <TableRow key={booking.id}>
                    <TableCell className="font-mono text-xs">{booking.id.slice(0, 8)}…</TableCell>
                    <TableCell>{booking.service_type}</TableCell>
                    <TableCell>
                      <StatusBadge status={booking.status} />
                    </TableCell>
                    <TableCell>{new Date(booking.scheduled_at).toLocaleString()}</TableCell>
                    <TableCell>{new Date(booking.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
