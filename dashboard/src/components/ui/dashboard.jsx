import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar, Users, CheckCircle, Clock } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time status of your AI booking system.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Bookings"
          value="128"
          icon={<Calendar className="h-4 w-4 text-muted-foreground" />}
          description="+12% from last month"
        />
        <StatCard
          title="Active Consultants"
          value="14"
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
          description="Across 3 departments"
        />
        <StatCard
          title="Confirmed Today"
          value="8"
          icon={<CheckCircle className="h-4 w-4 text-muted-foreground" />}
          description="No cancellations"
        />
        <StatCard
          title="Pending Invites"
          value="3"
          icon={<Clock className="h-4 w-4 text-muted-foreground" />}
          description="Awaiting user email"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Recent AI Interactions</CardTitle>
          </CardHeader>
          <CardContent>
            {/* This is where you'd list the latest logs from Python/Supabase */}
            <p className="text-sm text-muted-foreground italic">
              Fetching latest activity...
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, description }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
