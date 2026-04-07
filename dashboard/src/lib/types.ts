export interface Stats {
  total: number;
  confirmed: number;
  cancelled: number;
  pending: number;
}

export interface Booking {
  id: string;
  user_id: string;
  consultant_id: string;
  service_type: string;
  scheduled_at: string;
  status: "pending" | "confirmed" | "cancelled";
  notes?: string;
  created_at: string;
}

export interface Consultant {
  id: string;
  name: string;
  specialization: string;
  phone?: string;
  email?: string;
  available_days?: string[];
  available_hours?: string;
  is_active: boolean;
}

export interface User {
  id: string;
  phone_number: string;
  name?: string;
  created_at: string;
  conversation_history?: unknown[];
}
