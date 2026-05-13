import { apiClient } from "./client";

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

  addMember: async (committeeId: string, memberData: any) => {
    const response = await apiClient.post(`/api/committee/committees/addmember/${committeeId}/`, memberData);
    return response.data;
  },

  removeMember: async (committeeId: string, employeeId: string) => {
    // Some backend routes might expect employeeId in the URL, some in the body.
    // Based on committee/urls.py: path('committees/<str:committee_id>/members/<str:employee_id>/', RemoveMemberView.as_view(), name='remove-member-legacy'),
    const response = await apiClient.delete(`/api/committee/committees/${committeeId}/members/${employeeId}/`);
    return response.data;
  }
};
