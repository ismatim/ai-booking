"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import type { Consultant } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ConsultantForm {
  name: string;
  specialization: string;
  email: string;
  phone: string;
  available_hours: string;
}

const emptyForm: ConsultantForm = {
  name: "",
  specialization: "",
  email: "",
  phone: "",
  available_hours: "",
};

export default function ConsultantsPage() {
  const [consultants, setConsultants] = useState<Consultant[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Consultant | null>(null);
  const [form, setForm] = useState<ConsultantForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchConsultants = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Consultant[]>("/consultants");
      setConsultants(data);
    } catch (err) {
      console.error("Failed to fetch consultants:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConsultants();
  }, [fetchConsultants]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  };

  const openEdit = (consultant: Consultant) => {
    setEditing(consultant);
    setForm({
      name: consultant.name,
      specialization: consultant.specialization,
      email: consultant.email ?? "",
      phone: consultant.phone ?? "",
      available_hours: consultant.available_hours ?? "",
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        specialization: form.specialization,
        email: form.email || undefined,
        phone: form.phone || undefined,
        available_hours: form.available_hours || undefined,
      };
      if (editing) {
        await apiFetch(`/consultants/${editing.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/consultants", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      setDialogOpen(false);
      await fetchConsultants();
    } catch (err) {
      console.error("Failed to save consultant:", err);
    } finally {
      setSaving(false);
    }
  };

  const deleteConsultant = async (id: string) => {
    setDeleting(id);
    try {
      await apiFetch(`/consultants/${id}`, { method: "DELETE" });
      await fetchConsultants();
    } catch (err) {
      console.error("Failed to delete consultant:", err);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Consultants</h1>
        <Button onClick={openCreate}>Add Consultant</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Consultants ({consultants.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Specialization</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Active</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    Loading…
                  </TableCell>
                </TableRow>
              ) : consultants.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    No consultants found
                  </TableCell>
                </TableRow>
              ) : (
                consultants.map((consultant) => (
                  <TableRow key={consultant.id}>
                    <TableCell className="font-medium">{consultant.name}</TableCell>
                    <TableCell>{consultant.specialization}</TableCell>
                    <TableCell>{consultant.email ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={consultant.is_active ? "success" : "secondary"}>
                        {consultant.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEdit(consultant)}>
                          Edit
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={deleting === consultant.id}
                          onClick={() => deleteConsultant(consultant.id)}
                        >
                          {deleting === consultant.id ? "Deleting…" : "Delete"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Consultant" : "Add Consultant"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="specialization">Specialization *</Label>
              <Input
                id="specialization"
                required
                value={form.specialization}
                onChange={(e) => setForm({ ...form, specialization: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="available_hours">Available Hours</Label>
              <Input
                id="available_hours"
                placeholder="e.g. 9am–5pm"
                value={form.available_hours}
                onChange={(e) => setForm({ ...form, available_hours: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : editing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
