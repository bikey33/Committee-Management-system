import { apiClient } from "./client";

export interface CommitteeCheckpoint {
  id?: number;
  name?: string;
  phase?: string;
  is_completed?: boolean;
  order?: number;
}

export interface CommitteePhase {
  phase: string;
  name: string;
  order: number;
  completed: boolean;
  visible: boolean;
  checkpoints: CommitteeCheckpoint[];
  completion_percentage: number;
}

export interface Committee {
  id: string;
  _id?: string;
  name: string;
  purpose: string;
  committee_type: string;
  formation_date: string | null;
  deadline: string | null;
  status: string;
  committee_status: string;
  members_count?: number;
  office?: number | string | null;
  office_name?: string;
  formationLetterURL?: string;
  membersList?: { employeeId: string; name: string; role: string }[];
  current_phase?: string;
  phases?: CommitteePhase[];
  initialization_phase_completed?: boolean;
  finalization_phase_completed?: boolean;
  is_closed?: boolean;
  is_overdue?: boolean;
  completion_notes?: string | null;
}

export interface MyCommitteeReportItem {
  committee_id: number | string;
  name: string;
  committee_type: string;
  committee_status: string;
  office_name?: string | null;
  deadline?: string | null;
  members_count?: number;
  is_closed: boolean;
  is_overdue: boolean;
  my_role?: string;
  membership_active?: boolean;
  joined_at?: string | null;
  left_at?: string | null;
  left_reason?: "removed" | "closed" | null;
}

export interface MyCommitteesReport {
  active: MyCommitteeReportItem[];
  past: MyCommitteeReportItem[];
  counts: { active: number; past: number };
}

export interface CommitteeStats {
  scope?: "org" | "office" | "personal" | string;
  totals: { total: number; closed: number; open: number; overdue: number };
  by_status: { committee_status: string; count: number }[];
  by_type: { committee_type: string; count: number }[];
  by_office: { office_id: number | null; office_name: string | null; count: number }[];
}

export interface CommitteeDocument {
  id: number;
  name: string;
  url: string | null;
  uploaded_at: string;
  uploaded_by: string | null;
}

export interface RoleDistributionMember {
  employee_id: string;
  name: string;
  office: string | null;
  committee_count: number;
  committees: { id: number; name: string; office: string | null; status: string }[];
}

export interface RoleDistributionEntry {
  role: string;
  member_count: number;
  total_memberships: number;
  members: RoleDistributionMember[];
}

export interface RoleDistributionReport {
  roles: RoleDistributionEntry[];
}

export interface StalledCommitteeMember {
  employee_id: string;
  name: string;
  role: string;
}

export interface StalledCommittee {
  id: number;
  name: string;
  committee_type: string;
  committee_status: string;
  office: string | null;
  created_at: string;
  last_activity: string;
  days_stalled: number;
  is_overdue: boolean;
  deadline: string | null;
  member_count: number;
  members: StalledCommitteeMember[];
}

export interface StalledCommitteesReport {
  days_threshold: number;
  cutoff: string;
  count: number;
  committees: StalledCommittee[];
}

export const committeesService = {
  getAll: async () => {
    const response = await apiClient.get("/api/committee/committees/all/");
    // Return the array from the backend response structure
    if (response.data?.data?.committees) {
      return response.data.data.committees;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  getByMember: async (employeeId: string) => {
    const response = await apiClient.get(`/api/committee/committees/bymember/${employeeId}/`);
    if (response.data?.data?.committees) {
      return response.data.data.committees;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  getById: async (id: string) => {
    const response = await apiClient.get(`/api/committee/committees/${id}/`);
    return response.data;
  },

  create: async (data: any) => {
    const response = await apiClient.post("/api/committee/committees/create/", data);
    return response.data;
  },

  update: async (id: string, data: any) => {
    if (!id || id === 'undefined') {
      throw new Error('Committee ID is required for update');
    }
    const response = await apiClient.patch(`/api/committee/committees/update/${id}/`, data);
    return response.data;
  },

  delete: async (id: string) => {
    const response = await apiClient.delete(`/api/committee/committees/deletecommittee/${id}/`);
    return response.data;
  },

  getRoles: async () => {
    const response = await apiClient.get("/api/committee/roles/");
    return response.data;
  },

  // ----- Reporting -----
  getMyCommitteesReport: async (): Promise<MyCommitteesReport> => {
    const response = await apiClient.get("/api/committee/committees/reports/my-committees/");
    return response.data?.data ?? { active: [], past: [], counts: { active: 0, past: 0 } };
  },

  getOfficeCommittees: async (officeId?: number | string) => {
    const response = await apiClient.get("/api/committee/committees/reports/office/", {
      params: officeId ? { office_id: officeId } : {},
    });
    return response.data?.data?.committees ?? [];
  },

  getCommitteeStats: async (officeId?: number | string): Promise<CommitteeStats> => {
    const response = await apiClient.get("/api/committee/committees/reports/stats/", {
      params: officeId ? { office_id: officeId } : {},
    });
    return { scope: response.data?.scope, ...(response.data?.data ?? {}) };
  },

  transitionStatus: async (id: string, committeeStatus: string, completionNotes?: string) => {
    const response = await apiClient.patch(`/api/committee/committees/${id}/status/`, {
      committee_status: committeeStatus,
      ...(completionNotes !== undefined ? { completion_notes: completionNotes } : {}),
    });
    return response.data;
  },

  getDocuments: async (committeeId: string) => {
    const response = await apiClient.get(`/api/committee/committees/${committeeId}/documents/`);
    return (response.data?.data ?? []) as CommitteeDocument[];
  },

  uploadDocument: async (committeeId: string, file: File, name?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    const response = await apiClient.post(`/api/committee/committees/${committeeId}/documents/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data?.data as CommitteeDocument;
  },

  deleteDocument: async (committeeId: string, docId: number) => {
    await apiClient.delete(`/api/committee/committees/${committeeId}/documents/${docId}/`);
  },

  viewDocument: async (committeeId: string, docId: number) => {
    const response = await apiClient.get(
      `/api/committee/committees/${committeeId}/documents/${docId}/serve/`,
      { responseType: "blob" }
    );
    const blob = new Blob([response.data], { type: response.headers["content-type"] || "application/octet-stream" });
    const url = window.URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => window.URL.revokeObjectURL(url), 10_000);
  },

  addMember: async (committeeId: string, memberData: any) => {
    const response = await apiClient.post(`/api/committee/committees/addmember/${committeeId}/`, memberData);
    return response.data;
  },

  removeMember: async (committeeId: string, employeeId: string) => {
    // Some backend routes might expect employeeId in the URL, some in the body.
    // Based on committee/urls.py: path('committees/<str:committee_id>/members/<str:employee_id>/', RemoveMemberView.as_view(), name='remove-member-legacy'),
    const response = await apiClient.delete(`/api/committee/committees/${committeeId}/members/${employeeId}/`);
    return response.data;
  },

  getRoleDistribution: async (): Promise<RoleDistributionReport> => {
    const response = await apiClient.get('/api/committee/committees/reports/role-distribution/');
    return response.data;
  },

  getStalledCommittees: async (days = 30): Promise<StalledCommitteesReport> => {
    const response = await apiClient.get(`/api/committee/committees/reports/stalled/?days=${days}`);
    return response.data;
  },
};
