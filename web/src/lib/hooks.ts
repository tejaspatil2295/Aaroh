import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { del, get, patch, post } from "../api/client";

/** Invalidate everything that might show derived numbers (dashboard, summaries). */
export function useInvalidate() {
  const qc = useQueryClient();
  return (...keys: string[]) => {
    keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };
}

export function useList<T = any>(path: string, params = "", enabled = true) {
  return useQuery<T[]>({ queryKey: [path, params], queryFn: () => get<T[]>(`${path}${params}`), enabled });
}

export function useGet<T = any>(path: string, enabled = true) {
  return useQuery<T>({ queryKey: [path], queryFn: () => get<T>(path), enabled });
}

/** CRUD mutations for a REST collection. `related` lists other query roots to refresh. */
export function useCrud(path: string, related: string[] = []) {
  const inv = useInvalidate();
  const done = () => inv(path, ...related);
  return {
    create: useMutation({ mutationFn: (data: any) => post(path, data), onSuccess: done }),
    update: useMutation({ mutationFn: ({ id, data }: { id: string; data: any }) => patch(`${path}/${id}`, data), onSuccess: done }),
    remove: useMutation({ mutationFn: (id: string) => del(`${path}/${id}`), onSuccess: done }),
  };
}
