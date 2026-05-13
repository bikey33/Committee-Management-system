import { useQuery } from '@tanstack/react-query';
import { committeesService } from '@/api/committees';
import { AxiosError } from 'axios';

interface ErrorResponse {
  status?: string;
  message?: string;
  detail?: string;
  error?: string;
}

/**
 * Hook to fetch a committee by ID using React Query
 */
export const useGetCommitteeById = (id?: string) => {
  return useQuery({
    queryKey: ['committee', id],
    queryFn: () => {
      if (!id) {
        return Promise.resolve(null);
      }
      return committeesService.getById(id);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
    throwOnError: false,
  });
};

/**
 * Hook to fetch all committees using React Query
 */
export const useGetCommittees = () => {
  return useQuery({
    queryKey: ['committees'],
    queryFn: committeesService.getAll,
    staleTime: 5 * 60 * 1000, // 5 minutes
    throwOnError: false,
  });
};
