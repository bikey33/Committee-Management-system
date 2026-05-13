import type { CommitteeMember } from '@/types/committee';

interface RoleConfig {
  label: string;
  badgeClasses: string;
  cardBg: string;
  cardBorder: string;
  cardTextColor: string;
  cardCountColor: string;
}

const ROLE_CONFIGS: Record<string, RoleConfig> = {
  chairperson: {
    label: 'Chairperson',
    badgeClasses: 'bg-blue-100 text-blue-700 border-blue-200',
    cardBg: 'bg-blue-50',
    cardBorder: 'border-blue-200',
    cardTextColor: 'text-blue',
    cardCountColor: 'text-blue-600',
  },
  coordinator: {
    label: 'Coordinator',
    badgeClasses: 'bg-blue-100 text-blue-700 border-blue-200',
    cardBg: 'bg-blue-50',
    cardBorder: 'border-blue-200',
    cardTextColor: 'text-blue',
    cardCountColor: 'text-blue-600',
  },
  'co-ordinator': {
    label: 'Co-ordinator',
    badgeClasses: 'bg-blue-100 text-blue-700 border-blue-200',
    cardBg: 'bg-blue-50',
    cardBorder: 'border-blue-200',
    cardTextColor: 'text-blue',
    cardCountColor: 'text-blue-600',
  },
  secretary: {
    label: 'Secretary',
    badgeClasses: 'bg-purple-100 text-purple-700 border-purple-200',
    cardBg: 'bg-purple-50',
    cardBorder: 'border-purple-200',
    cardTextColor: 'text-purple',
    cardCountColor: 'text-purple-600',
  },
  member: {
    label: 'Member',
    badgeClasses: 'bg-gray-100 text-gray-700 border-gray-200',
    cardBg: 'bg-gray-50',
    cardBorder: 'border-gray-200',
    cardTextColor: 'text-gray',
    cardCountColor: 'text-gray-600',
  },
  subject_expert: {
    label: 'Subject Expert',
    badgeClasses: 'bg-green-100 text-green-700 border-green-200',
    cardBg: 'bg-green-50',
    cardBorder: 'border-green-200',
    cardTextColor: 'text-green',
    cardCountColor: 'text-green-600',
  },
  invitee: {
    label: 'Invitee',
    badgeClasses: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    cardBg: 'bg-yellow-50',
    cardBorder: 'border-yellow-200',
    cardTextColor: 'text-yellow',
    cardCountColor: 'text-yellow-600',
  },
  sub_coordinator: {
    label: 'Sub Coordinator',
    badgeClasses: 'bg-orange-100 text-orange-700 border-orange-200',
    cardBg: 'bg-orange-50',
    cardBorder: 'border-orange-200',
    cardTextColor: 'text-orange',
    cardCountColor: 'text-orange-600',
  },
};

/**
 * Normalize role name to match config keys
 */
export const normalizeRole = (role: string | undefined | null): string => {
  if (!role) return 'member';
  
  const normalized = role.toLowerCase().trim();
  
  // Check for exact matches
  if (normalized in ROLE_CONFIGS) {
    return normalized;
  }
  
  // Check for variations
  if (normalized === 'co-ordinator' || normalized === 'coordinator') {
    return 'coordinator';
  }
  
  // Default to member
  return 'member';
};

/**
 * Get role configuration
 */
export const getRoleConfig = (role: string | undefined | null): RoleConfig => {
  const normalized = normalizeRole(role);
  return ROLE_CONFIGS[normalized] || ROLE_CONFIGS.member;
};

/**
 * Check if role is a coordinator role
 */
export const isCoordinatorRole = (role: string | undefined | null): boolean => {
  const normalized = normalizeRole(role);
  return normalized === 'chairperson' || normalized === 'coordinator' || normalized === 'co-ordinator';
};

/**
 * Check if role is a secretary role
 */
export const isSecretaryRole = (role: string | undefined | null): boolean => {
  const normalized = normalizeRole(role);
  return normalized === 'secretary';
};

/**
 * Count members by role
 */
export const countMembersByRole = (members: CommitteeMember[]) => {
  const roleMap: Record<string, { count: number; config: RoleConfig }> = {};

  members.forEach((member) => {
    const normalized = normalizeRole(member.role);
    if (!roleMap[normalized]) {
      roleMap[normalized] = {
        count: 0,
        config: getRoleConfig(normalized),
      };
    }
    roleMap[normalized].count++;
  });

  return Object.entries(roleMap).map(([role, data]) => ({
    role,
    count: data.count,
    config: data.config,
  }));
};

/**
 * Get all available roles
 */
export const getAllRoles = (): RoleConfig[] => {
  return Object.values(ROLE_CONFIGS);
};

/**
 * Get role label
 */
export const getRoleLabel = (role: string | undefined | null): string => {
  return getRoleConfig(role).label;
};
